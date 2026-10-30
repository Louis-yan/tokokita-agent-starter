"""Optional RDS backend. Each operation uses its own connection for thread safety."""
import json
from pathlib import Path
from urllib.parse import urlparse, unquote


class RdsStore:
    def __init__(self, database_url: str, orders: list[dict]):
        import pymysql
        u = urlparse(database_url)
        if u.scheme != 'mysql+pymysql' or not u.hostname or not u.path.strip('/'):
            raise ValueError('DATABASE_URL must identify an RDS MySQL database.')
        self.pymysql = pymysql
        self.options = dict(host=u.hostname, port=u.port or 3306,
                            user=unquote(u.username or ''), password=unquote(u.password or ''),
                            database=unquote(u.path.lstrip('/')), charset='utf8mb4',
                            connect_timeout=5, read_timeout=10, write_timeout=10)
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''CREATE TABLE IF NOT EXISTS orders (
                    order_id VARCHAR(40) PRIMARY KEY, phone VARCHAR(40) NOT NULL,
                    status VARCHAR(80) NOT NULL, items TEXT NOT NULL, courier VARCHAR(120),
                    tracking_no VARCHAR(120), estimated_delivery VARCHAR(120), payment VARCHAR(120))''')
                cur.execute('''CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id VARCHAR(40) PRIMARY KEY, category VARCHAR(80) NOT NULL,
                    summary TEXT NOT NULL, order_id VARCHAR(40), created_at VARCHAR(80) NOT NULL)''')
                for o in orders:
                    cur.execute('''INSERT IGNORE INTO orders
                        (order_id,phone,status,items,courier,tracking_no,estimated_delivery,payment)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
                        (o['order_id'], o['phone'], o['status'], json.dumps(o['items'], ensure_ascii=False),
                         o.get('courier'), o.get('tracking_no'), o.get('estimated_delivery'), o['payment']))
            conn.commit()

    def connection(self):
        return self.pymysql.connect(**self.options)

    def get(self, order_id, default=None):
        with self.connection() as conn:
            with conn.cursor(self.pymysql.cursors.DictCursor) as cur:
                cur.execute('SELECT * FROM orders WHERE order_id=%s', (order_id,))
                row = cur.fetchone()
        if row is None:
            return default
        row['items'] = json.loads(row['items'])
        return row

    def create_ticket(self, record):
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''INSERT IGNORE INTO tickets
                    (ticket_id,category,summary,order_id,created_at) VALUES (%s,%s,%s,%s,%s)''',
                    (record['ticket_id'], record['category'], record['summary'],
                     record.get('order_id') or None, record['created_at']))
            conn.commit()

    def import_tickets(self, path: Path):
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                if line.strip():
                    self.create_ticket(json.loads(line))

    def counts(self):
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) FROM orders')
                orders = cur.fetchone()[0]
                cur.execute('SELECT COUNT(*) FROM tickets')
                tickets = cur.fetchone()[0]
        return orders, tickets
