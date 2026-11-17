"""UK discovery agent with private persistence and safe Sheets appends."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from utils.uk_discovery import fetch_board
from utils.uk_store import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    print('Agent ID: UK_SOC_AGENT')
    print(f'Execution timestamp (UTC): {now.isoformat()}')
    print(f'Execution timestamp (Europe/London): {now.astimezone(ZoneInfo("Europe/London")).isoformat()}')
    sources = json.loads((ROOT / 'config/uk_sources.json').read_text())
    if Counter(s['kind'] for s in sources) != {'employer': 42, 'agency': 5, 'platform': 14}:
        raise ValueError('Incorrect source inventory')
    if args.check:
        print('Configuration valid; no job searches or applications performed. Successful completion.')
        return
    store = None if args.dry_run else Store(os.environ['GOOGLE_SHEET_ID'])
    summary = dict(status='partial coverage', configured=len(sources), searched=0, unsearched=0, failed=0, scanned=0, included=0, review=0, rejected=0, inserted=0, sources=[])
    for source in sources:
        if source['adapter'] != 'greenhouse':
            summary['unsearched'] += 1
            summary['sources'].append(dict(name=source['name'], status='not searched: no verified adapter'))
            continue
        try:
            result = fetch_board(source['board'], source['name'], now)
        except Exception as exc:
            summary['failed'] += 1
            summary['sources'].append(dict(name=source['name'], status='temporarily unavailable', error_type=type(exc).__name__))
            continue
        summary['searched'] += 1
        summary['scanned'] += result['listings_scanned']
        summary['sources'].append(dict(name=source['name'], status='successfully searched'))
        for job in result['records']:
            summary[{'include': 'included', 'review': 'review', 'reject': 'rejected'}[job['decision']]] += 1
            if store:
                summary['inserted'] += int(store.save(job))
    if not summary['searched']:
        summary['status'] = 'failed: no source successfully searched'
    if store:
        store.log(summary)
    print(json.dumps({k:v for k,v in summary.items() if k != 'sources'}))
    if not summary['searched']:
        raise RuntimeError('All live sources failed')
    print('Successful completion; see EXECUTION_LOGS for source coverage.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'UK agent failed ({type(exc).__name__}); private details withheld.', file=sys.stderr)
        sys.exit(1)
