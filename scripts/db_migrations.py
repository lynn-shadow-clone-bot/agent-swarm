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
        ],
        2: [
            '''
            ALTER TABLE agents ADD COLUMN priority INTEGER DEFAULT 0;
            ''',
            '''
            CREATE TABLE IF NOT EXISTS task_cache (
                task_hash TEXT PRIMARY KEY,
                agent_type TEXT,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            '''
        ],
        3: [
            '''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                user_id TEXT,
                details TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ''',
            '''
            CREATE TABLE IF NOT EXISTS rate_limits (
                key TEXT PRIMARY KEY,
                tokens REAL,
                last_updated TIMESTAMP
            );
            '''
        ],
        4: [
            '''
            CREATE TABLE IF NOT EXISTS agent_registry (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                model TEXT DEFAULT 'kimi-coding/k2p5',
                thinking TEXT DEFAULT 'high',
                description TEXT,
                capabilities TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ''',
            # Seed with default agents from JSON templates
            '''INSERT OR IGNORE INTO agent_registry (id, name, type, model, thinking, description, capabilities) VALUES
                ('code-writer', 'Code Writer', 'code-writer', 'kimi-coding/k2p5', 'high', 
                 'Senior software engineer. Writes clean, efficient, well-documented code.',
                 'implementation,coding,development');
            ''',
            '''INSERT OR IGNORE INTO agent_registry (id, name, type, model, thinking, description, capabilities) VALUES
                ('code-reviewer', 'Code Reviewer', 'code-reviewer', 'kimi-coding/k2p5', 'high',
                 'Analyzes code for bugs, security issues, performance problems, and style violations.',
                 'review,quality,security');
            ''',
            '''INSERT OR IGNORE INTO agent_registry (id, name, type, model, thinking, description, capabilities) VALUES
                ('tester', 'Tester', 'tester', 'kimi-coding/k2p5', 'high',
                 'Writes comprehensive tests and performs QA. Ensures code works as expected.',
                 'testing,qa,validation');
            ''',
            '''INSERT OR IGNORE INTO agent_registry (id, name, type, model, thinking, description, capabilities) VALUES
                ('researcher', 'Researcher', 'researcher', 'kimi-coding/k2p5', 'high',
                 'Conducts web research and finds documentation. Discovers solutions and best practices.',
                 'research,discovery,documentation');
            ''',
            # Additional useful agents
            '''INSERT OR IGNORE INTO agent_registry (id, name, type, model, thinking, description, capabilities) VALUES
                ('debugger', 'Debugger', 'debugger', 'kimi-coding/k2p5', 'high',
                 'Expert at finding and fixing bugs. Analyzes error logs and traces issues to root cause.',
                 'debugging,troubleshooting,error-analysis');
            ''',
            '''INSERT OR IGNORE INTO agent_registry (id, name, type, model, thinking, description, capabilities) VALUES
                ('architect', 'System Architect', 'architect', 'kimi-coding/k2p5', 'high',
                 'Designs system architecture and makes high-level technical decisions. Plans scalable solutions.',
                 'architecture,design,planning,system-design');
            ''',
            '''INSERT OR IGNORE INTO agent_registry (id, name, type, model, thinking, description, capabilities) VALUES
                ('documenter', 'Documenter', 'documenter', 'kimi-coding/k2p5', 'high',
                 'Writes clear documentation, comments, and guides. Explains complex concepts simply.',
                 'documentation,writing,guides,explanations');
            ''',
            '''INSERT OR IGNORE INTO agent_registry (id, name, type, model, thinking, description, capabilities) VALUES
                ('optimizer', 'Optimizer', 'optimizer', 'kimi-coding/k2p5', 'high',
                 'Improves performance and refactors code. Finds bottlenecks and optimizes resource usage.',
                 'optimization,performance,refactoring');
            ''',
            '''INSERT OR IGNORE INTO agent_registry (id, name, type, model, thinking, description, capabilities) VALUES
                ('devops', 'DevOps Engineer', 'devops', 'kimi-coding/k2p5', 'high',
                 'Handles deployment, CI/CD, infrastructure, and operational tasks.',
                 'devops,deployment,cicd,infrastructure,docker,kubernetes');
            ''',
            '''INSERT OR IGNORE INTO agent_registry (id, name, type, model, thinking, description, capabilities) VALUES
                ('security-expert', 'Security Expert', 'security-expert', 'kimi-coding/k2p5', 'high',
                 'Audits code for security vulnerabilities. Implements secure coding practices.',
                 'security,auditing,vulnerabilities,secure-coding');
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
