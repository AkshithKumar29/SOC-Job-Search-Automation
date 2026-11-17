"""Private workbook persistence. Never rewrite user application status cells."""
import json
import hashlib
from datetime import datetime, timezone
import google.auth
import gspread
from utils.uk_screening import canonical_url, sheet_row

HEADERS = ['Company Name', 'Job Title', 'Location', 'Experience Required',
           'Visa Sponsorship', 'Job Posted Date', 'Application URL', 'Application Status']


def key(job):
    identity = job['company'].casefold() + '|' + (job.get('requisition') or canonical_url(job['url']))
    return hashlib.sha256(identity.encode()).hexdigest()


class Store:
    def __init__(self, sheet_id):
        creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/spreadsheets'])
        self.book = gspread.authorize(creds).open_by_key(sheet_id)
        print('Sheets: authenticated and opened workbook')
        self.jobs = self.book.worksheet('UK_JOBS')
        rows = self.jobs.get_all_values()
        if rows and rows[0] != HEADERS:
            raise ValueError('UK_JOBS header differs from required eight columns; refusing to overwrite existing data')
        if not rows:
            print('Sheets: initializing UK headers')
            self.jobs.update(range_name='A1:H1', values=[HEADERS], value_input_option='RAW')
        self.urls = {canonical_url(r[6]) for r in rows[1:] if len(r) > 6}
        self.url_rows = {canonical_url(r[6]): i for i, r in enumerate(rows[1:], start=2) if len(r) > 6}
        if any(len(r) > 8 for r in rows):
            raise ValueError('UK_JOBS contains data beyond eight columns')
        if self.jobs.col_count != 8:
            print('Sheets: setting UK column count to eight')
            self.jobs.resize(cols=8)
        try:
            self.tracking = self.book.worksheet('UK_INTERNAL_TRACKING')
        except gspread.WorksheetNotFound:
            print('Sheets: creating private tracking worksheet')
            self.tracking = self.book.add_worksheet(title='UK_INTERNAL_TRACKING', rows=1000, cols=3)
            self.tracking.append_row(['Record ID', 'Last Verified UTC', 'Private Record JSON'], value_input_option='RAW')
        self.previous = {}
        for number, row in enumerate(self.tracking.get_all_values()[1:], start=2):
            if len(row) >= 3:
                self.previous[row[0]] = (number, json.loads(row[2]))

    def save(self, job):
        print('Sheets: persisting private tracking record')
        identifier = key(job)
        prior = self.previous.get(identifier)
        if prior:
            job['first_seen'] = prior[1].get('first_seen', job['first_seen'])
        url = canonical_url(job['url'])
        inserted = False
        old_url = canonical_url(prior[1]['url']) if prior else ''
        if old_url in self.url_rows and url != old_url:
            # Only the verified application URL is updated; column H is never touched.
            self.jobs.update(range_name=f'G{self.url_rows[old_url]}', values=[[job['url']]], value_input_option='RAW')
            self.urls.add(url)
        # Existing sheet URLs are authoritative after an interrupted earlier run.
        if job['decision'] == 'include' and url not in self.urls:
            result = self.jobs.append_row(sheet_row(job), value_input_option='RAW')
            import re
            self.url_rows[url] = int(re.search(r'![A-Z]+(\d+)', result['updates']['updatedRange']).group(1))
            self.urls.add(url)
            inserted = True
        row = [identifier, job['verified_at'], json.dumps(job, ensure_ascii=False)]
        if len(row[2]) > 45000:
            job = dict(job, description=job.get('description', '')[:20000], description_truncated=True)
            row[2] = json.dumps(job, ensure_ascii=False)
        if prior:
            self.tracking.update(range_name=f'A{prior[0]}:C{prior[0]}', values=[row], value_input_option='RAW')
            self.previous[identifier] = (prior[0], job)
        else:
            result = self.tracking.append_row(row, value_input_option='RAW')
            import re
            number = int(re.search(r'![A-Z]+(\d+)', result['updates']['updatedRange']).group(1))
            self.previous[identifier] = (number, job)
        return inserted

    def log(self, summary):
        print('Sheets: appending execution summary')
        self.book.worksheet('EXECUTION_LOGS').append_row(
            ['UK_AGENT', datetime.now(timezone.utc).isoformat(), summary['status'], json.dumps(summary)],
            value_input_option='RAW')
