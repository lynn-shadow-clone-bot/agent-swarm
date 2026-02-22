import os
import sqlite3
import logging

try:
    from scripts.config_loader import config
except ImportError:
    from config_loader import config

# Database configuration
DB_PATH = config.database.path
DB_TIMEOUT = config.database.timeout

def get_connection():
    """Get a database connection with configured pragmas."""
    # Ensure directory exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)

    if config.database.enable_wal:
        try:
            # Enable WAL mode
            conn.execute('PRAGMA journal_mode=WAL;')
            # Normal synchronous mode is safe with WAL and much faster
            conn.execute('PRAGMA synchronous=NORMAL;')
            # Increase cache size (negative value = pages, positive = bytes? No, negative is kb usually in some sqlites, but actually:
            # "If N is negative, the number of cache pages is adjusted to use approximately abs(N)*1024 bytes of memory."
            # So -64000 is approx 64MB.
            conn.execute('PRAGMA cache_size=-64000;')
            conn.execute('PRAGMA foreign_keys=ON;')
        except Exception as e:
            # We can't rely on logging being configured yet, but we can try
            logging.error(f"Failed to set database pragmas: {e}")

    return conn
