import unittest
from copy import deepcopy
from utils.uk_store import Store, HEADERS
from utils.uk_discovery import assess


class Tab:
    def __init__(self, rows):
        self.rows = deepcopy(rows)
    def append_row(self, row, **kwargs):
        self.rows.append(row)
        return {'updates': {'updatedRange': f"'Tab'!A{len(self.rows)}:H{len(self.rows)}"}}
    def update(self, range_name, values, **kwargs):
        import re
        number = int(re.search(r'\d+', range_name).group()) - 1
        if range_name.startswith('G'):
            self.rows[number][6] = values[0][0]
        else:
            self.rows[number] = values[0]


class StoreTests(unittest.TestCase):
    def test_retries_and_url_upgrade_preserve_status(self):
        s = Store.__new__(Store)
        s.jobs = Tab([HEADERS])
        s.tracking = Tab([['ID', 'Time', 'JSON']])
        s.urls, s.url_rows, s.previous = set(), {}, {}
        job = dict(company='Example', title='Junior SOC Analyst', location='UK', requisition='123', url='https://example.com/jobs/123', decision='include', verified_at='2026-11-17', first_seen='2026-11-17')
        self.assertTrue(s.save(dict(job)))
        s.jobs.rows[1][7] = 'Applied'
        self.assertFalse(s.save(dict(job)))
        self.assertEqual(len(s.jobs.rows), 2)
        job['url'] = 'https://example.com/careers/123'
        self.assertFalse(s.save(dict(job)))
        self.assertEqual(s.jobs.rows[1][7], 'Applied')
        self.assertEqual(s.jobs.rows[1][6], job['url'])
        self.assertEqual(len(s.tracking.rows), 2)

    def test_review_never_inserts(self):
        s = Store.__new__(Store)
        s.jobs, s.tracking = Tab([HEADERS]), Tab([['ID', 'Time', 'JSON']])
        s.urls, s.url_rows, s.previous = set(), {}, {}
        s.save(dict(company='Example', title='SOC Analyst', url='https://example.com/job/2', decision='review', verified_at='now', first_seen='now'))
        self.assertEqual(len(s.jobs.rows), 1)
        self.assertEqual(len(s.tracking.rows), 2)

    def test_eligibility_uncertainty(self):
        self.assertEqual(assess('Junior SOC Analyst', 'Training provided')[0], 'include')
        self.assertEqual(assess('Junior SOC Analyst', 'Three years preferred, UK citizen required')[0], 'review')
        self.assertEqual(assess('Junior SOC Analyst', '2 years experience required')[0], 'review')
        self.assertEqual(assess('SOC Analyst', 'Experience required')[0], 'review')
