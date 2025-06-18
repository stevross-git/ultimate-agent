#!/usr/bin/env python3
"""
Ultimate Agent Utilities - Complete Version
Combines existing functions with missing classes
"""

import logging
import sys
import json
import time
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, List, Optional


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Setup logging for a module"""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent.parent


def handle_exception(logger, operation: str, exception: Exception, reraise: bool = False):
    """Standardized exception handling"""
    logger.error(f"❌ Error in {operation}: {exception}")
    if reraise:
        raise exception


def safe_json_serialize(obj):
    """Safely serialize objects to JSON"""
    try:
        return json.dumps(obj, default=str, indent=2)
    except Exception as e:
        return f"{{\"error\": \"Serialization failed: {str(e)}\"}}"


class AgentUtils:
    """Utility functions for the agent - Required by main agent code"""
    
    @staticmethod
    def check_dependencies() -> Dict[str, Any]:
        """Check if required dependencies are available"""
        required_deps = [
            'requests', 'flask', 'numpy', 'psutil', 
            'torch', 'cryptography', 'web3'
        ]
        optional_deps = [
            'flask_cors', 'flask_socketio', 'ollama'
        ]
        
        missing_required = []
        missing_optional = []
        
        for dep in required_deps:
            try:
                __import__(dep)
            except ImportError:
                missing_required.append(dep)
        
        for dep in optional_deps:
            try:
                __import__(dep)
            except ImportError:
                missing_optional.append(dep)
        
        return {
            'all_required_available': len(missing_required) == 0,
            'missing_required': missing_required,
            'missing_optional': missing_optional,
            'total_required': len(required_deps),
            'total_optional': len(optional_deps)
        }
    
    @staticmethod
    def format_uptime(seconds: float) -> str:
        """Format uptime in human readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    @staticmethod
    def format_bytes(bytes_value: int) -> str:
        """Format bytes in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    @staticmethod
    def safe_json_serialize(obj: Any) -> Any:
        """Safely serialize object for JSON"""
        if hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        return str(obj)


class AsyncTaskRunner:
    """Helper for running async tasks - Required by main agent code"""
    
    def __init__(self):
        self.loop = None
    
    def run_async(self, coro):
        """Run async coroutine safely"""
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create a new task
                return asyncio.create_task(coro)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop exists, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
    
    async def safe_await(self, coro):
        """Safely await a coroutine"""
        try:
            return await coro
        except Exception as e:
            print(f"Async task error: {e}")
            return None


class PerformanceProfiler:
    """Simple performance profiler - Required by main agent code"""
    
    def __init__(self):
        self.timings = {}
    
    def start_timer(self, name: str):
        """Start timing an operation"""
        self.timings[name] = time.time()
    
    def end_timer(self, name: str) -> float:
        """End timing and return duration"""
        if name in self.timings:
            duration = time.time() - self.timings[name]
            del self.timings[name]
            return duration
        return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'active_timers': list(self.timings.keys()),
            'profiler_active': True
        }


# Additional utility functions for common operations
def ensure_directory(path: Path) -> Path:
    """Ensure directory exists, create if it doesn't"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json_file(file_path: Path, default: Any = None) -> Any:
    """Safely load JSON file"""
    try:
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return default
    except Exception as e:
        print(f"Error loading JSON file {file_path}: {e}")
        return default


def save_json_file(file_path: Path, data: Any) -> bool:
    """Safely save JSON file"""
    try:
        ensure_directory(file_path.parent)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        print(f"Error saving JSON file {file_path}: {e}")
        return False


def get_system_info() -> Dict[str, Any]:
    """Get basic system information"""
    try:
        import platform
        import psutil
        
        return {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_gb': round(psutil.virtual_memory().total / (1024**3), 1),
            'disk_usage': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:\\').percent
        }
    except Exception as e:
        return {
            'platform': 'unknown',
            'error': str(e)
        }


def is_port_available(port: int, host: str = 'localhost') -> bool:
    """Check if a port is available"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result != 0
    except Exception:
        return False


def find_available_port(start_port: int = 8080, max_attempts: int = 100) -> int:
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(port):
            return port
    return start_port  # Fallback to original port


# Export all utilities for import
__all__ = [
    # Original functions
    'setup_logging',
    'get_project_root', 
    'handle_exception',
    'safe_json_serialize',
    
    # Required classes
    'AgentUtils', 
    'AsyncTaskRunner',
    'PerformanceProfiler',
    
    # Additional utilities
    'ensure_directory',
    'load_json_file',
    'save_json_file',
    'get_system_info',
    'is_port_available',
    'find_available_port'
]