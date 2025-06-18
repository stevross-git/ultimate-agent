#!/usr/bin/env python3
"""
ultimate_agent/config/settings.py
Configuration management for the agent
"""

import os
import configparser
from typing import Any, Optional


class ConfigManager:
    """Manages configuration settings for the agent"""
    
    def __init__(self, config_file: str = "ultimate_agent_config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self._load_or_create_config()
    
    def _load_or_create_config(self):
        """Load existing config or create default configuration"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self._create_default_config()
            self._save_config()
    
    def _create_default_config(self):
        """Create default configuration sections"""
        # Main settings
        self.config['DEFAULT'] = {


            'node_url': 'https://srvnodes.peoplesainetwork.com',

            'dashboard_port': '8080',
            'heartbeat_interval': '30',
            'auto_start_tasks': 'true',
            'max_concurrent_tasks': '3'
        }
        
        # AI Training settings
        self.config['AI_TRAINING'] = {
            'enabled': 'true',
            'max_concurrent_training': '2',
            'gpu_enabled': 'auto',
            'training_data_path': './training_data',
            'model_cache_size': '1000',
            'training_timeout': '3600'
        }
        
        # Blockchain settings
        self.config['BLOCKCHAIN'] = {
            'enabled': 'true',
            'smart_contracts_enabled': 'true',
            'multi_currency_support': 'true',
            'transaction_pool_size': '100',
            'gas_limit': '150000',
            'gas_price': '20'
        }
        
        # Task Control settings
        self.config['TASK_CONTROL'] = {
            'enabled': 'true',
            'progress_reporting': 'true',
            'real_time_updates': 'true',
            'task_timeout': '1800',
            'retry_failed_tasks': 'true'
        }
        
        # Security settings
        self.config['SECURITY'] = {
            'encryption_enabled': 'true',
            'auth_token_expiry': '3600',
            'max_login_attempts': '3',
            'secure_communication': 'true'
        }
        
        # Monitoring settings
        self.config['MONITORING'] = {
            'metrics_enabled': 'true',
            'log_level': 'INFO',
            'performance_tracking': 'true',
            'alert_thresholds': 'true'
        }
        
        # Database settings
        self.config['DATABASE'] = {
            'type': 'sqlite',
            'path': './ultimate_agent.db',
            'backup_enabled': 'true',
            'vacuum_interval': '86400'
        }
        
        # Network settings
        self.config['NETWORK'] = {
            'connection_timeout': '30',
            'retry_attempts': '3',
            'use_ssl': 'true',
            'verify_ssl': 'true',
            'compression_enabled': 'true'
        }
        
        # Dashboard settings
        self.config['DASHBOARD'] = {
            'host': '127.0.0.1',
            'cors_enabled': 'true',
            'websocket_enabled': 'true',
            'static_files_enabled': 'true'
        }

        # Plugin settings
        self.config['PLUGINS'] = {
            'enabled': 'true',
            'plugin_directory': './plugins',
            'auto_load': 'true',
            'sandbox_enabled': 'true'
        }

        # Local AI settings
        self.config['LOCAL_AI'] = {
            'enabled': 'true',
            'auto_model_management': 'true',
            'preload_models': 'false',
            'prefer_local_ai': 'true',
            'fallback_to_cloud': 'true',
            'max_concurrent_requests': '3'
        }

        # Ollama settings
        self.config['OLLAMA'] = {
            'host': 'localhost',
            'port': '11434',
            'timeout': '30.0',
            'auto_pull_models': 'false',
            'model_selection_strategy': 'auto',
            'default_model': 'auto'
        }
    
    def _save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            self.config.write(f)
    
    def get(self, section: str, key: str, fallback: Any = None) -> str:
        """Get configuration value"""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return str(fallback)
            raise
    
    def getboolean(self, section: str, key: str, fallback: bool = False) -> bool:
        """Get boolean configuration value"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        """Get integer configuration value"""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def getfloat(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Get float configuration value"""
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def set(self, section: str, key: str, value: str):
        """Set configuration value"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
        self._save_config()
    
    def has_section(self, section: str) -> bool:
        """Check if section exists"""
        return self.config.has_section(section)
    
    def has_option(self, section: str, key: str) -> bool:
        """Check if option exists in section"""
        return self.config.has_option(section, key)
    
    def get_section(self, section: str) -> dict:
        """Get all options in a section as dictionary"""
        try:
            return dict(self.config.items(section))
        except configparser.NoSectionError:
            return {}
    
    def reload(self):
        """Reload configuration from file"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self._create_default_config()
            self._save_config()
    
    def validate_config(self) -> bool:
        """Validate configuration settings"""
        required_sections = ['DEFAULT', 'AI_TRAINING', 'BLOCKCHAIN', 'SECURITY']
        
        for section in required_sections:
            if not self.has_section(section):
                print(f"⚠️ Missing required config section: {section}")
                return False
        
        # Validate specific settings
        try:
            port = self.getint('DEFAULT', 'dashboard_port')
            if not (1000 <= port <= 65535):
                print(f"⚠️ Invalid dashboard port: {port}")
                return False
            
            heartbeat = self.getint('DEFAULT', 'heartbeat_interval')
            if heartbeat < 10:
                print(f"⚠️ Heartbeat interval too short: {heartbeat}")
                return False
            
            return True
            
        except Exception as e:
            print(f"⚠️ Config validation error: {e}")
            return False
    
    def get_ai_config(self) -> dict:
        """Get AI-specific configuration"""
        return self.get_section('AI_TRAINING')
    
    def get_blockchain_config(self) -> dict:
        """Get blockchain-specific configuration"""
        return self.get_section('BLOCKCHAIN')
    
    def get_security_config(self) -> dict:
        """Get security-specific configuration"""
        return self.get_section('SECURITY')
    
    def get_network_config(self) -> dict:
        """Get network-specific configuration"""
        return self.get_section('NETWORK')
    
    def get_dashboard_config(self) -> dict:
        """Get dashboard-specific configuration"""
        return self.get_section('DASHBOARD')
    
    def export_config(self, export_path: str):
        """Export configuration to specified path"""
        with open(export_path, 'w') as f:
            self.config.write(f)
        print(f"📄 Configuration exported to {export_path}")
    
    def import_config(self, import_path: str):
        """Import configuration from specified path"""
        if os.path.exists(import_path):
            backup_path = f"{self.config_file}.backup"
            # Create backup of current config
            with open(backup_path, 'w') as f:
                self.config.write(f)
            
            # Load new config
            self.config.read(import_path)
            self._save_config()
            print(f"📄 Configuration imported from {import_path}")
            print(f"💾 Backup saved to {backup_path}")
        else:
            raise FileNotFoundError(f"Config file not found: {import_path}")
