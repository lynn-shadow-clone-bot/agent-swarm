import os
import re
import json
import logging
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any

try:
    from scripts.db_config import get_connection
    from scripts.config_loader import config
except ImportError:
    from db_config import get_connection
    from config_loader import config

# --- Secrets Management ---

class SecretsManager:
    """
    Manages secure access to sensitive configuration.
    Prioritizes environment variables over config files.
    """
    
    @staticmethod
    def get(key: str, default: Optional[str] = None) -> str:
        """Get a secret from environment variables."""
        return os.environ.get(key, default)

    @staticmethod
    def mask_secret(secret: str) -> str:
        """Mask a secret for logging purposes."""
        if not secret:
            return ""
        if len(secret) <= 4:
            return "*" * len(secret)
        return secret[:2] + "*" * (len(secret) - 4) + secret[-2:]

# --- Input Validation ---

class InputValidator:
    """
    Validates user inputs to prevent injection and ensure data integrity.
    """
    
    MAX_TASK_LENGTH = 1000
    ALLOWED_AGENT_TYPES = {
        "architect", "code-writer", "tester", "code-reviewer", 
        "researcher", "debugger", "documenter", "optimizer"
    }

    @staticmethod
    def validate_task_description(description: str) -> str:
        """
        Validate task description.
        - Must be non-empty string.
        - Must not exceed max length.
        - detailed sanitization if needed.
        """
        if not description or not isinstance(description, str):
            raise ValueError("Task description must be a non-empty string.")
        
        if len(description) > InputValidator.MAX_TASK_LENGTH:
            raise ValueError(f"Task description exceeds maximum length of {InputValidator.MAX_TASK_LENGTH} characters.")
        
        # Basic sanitization: remove potential control characters but allow newlines/tabs
        # For a task description, we generally want to allow most text, but maybe block script tags if it were a web app.
        # Since this is a CLI tool primarily, just ensuring length and type is a good start.
        return description.strip()

    @staticmethod
    def validate_team_config(team_types: List[str]) -> List[str]:
        """
        Validate team configuration.
        - Must be a list of allowed agent types.
        """
        if not team_types or not isinstance(team_types, list):
            raise ValueError("Team configuration must be a list of agent types.")
        
        validated_team = []
        for agent_type in team_types:
            clean_type = agent_type.strip().lower()
            if clean_type not in InputValidator.ALLOWED_AGENT_TYPES:
                raise ValueError(f"Invalid agent type: {clean_type}. Allowed: {', '.join(InputValidator.ALLOWED_AGENT_TYPES)}")
            validated_team.append(clean_type)
            
        return validated_team

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename to prevent directory traversal.
        """
        # Remove path separators and null bytes
        clean_name = os.path.basename(filename)
        clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '', clean_name)
        return clean_name

# --- Audit Logging ---

class AuditLogger:
    """
    Logs security-critical events to a dedicated log file and database.
    """
    
    def __init__(self, log_file="logs/audit.log"):
        self.log_file = log_file
        
        # Ensure log dir exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Setup file logger
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers to avoid duplicates
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
            
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_event(self, event_type: str, user: str, details: Dict[str, Any], status: str = "SUCCESS"):
        """
        Log an audit event.
        
        Args:
            event_type: Category of event (e.g., "TASK_CREATED", "AGENT_SPAWNED", "AUTH_FAILURE")
            user: User or system component initiating the action
            details: Dictionary of event details
            status: Outcome of the event (SUCCESS/FAILURE)
        """
        timestamp = datetime.now().isoformat()
        
        # 1. Log to File
        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "user": user,
            "status": status,
            "details": details
        }
        self.logger.info(json.dumps(log_entry))
        
        # 2. Log to Database (Best Effort)
        try:
            conn = get_connection()
            c = conn.cursor()
            
            # Ensure table exists (handled by migrations ideally, but safe check here)
            # Actually, we should rely on migrations.
            
            c.execute('''
                INSERT INTO audit_logs (event_type, user_id, details, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (event_type, user, json.dumps(details), status, timestamp))
            
            conn.commit()
            conn.close()
        except Exception as e:
            # Fallback to file log for DB error
            self.logger.error(f"Failed to write to audit DB: {e}")

# Global Instance
audit_logger = AuditLogger()
