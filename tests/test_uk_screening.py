import unittest
from datetime import datetime, timezone
from utils.uk_screening import sponsorship, clearance, same_vacancy, sheet_row, search_since


class UKScreeningTests(unittest.TestCase):
    def test_sponsorship_never_assumes(self):
        self.assertEqual(sponsorship('Visa sponsorship is not offered.'), 'Not Offered')
        self.assertEqual(sponsorship('Skilled Worker sponsorship may be available.'), 'Available')
        self.assertEqual(sponsorship('Right to work required.'), 'Not Specified')

    def test_clearance(self):
        self.assertEqual(clearance('Candidates must already hold active SC clearance.'), 'exclude_existing_clearance_required')
        self.assertEqual(clearance('Must be eligible for SC clearance.'), 'review')
        self.assertEqual(clearance('Security operations analyst'), 'not stated')

    def test_matching_requires_strong_identity(self):
        a = {'company': 'Example', 'requisition': '123', 'url': 'https://example.com/job/123?utm_source=x'}
        self.assertTrue(same_vacancy(a, {'company': 'Example', 'requisition': '123'}))
        self.assertFalse(same_vacancy(a, {'company': 'Example', 'requisition': '456', 'url': a['url']}))
        self.assertFalse(same_vacancy(a, {'company': 'Other', 'requisition': '123'}))

    def test_weekend_and_weekday_windows(self):
        self.assertEqual(search_since(datetime(2026, 11, 14, 12, tzinfo=timezone.utc)).isoformat(), '2026-11-09T00:00:00+00:00')
        self.assertEqual(search_since(datetime(2026, 11, 17, 12, tzinfo=timezone.utc)).isoformat(), '2026-11-16T12:00:00+00:00')

    def test_eight_columns(self):
        self.assertEqual(len(sheet_row({})), 8)
        self.assertEqual(sheet_row({})[-1], 'Not Applied')


if __name__ == '__main__':
    unittest.main()
