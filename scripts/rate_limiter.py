import time
import logging
from typing import Tuple

try:
    from scripts.db_config import get_connection
except ImportError:
    from db_config import get_connection

logger = logging.getLogger('rate_limiter')

class RateLimiter:
    """
    Token bucket rate limiter backed by SQLite.
    """

    def __init__(self, key: str, max_tokens: float, refill_rate: float):
        """
        Initialize rate limiter.
        
        Args:
            key: Unique identifier for the limit (e.g., 'task_creation')
            max_tokens: Maximum burst size
            refill_rate: Tokens added per second
        """
        self.key = key
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate

    def _get_tokens(self, conn) -> Tuple[float, float]:
        """Get current tokens and last update time."""
        c = conn.cursor()
        c.execute('SELECT tokens, last_updated FROM rate_limits WHERE key = ?', (self.key,))
        row = c.fetchone()
        
        if row:
            return row[0], row[1]
        else:
            # Initialize if not exists
            now = time.time()
            c.execute('INSERT INTO rate_limits (key, tokens, last_updated) VALUES (?, ?, ?)', 
                      (self.key, self.max_tokens, now))
            conn.commit()
            return self.max_tokens, now

    def acquire(self, tokens: float = 1.0) -> bool:
        """
        Attempt to acquire tokens.
        
        Returns:
            True if tokens acquired, False otherwise.
        """
        conn = get_connection()
        try:
            # Simple optimistic locking (or just serial execution since SQLite handles concurrency reasonably well for this scale)
            # For strict correctness, we'd need a transaction.
            
            with conn: # Transaction context
                current_tokens, last_updated = self._get_tokens(conn)
                now = time.time()
                
                # Refill
                elapsed = now - last_updated
                new_tokens = min(self.max_tokens, current_tokens + elapsed * self.refill_rate)
                
                if new_tokens >= tokens:
                    new_tokens -= tokens
                    conn.execute('UPDATE rate_limits SET tokens = ?, last_updated = ? WHERE key = ?',
                                 (new_tokens, now, self.key))
                    return True
                else:
                    # Update timestamp even if failed? 
                    # Usually better to update to reflect the refill that happened, but not consume.
                    # But for simple rejection, we can leave it.
                    # Actually, we should update the refill so we don't 'lose' the time if we check frequently.
                    conn.execute('UPDATE rate_limits SET tokens = ?, last_updated = ? WHERE key = ?',
                                 (new_tokens, now, self.key))
                    return False
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Fail open or closed? Security -> Closed. Availability -> Open.
            # Let's fail open to avoid blocking legitimate work on DB errors, but log it.
            return True 
        finally:
            conn.close()

# Pre-defined limiters
# Limit task creation to 10 per minute (1 per 6 seconds roughly)
# max_tokens=5, refill=0.16 (1/6)
task_submission_limiter = RateLimiter("task_submission", max_tokens=5, refill_rate=0.2)
