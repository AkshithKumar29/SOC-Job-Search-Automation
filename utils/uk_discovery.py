"""Public Greenhouse discovery, with conservative review and publication-date checks."""
import html
import re
import time
from datetime import datetime, timezone
import requests
from utils.uk_screening import clearance, sponsorship, search_since


def fetch_board(board, company, now=None):
    now = now or datetime.now(timezone.utc)
    base = f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs'
    session = requests.Session()
    session.headers['User-Agent'] = 'SOC-Job-Search-Automation/1.0'
    response = session.get(base, params={'content': 'true'}, timeout=30)
    response.raise_for_status()
    jobs = response.json()['jobs']
    records = []
    for item in jobs:
        title = item['title']
        location = item.get('location', {}).get('name', '')
        if not re.search(r'\b(?:security|cyber|soc|siem|threat|incident|mdr)\b', title, re.I):
            continue
        if re.search(r'\b(?:sales|account manager|marketing|recruiter|business development)\b', title, re.I):
            continue
        if not re.search(r'\b(?:United Kingdom|UK|England|Scotland|Wales|Northern Ireland|London|Belfast|Manchester|Edinburgh|Cardiff)\b', location, re.I):
            continue
        time.sleep(0.5)
        response = session.get(f'{base}/{item["id"]}', timeout=30)
        response.raise_for_status()
        detail = response.json()
        text = re.sub('<[^>]+>', ' ', html.unescape(detail.get('content', '')))
        published = detail.get('first_published', '')
        decision = 'review'
        reason = 'eligibility requires review'
        if re.search(r'\b(?:senior|lead|principal|staff|manager|director)\b', title, re.I):
            decision, reason = 'reject', 'senior title'
        elif clearance(text).startswith('exclude'):
            decision, reason = 'reject', 'existing clearance required'
        elif not published:
            reason = 'publication date unknown'
        else:
            date = datetime.fromisoformat(published.replace('Z', '+00:00'))
            if date < search_since(now) or date > now:
                decision, reason = 'reject', 'outside posting window'
            else:
                decision, reason = assess(title, text)
        records.append(dict(company=company, title=title, location=location,
            requisition=detail.get('requisition_id', ''), source_id=str(item['id']),
            url=detail['absolute_url'], description=text, posted=published,
            sponsorship=sponsorship(text), clearance=clearance(text), decision=decision,
            experience='Not Specified', application_url_verification='live employer-authorised ATS record',
            reason=reason, first_seen=now.isoformat(), verified_at=now.isoformat(),
            source='Greenhouse public Job Board API'))
    return {'source': company, 'status': 'successfully searched', 'listings_scanned': len(jobs), 'records': records}


def assess(title, text):
    if re.search(r'\b(?:two|three|four|five|six|seven|eight|nine|ten)\s+years?\b', text, re.I):
        return 'review', 'experience requirement needs contextual verification'
    if re.search(r'\b(?:nationality|citizen|indefinite leave|permanent right|unrestricted right)\b', text, re.I):
        return 'review', 'right-to-work or nationality restriction needs verification'
    if re.search(r'\b(?:[2-9]|1[0-9])\+?\s*(?:-|to)?\s*\d*\s*years?\b', text, re.I):
        return 'review', 'experience requirement needs contextual verification'
    if re.search(r'\b(?:junior|graduate|trainee|entry[- ]level|level 1|tier 1|l1|associate)\b', title, re.I):
        return 'include', 'explicit beginner title; verify full eligibility before applying'
    if re.search(r'\bno (?:prior |professional )?experience (?:is )?(?:required|necessary)\b', text, re.I):
        return 'include', 'explicit beginner experience evidence'
    return 'review', 'beginner suitability not established'
