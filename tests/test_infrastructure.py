"""Check schedules, isolation, least privilege and placeholder execution."""
import ast
from datetime import datetime, timedelta
from pathlib import Path
import re
import subprocess
import sys
import unittest
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {'uk': 'Europe/London', 'india': 'Asia/Kolkata', 'eu': 'Europe/Berlin'}


class InfrastructureTests(unittest.TestCase):
    def test_workflows_and_config(self):
        config = yaml.safe_load((ROOT / 'config/settings.yaml').read_text())
        groups = set()
        for key, zone in EXPECTED.items():
            with self.subTest(agent=key):
                # BaseLoader preserves YAML 1.2/GitHub's "on" key as a string.
                workflow = yaml.load((ROOT / f'.github/workflows/{key}-agent.yml').read_text(), Loader=yaml.BaseLoader)
                self.assertEqual(set(workflow['on']), {'schedule', 'workflow_dispatch'})
                self.assertEqual(workflow['on']['schedule'], [{'cron': '0 8,14,20 * * *', 'timezone': zone}])
                self.assertEqual(workflow['permissions'], {'contents': 'read', **({'id-token': 'write'} if key == 'uk' else {})})
                group = workflow['concurrency']['group']
                self.assertNotIn(group, groups)
                groups.add(group)
                self.assertEqual(workflow['concurrency']['cancel-in-progress'], 'false')
                self.assertEqual(len(workflow['jobs']), 1)
                job = workflow['jobs']['run-agent']
                self.assertEqual(job['runs-on'], 'ubuntu-latest')
                self.assertEqual(job['env']['TZ'], zone)
                self.assertNotIn('needs', job)
                self.assertLessEqual(int(job['timeout-minutes']), 5)
                steps = job['steps']
                for step in steps:
                    self.assertNotIn('continue-on-error', step)
                    if 'uses' in step:
                        self.assertRegex(step['uses'], r'^(actions/(checkout|setup-python)|google-github-actions/auth)@[a-f0-9]{40}$')
                self.assertEqual(steps[0]['with']['persist-credentials'], 'false')
                commands = '\n'.join(s.get('run', '') for s in steps)
                self.assertIn(f'python agents/{key}_agent.py', commands)
                self.assertIn('-r requirements.txt', commands)
                self.assertEqual(config['agents'][f'{key.upper()}_SOC_AGENT']['timezone'], zone)
                self.assertEqual(config['agents'][f'{key.upper()}_SOC_AGENT']['times'], ['08:00', '14:00', '20:00'])

    def test_dst_offsets(self):
        expected = {'Europe/London': (0, 1), 'Europe/Berlin': (1, 2), 'Asia/Kolkata': (5.5, 5.5)}
        for zone, offsets in expected.items():
            for month, hours in zip((1, 7), offsets):
                for hour in (8, 14, 20):
                    local = datetime(2027, month, 15, hour, tzinfo=ZoneInfo(zone))
                    self.assertEqual(local.utcoffset(), timedelta(hours=hours))

    def test_python_syntax_and_placeholders(self):
        for path in ROOT.rglob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for key, zone in EXPECTED.items():
            with self.subTest(agent=key):
                result = subprocess.run([sys.executable, str(ROOT / f'agents/{key}_agent.py')] + (['--check'] if key == 'uk' else []), capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f'{key.upper()}_SOC_AGENT', result.stdout)
                self.assertIn(zone, result.stdout)
                self.assertIn('Successful completion.', result.stdout)
                self.assertIn('no job searches or applications performed', result.stdout)
                stamp = re.search(r'Execution timestamp \(UTC\): (.+)', result.stdout).group(1)
                self.assertIsNotNone(datetime.fromisoformat(stamp).tzinfo)


if __name__ == '__main__':
    unittest.main()
