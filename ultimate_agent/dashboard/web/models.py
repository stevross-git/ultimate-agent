#!/usr/bin/env python3
"""
ultimate_agent/dashboard/web/models.py
Dashboard data models and schemas
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgentStatus:
    """Agent status data model"""
    agent_id: str
    running: bool
    uptime: float
    current_tasks: int
    completed_tasks: int
    node_url: str
    timestamp: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_id': self.agent_id,
            'running': self.running,
            'uptime': self.uptime,
            'current_tasks': self.current_tasks,
            'completed_tasks': self.completed_tasks,
            'node_url': self.node_url,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class TaskInfo:
    """Task information data model"""
    task_id: str
    task_type: str
    status: str
    progress: float
    start_time: datetime
    estimated_completion: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'status': self.status,
            'progress': self.progress,
            'start_time': self.start_time.isoformat(),
            'estimated_completion': self.estimated_completion.isoformat() if self.estimated_completion else None
        }


@dataclass
class SystemMetrics:
    """System metrics data model"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_in: int
    network_out: int
    timestamp: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'disk_percent': self.disk_percent,
            'network_in': self.network_in,
            'network_out': self.network_out,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class BlockchainInfo:
    """Blockchain information data model"""
    wallet_address: str
    balance: float
    pending_transactions: int
    total_earnings: float
    network_status: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'wallet_address': self.wallet_address,
            'balance': self.balance,
            'pending_transactions': self.pending_transactions,
            'total_earnings': self.total_earnings,
            'network_status': self.network_status
        }


@dataclass
class AIModelInfo:
    """AI model information data model"""
    model_id: str
    model_name: str
    model_type: str
    status: str
    accuracy: Optional[float] = None
    training_progress: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_id': self.model_id,
            'model_name': self.model_name,
            'model_type': self.model_type,
            'status': self.status,
            'accuracy': self.accuracy,
            'training_progress': self.training_progress
        }


class DashboardResponse:
    """Helper class for creating consistent API responses"""
    
    @staticmethod
    def success(data: Any, message: str = "Success") -> Dict[str, Any]:
        """Create a success response"""
        return {
            'success': True,
            'message': message,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def error(error: str, details: Optional[str] = None) -> Dict[str, Any]:
        """Create an error response"""
        response = {
            'success': False,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        if details:
            response['details'] = details
        return response
    
    @staticmethod
    def paginated(data: List[Any], page: int, per_page: int, total: int) -> Dict[str, Any]:
        """Create a paginated response"""
        return {
            'success': True,
            'data': data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            },
            'timestamp': datetime.now().isoformat()
        }


# Utility functions for dashboard
def format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def format_bytes(bytes_value: int) -> str:
    """Format bytes in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize data for safe transmission"""
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, dict):
            sanitized[key] = sanitize_data(value)
        elif isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif value is None:
            sanitized[key] = None
        else:
            sanitized[key] = str(value)
    return sanitized


# Export all models and utilities
__all__ = [
    'AgentStatus',
    'TaskInfo', 
    'SystemMetrics',
    'BlockchainInfo',
    'AIModelInfo',
    'DashboardResponse',
    'format_uptime',
    'format_bytes',
    'sanitize_data'
]