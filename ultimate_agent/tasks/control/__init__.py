#!/usr/bin/env python3
"""
ultimate_agent/tasks/control/__init__.py
Task control client module
"""

import time
import threading
from typing import Dict, Any


class TaskControlClient:
    """Client for centralized task control integration"""
    
    def __init__(self, task_scheduler):
        self.task_scheduler = task_scheduler
        self.connected = False
        self.running = False
        
        print("🎛️ Task Control Client initialized")
    
    def connect_to_task_control(self, server_url: str, agent_id: str = None) -> bool:
        """Connect to centralized task control server"""
        try:
            self.control_server_url = server_url
            self.agent_id = agent_id or f"agent-{int(time.time())}"
            self.connected = True
            print(f"✅ Connected to task control server: {server_url}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to task control server: {e}")
            return False
    
    def handle_task_assignment(self, assignment: Dict[str, Any]) -> bool:
        """Handle task assignment from control server"""
        try:
            task_type = assignment.get('task_type', 'data_processing')
            task_config = assignment.get('config', {})
            
            if hasattr(self.task_scheduler, 'start_task'):
                task_id = self.task_scheduler.start_task(task_type, task_config)
                print(f"📋 Accepted task assignment: {task_type} ({task_id})")
                return True
            return False
        except Exception as e:
            print(f"❌ Error handling task assignment: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get task control client status"""
        return {
            'connected': self.connected,
            'agent_id': getattr(self, 'agent_id', None),
            'server_url': getattr(self, 'control_server_url', None)
        }


__all__ = ['TaskControlClient']
