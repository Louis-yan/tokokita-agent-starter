"""Save the latest timestamped evaluation report under an explicit label."""
import argparse
import json
import re
import shutil
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('label')
ap.add_argument('--expected-url')
args = ap.parse_args()
if Path(args.label).name != args.label:
    raise SystemExit('Label must be a filename, not a path.')
reports = [p for p in Path('eval').glob('report-*.json')
           if re.fullmatch(r'report-\d{8}-\d{6}\.json', p.name)]
if not reports:
    raise SystemExit('No timestamped report was found. Run the evaluation first.')
latest = max(reports, key=lambda p: p.stat().st_mtime_ns)
data = json.loads(latest.read_text(encoding='utf-8'))
if args.expected_url and data['url'] != args.expected_url.rstrip('/'):
    raise SystemExit('Latest report belongs to another endpoint. Do not mislabel it.')
Path('交付物').mkdir(exist_ok=True)
dest = Path('交付物') / (args.label + '.json')
if dest.exists():
    raise SystemExit('Label already exists. Use a new label to preserve the earlier evidence.')
shutil.copy2(latest, dest)
print(f'{dest}: {data["passed"]}/{data["total"]}; url={data["url"]}')
