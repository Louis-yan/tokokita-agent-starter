"""Add optional RDS storage without replacing the four learner exercises."""
import ast
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / 'app/tools.py'
text = path.read_text(encoding='utf-8')
marker = '# cloud-lab: optional RDS backend'
if marker in text:
    print('RDS adapter already installed; no changes made.')
    raise SystemExit(0)
for name in ['knowledge.py', 'tools.py', 'agent.py']:
    if 'raise NotImplementedError' in (root / 'app' / name).read_text(encoding='utf-8'):
        raise SystemExit('Finish labs 2 and 3, then run all 13 tests before enabling RDS.')
anchor = '        self.ticket_path = data_dir / "tickets.jsonl"'
old = ('        with self._lock, self.ticket_path.open("a", encoding="utf-8") as f:\n'
       '            f.write(json.dumps(record, ensure_ascii=False) + "\\n")')
if text.count(anchor) != 1 or text.count(old) != 1 or 'self.orders.get(' not in text:
    raise SystemExit('Unexpected tools.py structure. Compare it with the supplied starter; nothing was changed.')
text = text.replace('import json\n', 'import json\nimport os\nfrom app.cloud_db import RdsStore\n', 1)
text = text.replace(anchor, anchor + '\n        ' + marker + '\n'
                    '        self._store = None\n'
                    '        if os.getenv("DATABASE_URL"):\n'
                    '            self._store = RdsStore(os.environ["DATABASE_URL"], list(self.orders.values()))\n'
                    '            self.orders = self._store', 1)
text = text.replace(old,
                    '        if self._store is not None:\n'
                    '            self._store.create_ticket(record)\n'
                    '        else:\n'
                    '            with self._lock, self.ticket_path.open("a", encoding="utf-8") as f:\n'
                    '                f.write(json.dumps(record, ensure_ascii=False) + "\\n")', 1)
ast.parse(text)
backup = root / 'cloud_support/pre-rds-tools.py.bak'
if backup.exists():
    raise SystemExit('Backup already exists; inspect the previous attempt before retrying.')
shutil.copy2(path, backup)
shutil.copy2(root / 'cloud_support/rds_backend.py', root / 'app/cloud_db.py')
path.write_text(text, encoding='utf-8')
requirements = root / 'requirements.txt'
r = requirements.read_text(encoding='utf-8')
if 'pymysql' not in r.lower():
    requirements.write_text(r.rstrip() + '\npymysql[rsa]==1.1.1\n', encoding='utf-8')
print('RDS adapter installed; learner functions preserved. Install requirements, configure RDS, and verify it.')
