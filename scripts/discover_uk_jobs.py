"""Read-only live discovery pilot. Writes private results locally, never to public logs."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.uk_discovery import fetch_board

if __name__ == '__main__':
    result = fetch_board('huntress', 'Huntress')
    output = Path('private/uk_discovery.json')
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f'Live source searched: {result["source"]}; listings scanned: {result["listings_scanned"]}; UK security records: {len(result["records"])}')
    print('Eligibility review required; no jobs written to Sheets.')
