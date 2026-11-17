"""Conservative UK vacancy screening primitives; missing evidence stays unknown."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

LONDON = ZoneInfo('Europe/London')


def search_since(now):
    """Return the start of the requested search window in London time."""
    if now.tzinfo is None:
        raise ValueError('A timezone-aware execution time is required')
    local = now.astimezone(LONDON)
    last_day = (now.astimezone(ZoneInfo('UTC')) - timedelta(hours=24)).astimezone(LONDON)
    if local.weekday() >= 5:
        monday = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return min(last_day, monday)
    return last_day


def sponsorship(description):
    text = description.lower()
    if re.search(r'\b(?:no|without|cannot offer|does not offer|unable to (?:offer|provide))\s+(?:visa\s+)?sponsorship\b', text) or re.search(r'\bsponsorship\s+(?:is\s+)?not\s+(?:available|offered|provided)\b', text):
        return 'Not Offered'
    if re.search(r'\b(?:visa|skilled worker) sponsorship (?:is |may be )?(?:available|offered|provided)\b', text):
        return 'Available'
    return 'Not Specified'


def clearance(description):
    text = description.lower()
    if re.search(r'\b(?:must|you must|applicants must|candidates must) (?:already |currently )?(?:hold|have|possess) (?:an? |a valid |active |current |existing )*(?:sc|dv|security clearance)\b', text):
        return 'exclude_existing_clearance_required'
    if re.search(r'\b(?:active|current|existing) (?:sc|dv) clearance (?:is )?(?:essential|required|mandatory)\b', text):
        return 'exclude_existing_clearance_required'
    if re.search(r'\b(?:clearance|\bsc\b|\bdv\b)', text):
        return 'review'
    return 'not stated'


def canonical_url(url):
    parts = urlsplit(url)
    if parts.scheme.lower() not in ('https', 'http') or not parts.hostname:
        return ''
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in {'ref', 'source', 'trk'}]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/') or '/', urlencode(sorted(query)), ''))


def same_vacancy(a, b):
    """Match strong identifiers only; similar titles alone do not establish identity."""
    def norm(v):
        return re.sub(r'[^a-z0-9]+', ' ', (v or '').casefold()).strip()
    if not norm(a.get('company')) or norm(a.get('company')) != norm(b.get('company')):
        return False
    aid, bid = norm(a.get('requisition')), norm(b.get('requisition'))
    if aid and bid:
        return aid == bid
    au, bu = canonical_url(a.get('url', '')), canonical_url(b.get('url', ''))
    return bool(au and au == bu)


def sheet_row(job):
    return [job.get(k, '') for k in ('company', 'title', 'location', 'experience', 'sponsorship', 'posted', 'url')] + ['Not Applied']
