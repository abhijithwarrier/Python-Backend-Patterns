"""Programmer: python_scripts (Abhijith Warrier)
PYTHON BACKEND PATTERNS — IDEMPOTENCY PATTERN
Prevent duplicate local order creation when the same API operation is retried.
Save the order and replayable response atomically in SQLite. This runnable,
standard-library example models an API handler; it does not start an HTTP server.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
import json
import sqlite3


# 1. Keep the business operation and its idempotency record in the SAME database.
def initialize(db):
    with closing(sqlite3.connect(db)) as con, con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY, customer TEXT NOT NULL,
            product TEXT NOT NULL, quantity INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS requests (
            customer TEXT NOT NULL, operation TEXT NOT NULL, key TEXT NOT NULL,
            payload TEXT NOT NULL, status INTEGER NOT NULL, body TEXT NOT NULL,
            PRIMARY KEY (customer, operation, key)
        );
        """)


def validate(key, payload):
    if not isinstance(key, str) or not key.strip() or len(key) > 128:
        raise ValueError('Supply a nonempty idempotency key of at most 128 characters.')
    if not isinstance(payload, dict) or set(payload) != {'product', 'quantity'}:
        raise ValueError('Expected product and quantity only.')
    if not isinstance(payload['product'], str) or not payload['product'].strip():
        raise ValueError('product must be a nonempty string.')
    if type(payload['quantity']) is not int or not 1 <= payload['quantity'] <= 100:
        raise ValueError('quantity must be an integer from 1 to 100.')
    # Canonical JSON is sufficient for this small, validated schema.
    return json.dumps(payload, sort_keys=True, separators=(',', ':'))


class KeyConflict(Exception):
    """One operation key cannot represent two different payloads."""


# 2. The customer comes from trusted authentication, never an unchecked header.
def create_order(db, customer, key, payload):
    canonical = validate(key, payload)
    operation = 'POST /orders'
    with closing(sqlite3.connect(db, timeout=5, isolation_level=None)) as con:
        try:
            # Acquire SQLite's write transaction BEFORE checking the key.
            # Other writers wait (up to timeout) rather than both seeing a miss.
            con.execute('BEGIN IMMEDIATE')
            saved = con.execute(
                'SELECT payload, status, body FROM requests '
                'WHERE customer=? AND operation=? AND key=?',
                (customer, operation, key),
            ).fetchone()
            if saved:
                if saved[0] != canonical:
                    raise KeyConflict('Key already used with different request data.')
                con.commit()
                return saved[1], json.loads(saved[2])

            order_id = con.execute(
                'INSERT INTO orders(customer, product, quantity) VALUES (?, ?, ?)',
                (customer, payload['product'], payload['quantity']),
            ).lastrowid
            status = 201
            body = {'order_id': order_id, 'product': payload['product'],
                    'quantity': payload['quantity']}
            con.execute(
                'INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?)',
                (customer, operation, key, canonical, status, json.dumps(body)),
            )
            con.commit()  # Order + response become durable together.
            return status, body
        except Exception:
            con.rollback()  # Failed work is not cached by this example.
            raise


# 3. Framework-independent API boundary: (status code, JSON response body).
def api_request(db, customer, key, payload):
    try:
        return create_order(db, customer, key, payload)
    except ValueError as exc:
        return 400, {'error': str(exc)}
    except KeyConflict as exc:
        return 409, {'error': str(exc)}
    # Database/server failures propagate to the application's centralized handler.


def order_count(db):
    with closing(sqlite3.connect(db)) as con:
        return con.execute('SELECT COUNT(*) FROM orders').fetchone()[0]


# 4. Reproduce a lost response, retry, mismatch and a genuinely NEW operation.
def demo():
    payload = {'product': 'book', 'quantity': 1}
    with TemporaryDirectory() as tmp:
        db = Path(tmp) / 'orders.sqlite'
        initialize(db)
        first = api_request(db, 'customer-7', 'req-42', payload)
        # Imagine the first response is lost AFTER the transaction commits.
        retry = api_request(db, 'customer-7', 'req-42', payload)
        assert first == retry and order_count(db) == 1
        print('First:', first)
        print('Retry:', retry)
        print('Orders after retry:', order_count(db))
        conflict = api_request(db, 'customer-7', 'req-42', {**payload, 'quantity': 2})
        assert conflict[0] == 409 and order_count(db) == 1
        print('Changed payload:', conflict[0])
        fresh = api_request(db, 'customer-7', 'req-43', payload)
        assert fresh[1]['order_id'] == 2 and order_count(db) == 2
        print('New key:', fresh)
        print('Orders after new key:', order_count(db))

        # 5. Eight concurrent calls, separate connections, one shared database.
        concurrent_db = Path(tmp) / 'concurrent.sqlite'
        initialize(concurrent_db)
        gate = Barrier(8)
        def submit(_):
            gate.wait()
            return api_request(concurrent_db, 'customer-7', 'same-key', payload)
        with ThreadPoolExecutor(max_workers=8) as pool:
            replies = list(pool.map(submit, range(8)))
        assert all(reply == replies[0] for reply in replies)
        assert order_count(concurrent_db) == 1
        print('Concurrent calls: 8; orders: 1; identical replies: True')

        # Scope the key to the authenticated customer and operation.
        assert api_request(db, 'customer-8', 'req-42', payload)[0] == 201
        assert order_count(db) == 3
        assert api_request(db, 'customer-7', '', payload)[0] == 400
        assert api_request(db, 'customer-7', 'bad', {**payload, 'quantity': True})[0] == 400
        # JSON field order does not change the request identity.
        assert api_request(db, 'customer-7', 'req-42', {'quantity': 1, 'product': 'book'}) == first

        # 6. Inject a record-write failure: the order must roll back too.
        failed_db = Path(tmp) / 'rollback.sqlite'
        initialize(failed_db)
        with closing(sqlite3.connect(failed_db)) as con, con:
            con.execute("CREATE TRIGGER fail_record BEFORE INSERT ON requests "
                        "BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
        try:
            create_order(failed_db, 'customer-7', 'req-42', payload)
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError('Expected injected failure')
        assert order_count(failed_db) == 0
        with closing(sqlite3.connect(failed_db)) as con, con:
            con.execute('DROP TRIGGER fail_record')
        assert api_request(failed_db, 'customer-7', 'req-42', payload)[0] == 201
        assert order_count(failed_db) == 1
        print('Scope, validation, canonicalization and rollback checks: passed')


if __name__ == '__main__':
    demo()

# Production boundaries:
# - Keep the SAME key for retries; use a fresh random key for a new operation.
# - This demo retains records indefinitely. Define a retention/retry window.
# - SQLite serializes writers; handle lock timeouts with the same-key retry policy.
# - A local transaction cannot undo an external payment/email. Coordinate those
#   separately (provider idempotency and/or transactional outbox + deduplication).
# - This is not a universal distributed exactly-once guarantee.
