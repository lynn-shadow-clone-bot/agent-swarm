import sqlite3
import logging
import os

try:
    from scripts.db_config import get_connection
except ImportError:
    from db_config import get_connection

logger = logging.getLogger('db_migrations')

def apply_migrations():
    """Apply pending database migrations."""
    conn = get_connection()
    c = conn.cursor()

    # 0. Ensure version table
    c.execute('''
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Check version
    c.execute('SELECT MAX(version) FROM schema_version')
    row = c.fetchone()
    current_version = row[0] if row[0] is not None else 0

    # Define migrations
    # Version 1: Initial Schema (Tasks, Agents, Messages)
    migrations_to_apply = {
        1: [
            '''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                team_config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                result TEXT,
                output_dir TEXT
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                agent_type TEXT,
                status TEXT DEFAULT 'pending',
                session_key TEXT,
                spawned_at TIMESTAMP,
                completed_at TIMESTAMP,
                result TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                agent_id TEXT,
                message_type TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            '''
        ]
    }

    max_version = max(migrations_to_apply.keys())

    if current_version < max_version:
        logger.info(f"Migrating database from version {current_version} to {max_version}...")

        for version in range(current_version + 1, max_version + 1):
            if version in migrations_to_apply:
                logger.info(f"Applying migration v{version}...")
                for sql in migrations_to_apply[version]:
                    try:
                        c.execute(sql)
                    except sqlite3.OperationalError as e:
                        logger.warning(f"Migration step failed (might be idempotent): {e}")

                c.execute('INSERT INTO schema_version (version) VALUES (?)', (version,))
                conn.commit()

        logger.info("Migrations complete.")
    else:
        logger.info("Database schema is up to date.")

    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    apply_migrations()
