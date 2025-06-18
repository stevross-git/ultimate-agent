"""
Ultimate Agent Configuration Settings
"""


from typing import Dict, Any
import os
import uuid
from pathlib import Path
from typing import List
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:  # Graceful fallback if pydantic_settings isn't installed
    class BaseSettings:  # type: ignore[misc]
        """Fallback base class providing no functionality."""
        pass

    def Field(default=None, **kwargs):  # type: ignore[misc]
        return default


class Settings(BaseSettings):
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    ai_enabled: bool = Field(default=True)
    tasks_enabled: bool = Field(default=True)
    dashboard_enabled: bool = Field(default=True)
    blockchain_enabled: bool = Field(default=False)

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=5000)

    database_url: str = Field(default="sqlite:///ultimate_agent.db")

    ai_model_path: str = Field(default="./models")
    max_ai_workers: int = Field(default=4)

    max_concurrent_tasks: int = Field(default=10)
    task_timeout: int = Field(default=300)

    api_key: str | None = Field(default=None)
    secret_key: str = Field(default="dev-secret-key")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration values"""
    required_keys = ['host', 'port', 'secret_key']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required configuration: {key}")
    
    if not isinstance(config['port'], int) or config['port'] < 1 or config['port'] > 65535:
        raise ValueError("Port must be between 1 and 65535")
    
    return True

def get_config() -> Dict[str, Any]:
    """Get configuration dictionary"""
    config = {
        # Core settings
        'debug': os.getenv('DEBUG', 'false').lower() == 'true',
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        
        # Module toggles
        'ai_enabled': os.getenv('AI_ENABLED', 'true').lower() == 'true',
        'tasks_enabled': os.getenv('TASKS_ENABLED', 'true').lower() == 'true',
        'dashboard_enabled': os.getenv('DASHBOARD_ENABLED', 'true').lower() == 'true',
        'blockchain_enabled': os.getenv('BLOCKCHAIN_ENABLED', 'false').lower() == 'true',
        
        # Network settings
        'host': os.getenv('HOST', '0.0.0.0'),
        'port': int(os.getenv('PORT', '8080')),
        
        # Database settings
        'database_url': os.getenv('DATABASE_URL', 'sqlite:///ultimate_agent.db'),
        
        # AI settings
        'ai_model_path': os.getenv('AI_MODEL_PATH', './models'),
        'max_ai_workers': int(os.getenv('MAX_AI_WORKERS', '4')),
        
        # Task settings
        'max_concurrent_tasks': int(os.getenv('MAX_CONCURRENT_TASKS', '10')),
        'task_timeout': int(os.getenv('TASK_TIMEOUT', '300')),
        
        # Security settings
        'api_key': os.getenv('API_KEY'),
        'secret_key': os.getenv('SECRET_KEY', 'dev-secret-key'),
    }
    
    # Validate configuration before returning
    validate_config(config)
    return config

# Legacy compatibility
LOG_DIR = "logs"
DATABASE_PATH = "ultimate_agent.db"

# ✅ Now define settings without importing it prematurely
settings = get_config()
