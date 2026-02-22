import os
import sqlite3
from contextlib import contextmanager

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'swarm.db')
DB_TIMEOUT = 30.0

@contextmanager
def get_db_conn():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
