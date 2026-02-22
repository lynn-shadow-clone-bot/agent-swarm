import os
import sqlite3
import logging
import queue
from typing import Optional

try:
    from scripts.config_loader import config
except ImportError:
    from config_loader import config

# Database configuration
DB_PATH = config.database.path
DB_TIMEOUT = config.database.timeout

def create_connection(check_same_thread=True):
    """Create a new database connection with configured pragmas."""
    # Ensure directory exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT, check_same_thread=check_same_thread)

    if config.database.enable_wal:
        try:
            # Enable WAL mode
            conn.execute('PRAGMA journal_mode=WAL;')
            # Normal synchronous mode is safe with WAL and much faster
            conn.execute('PRAGMA synchronous=NORMAL;')
            # Increase cache size (approx 64MB)
            conn.execute('PRAGMA cache_size=-64000;')
            conn.execute('PRAGMA foreign_keys=ON;')
        except Exception as e:
            # We can't rely on logging being configured yet, but we can try
            logging.error(f"Failed to set database pragmas: {e}")

    return conn

def get_connection():
    """Get a fresh database connection (legacy/script usage)."""
    return create_connection(check_same_thread=True)

class ConnectionPool:
    """Simple blocking connection pool for SQLite."""
    def __init__(self, max_connections=10):
        self.max_connections = max_connections
        self.pool = queue.Queue(maxsize=max_connections)

        # Pre-fill pool with connections enabled for multi-thread usage
        for _ in range(max_connections):
            self.pool.put(create_connection(check_same_thread=False))

    def get_connection(self):
        """Get a connection from the pool. Blocks if empty."""
        return self.pool.get()

    def return_connection(self, conn):
        """Return a connection to the pool."""
        try:
            self.pool.put_nowait(conn)
        except queue.Full:
            # Should not happen if logic is correct
            conn.close()

    def close_all(self):
        """Close all connections in the pool."""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except queue.Empty:
                break

_pool: Optional[ConnectionPool] = None

def get_pool():
    """Get or create the global connection pool."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool()
    return _pool
