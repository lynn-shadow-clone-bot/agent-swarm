import os
import yaml
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class DatabaseConfig(BaseModel):
    path: str = Field(default='./swarm.db')
    timeout: float = Field(default=30.0)
    enable_wal: bool = Field(default=True)

class LoggingConfig(BaseModel):
    level: str = Field(default='INFO')
    file: str = Field(default='logs/swarm.log')
    max_bytes: int = Field(default=10485760)
    backup_count: int = Field(default=10)

class OpenClawConfig(BaseModel):
    gateway: str = Field(default='http://127.0.0.1:18789')
    retries: int = Field(default=3)

class Config(BaseModel):
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    openclaw: OpenClawConfig = Field(default_factory=OpenClawConfig)

def load_config() -> Config:
    # Try to find config.yaml in current dir or parent dir
    possible_paths = [
        os.environ.get('SWARM_CONFIG'),
        'config.yaml',
        os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    ]

    config_data: Dict[str, Any] = {}

    for path in possible_paths:
        if path and os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    loaded = yaml.safe_load(f)
                    if loaded:
                        config_data = loaded
                break
            except Exception as e:
                print(f"Warning: Failed to load config from {path}: {e}")

    # Override with env vars
    if 'SWARM_DB' in os.environ:
        if 'database' not in config_data:
            config_data['database'] = {}
        config_data['database']['path'] = os.environ['SWARM_DB']

    if 'OPENCLAW_GATEWAY' in os.environ:
        if 'openclaw' not in config_data:
            config_data['openclaw'] = {}
        config_data['openclaw']['gateway'] = os.environ['OPENCLAW_GATEWAY']

    if 'LOG_LEVEL' in os.environ:
        if 'logging' not in config_data:
            config_data['logging'] = {}
        config_data['logging']['level'] = os.environ['LOG_LEVEL']

    return Config(**config_data)

# Global config instance
config = load_config()
