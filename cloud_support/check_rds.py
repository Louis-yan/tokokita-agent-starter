"""Direct database evidence. A working order reply alone cannot prove use of RDS."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.cloud_db import RdsStore

ap = argparse.ArgumentParser()
ap.add_argument('--import-tickets', type=Path)
args = ap.parse_args()
root = Path(__file__).resolve().parents[1]
store = RdsStore(os.environ['DATABASE_URL'], json.loads((root / 'data/orders.json').read_text()))
if args.import_tickets:
    store.import_tickets(args.import_tickets)
orders, tickets = store.counts()
print(f'backend=RDS MySQL; orders={orders}; tickets={tickets}')
with store.connection() as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT ticket_id,category,order_id FROM tickets ORDER BY created_at DESC LIMIT 3')
        for row in cur.fetchall():
            print('ticket:', *row)
