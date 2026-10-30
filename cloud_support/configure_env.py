"""Interactive ECS configuration. Secret values are never printed."""
import argparse
import getpass
import os
from pathlib import Path
from urllib.parse import quote

from run_with_env import read_env

PATH = Path('/etc/tokokita-agent.env')
ap = argparse.ArgumentParser()
ap.add_argument('--rds', action='store_true')
args = ap.parse_args()
values = read_env(PATH) if PATH.exists() else {}

if args.rds:
    host = input('RDS internal hostname (no scheme): ').strip()
    user = input('RDS application user [tokokita]: ').strip() or 'tokokita'
    database = input('Database [tokokita]: ').strip() or 'tokokita'
    password = getpass.getpass('RDS password (hidden): ')
    if not host or not password or any(c.isspace() for c in host):
        raise SystemExit('Hostname and password are required.')
    values['DATABASE_URL'] = (f'mysql+pymysql://{quote(user, safe="")}:'
                              f'{quote(password, safe="")}@{host}:3306/{quote(database, safe="")}')
else:
    base = input('OpenAI-compatible Base URL from Model Studio: ').strip().rstrip('/')
    key = getpass.getpass('Model Studio API Key (hidden): ')
    if not base.startswith('https://') or not base.endswith('/compatible-mode/v1'):
        raise SystemExit('Use the HTTPS OpenAI-compatible endpoint ending in /compatible-mode/v1.')
    if not key or any(c.isspace() for c in base + key):
        raise SystemExit('Base URL and API Key must be non-empty and contain no whitespace.')
    values.update(LLM_BASE_URL=base, LLM_API_KEY=key, LLM_MODEL='qwen-plus',
                  EMBED_MODEL='text-embedding-v3', RETRIEVER='keyword',
                  AUTO_RETRIEVE='true', MAX_TOOL_ROUNDS='4')
if any('\n' in value or '\r' in value for value in values.values()):
    raise SystemExit('Configuration values must be single-line.')
os.umask(0o077)
PATH.write_text(''.join(f'{k}={v}\n' for k, v in values.items()), encoding='utf-8')
PATH.chmod(0o600)
print('Saved /etc/tokokita-agent.env (mode 600). Secret values were not printed.')
