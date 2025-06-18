#!/usr/bin/env python3
"""
ultimate_agent/tasks/execution/scheduler.py
Task scheduling and execution management
"""

import time
import threading
import random
import uuid
try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    class _DummyNumpy:
        class ndarray:
            pass

    np = _DummyNumpy()
from datetime import datetime
from typing import Dict, Any, List, Callable
from ..simulation import TaskSimulator
from ..control import TaskControlClient


class TaskScheduler:
    """Manages task scheduling and execution"""
    
    def __init__(self, ai_manager, blockchain_manager):
        self.ai_manager = ai_manager
        self.blockchain_manager = blockchain_manager
        self.task_simulator = TaskSimulator(ai_manager, blockchain_manager)
        self.task_control_client = TaskControlClient(self)
        
        # Active tasks and execution state
        self.current_tasks = {}
        self.completed_tasks = []
        self.task_queue = []
        self.max_concurrent_tasks = 3
        
        # Task execution threads
        self.executor_threads = {}
        self._thread = None
        self.running = False

        print(f"🎯 Task Scheduler initialized")

    def start(self):
        """Start the scheduler background loop."""
        if self.running:
            return

        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        """Internal thread loop for processing tasks"""
        while self.running:
            try:
                self.auto_start_tasks()
                time.sleep(1)
            except Exception as e:
                print(f"❌ Scheduler loop error: {e}")
    
    def get_available_task_types(self) -> List[str]:
        """Get list of available task types"""
        return list(self.task_simulator.tasks.keys())
    
    def start_task(self, task_type: str, task_config: Dict = None) -> str:
        """Start a new task"""
        if task_type not in self.task_simulator.tasks:
            raise ValueError(f"Unknown task type: {task_type}")
        
        if len(self.current_tasks) >= self.max_concurrent_tasks:
            # Queue the task
            task_id = self._queue_task(task_type, task_config or {})
            return task_id
        
        return self._execute_task_immediately(task_type, task_config or {})
    
    def _queue_task(self, task_type: str, task_config: Dict) -> str:
        """Queue task for later execution"""
        task_id = f"queued-{int(time.time())}-{random.randint(1000, 9999)}"
        
        queued_task = {
            'task_id': task_id,
            'task_type': task_type,
            'config': task_config,
            'queued_at': datetime.now(),
            'status': 'queued'
        }
        
        self.task_queue.append(queued_task)
        print(f"📋 Task queued: {task_id} ({task_type})")
        
        return task_id
    
    def _execute_task_immediately(self, task_type: str, task_config: Dict) -> str:
        """Execute task immediately"""
        task_id = f"task-{int(time.time())}-{random.randint(1000, 9999)}"
        
        # Get task configuration
        base_config = self.task_simulator.tasks[task_type].copy()
        base_config.update(task_config)
        base_config['type'] = task_type
        base_config['duration'] = random.randint(
            base_config['min_duration'], 
            base_config['max_duration']
        )
        
        # Create task details
        task_details = {
            **base_config,
            "task_id": task_id,
            "start_time": datetime.now().isoformat(),
            "progress": 0,
            "status": "running",
            "details": {}
        }
        
        self.current_tasks[task_id] = task_details
        
        # Start execution thread
        execution_thread = threading.Thread(
            target=self._execute_task_thread,
            args=(task_id, base_config),
            daemon=True,
            name=f"Task-{task_id}"
        )
        
        self.executor_threads[task_id] = execution_thread
        execution_thread.start()
        
        print(f"🚀 Task started: {task_id} ({task_type})")
        return task_id
    
    def _execute_task_thread(self, task_id: str, task_config: Dict):
        """Execute task in separate thread"""
        try:
            start_time = time.time()
            
            # Progress callback
            def progress_callback(progress: float, details: Dict = None) -> bool:
                if task_id not in self.current_tasks:
                    return False
                
                self.current_tasks[task_id]["progress"] = progress
                if details:
                    self.current_tasks[task_id]["details"].update(details)
                
                # Broadcast progress (would be handled by agent)
                self._broadcast_progress(task_id, progress, details)
                
                return True
            
            # Execute based on task type
            if task_config.get('ai_workload'):
                result = self.task_simulator.execute_ai_task(task_config, progress_callback)
            elif task_config.get('blockchain_task'):
                result = self.task_simulator.execute_blockchain_task(task_config, progress_callback)
            else:
                result = self.task_simulator.execute_generic_task(task_config, progress_callback)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Handle completion
            self._handle_task_completion(task_id, task_config, result, duration, start_time, end_time)
            
        except Exception as e:
            print(f"❌ Task {task_id} execution failed: {e}")
            self._handle_task_failure(task_id, str(e))
        finally:
            # Clean up
            if task_id in self.current_tasks:
                del self.current_tasks[task_id]
            if task_id in self.executor_threads:
                del self.executor_threads[task_id]
            
            # Check for queued tasks
            self._process_task_queue()
    
    def _handle_task_completion(self, task_id: str, task_config: Dict, result: Dict, 
                               duration: float, start_time: float, end_time: float):
        """Handle successful task completion"""
        success = result.get('success', False)
        
        # Create completion record
        completion_record = {
            'task_id': task_id,
            'task_type': task_config['type'],
            'start_time': datetime.fromtimestamp(start_time),
            'end_time': datetime.fromtimestamp(end_time),
            'duration': duration,
            'success': success,
            'result': result,
            'reward': task_config.get('reward', 0) if success else 0
        }
        
        self.completed_tasks.append(completion_record)
        
        # Send blockchain reward if successful
        if success and task_config.get('reward', 0) > 0:
            tx_hash = self.blockchain_manager.send_earnings(
                task_config['reward'], 
                task_id
            )
            completion_record['blockchain_tx'] = tx_hash
        
        # Broadcast completion
        self._broadcast_completion(task_id, completion_record)
        
        print(f"✅ Task completed: {task_id} (reward: {completion_record['reward']})")
    
    def _handle_task_failure(self, task_id: str, error: str):
        """Handle task failure"""
        failure_record = {
            'task_id': task_id,
            'error': error,
            'failed_at': datetime.now(),
            'success': False
        }
        
        self.completed_tasks.append(failure_record)
        self._broadcast_completion(task_id, failure_record)
        
        print(f"❌ Task failed: {task_id} - {error}")
    
    def _process_task_queue(self):
        """Process queued tasks"""
        if self.task_queue and len(self.current_tasks) < self.max_concurrent_tasks:
            queued_task = self.task_queue.pop(0)
            print(f"📋 Starting queued task: {queued_task['task_id']}")
            
            self._execute_task_immediately(
                queued_task['task_type'],
                queued_task['config']
            )
    
    def _broadcast_progress(self, task_id: str, progress: float, details: Dict = None):
        """Broadcast task progress (placeholder for agent integration)"""
        # This would be implemented by the agent to broadcast via WebSocket
        pass
    
    def _broadcast_completion(self, task_id: str, completion_record: Dict):
        """Broadcast task completion (placeholder for agent integration)"""
        # This would be implemented by the agent to broadcast via WebSocket
        pass
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel running task"""
        if task_id in self.current_tasks:
            # Mark for cancellation (task thread will check and exit)
            del self.current_tasks[task_id]
            print(f"🛑 Task cancelled: {task_id}")
            return True
        
        # Check if task is queued
        for i, queued_task in enumerate(self.task_queue):
            if queued_task['task_id'] == task_id:
                del self.task_queue[i]
                print(f"🛑 Queued task cancelled: {task_id}")
                return True
        
        return False
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of specific task"""
        # Check current tasks
        if task_id in self.current_tasks:
            return self.current_tasks[task_id]
        
        # Check queued tasks
        for queued_task in self.task_queue:
            if queued_task['task_id'] == task_id:
                return queued_task
        
        # Check completed tasks
        for completed_task in self.completed_tasks:
            if completed_task['task_id'] == task_id:
                return completed_task
        
        return {'error': 'Task not found'}
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get comprehensive scheduler status"""
        return {
            'current_tasks': len(self.current_tasks),
            'queued_tasks': len(self.task_queue),
            'completed_tasks': len(self.completed_tasks),
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'available_task_types': self.get_available_task_types(),
            'task_control_connected': self.task_control_client.connected if hasattr(self.task_control_client, 'connected') else False,
            'active_threads': len(self.executor_threads),
            'scheduler_running': self.running
        }
    
    def auto_start_tasks(self):
        """Automatically start tasks based on configuration"""
        if len(self.current_tasks) < self.max_concurrent_tasks:
            # 10% chance to start a random task
            if random.random() < 0.1:
                task_types = self.get_available_task_types()
                task_type = random.choice(task_types)
                self.start_task(task_type)
    
    def set_max_concurrent_tasks(self, max_tasks: int):
        """Set maximum concurrent tasks"""
        self.max_concurrent_tasks = max(1, max_tasks)
        print(f"🎯 Max concurrent tasks set to: {self.max_concurrent_tasks}")
        
        # Process queue if we can now run more tasks
        self._process_task_queue()
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """Get task execution statistics"""
        total_completed = len(self.completed_tasks)
        successful_tasks = len([t for t in self.completed_tasks if t.get('success', False)])
        failed_tasks = total_completed - successful_tasks
        
        # Calculate average duration for successful tasks
        successful_with_duration = [t for t in self.completed_tasks 
                                  if t.get('success', False) and 'duration' in t]
        avg_duration = (sum(t['duration'] for t in successful_with_duration) / 
                       len(successful_with_duration)) if successful_with_duration else 0
        
        # Total earnings
        total_earnings = sum(t.get('reward', 0) for t in self.completed_tasks)
        
        return {
            'total_completed': total_completed,
            'successful_tasks': successful_tasks,
            'failed_tasks': failed_tasks,
            'success_rate': (successful_tasks / total_completed) if total_completed > 0 else 0,
            'average_duration': avg_duration,
            'total_earnings': total_earnings,
            'current_active': len(self.current_tasks),
            'current_queued': len(self.task_queue)
        }
    
    def clear_completed_tasks(self, keep_recent: int = 100):
        """Clear old completed tasks to save memory"""
        if len(self.completed_tasks) > keep_recent:
            removed_count = len(self.completed_tasks) - keep_recent
            self.completed_tasks = self.completed_tasks[-keep_recent:]
            print(f"🗑️ Cleared {removed_count} old completed tasks")
    
    def export_task_history(self, filepath: str):
        """Export task history to file"""
        try:
            import json
            
            export_data = {
                'completed_tasks': [
                    {
                        **task,
                        'start_time': task['start_time'].isoformat() if isinstance(task.get('start_time'), datetime) else task.get('start_time'),
                        'end_time': task['end_time'].isoformat() if isinstance(task.get('end_time'), datetime) else task.get('end_time'),
                        'failed_at': task['failed_at'].isoformat() if isinstance(task.get('failed_at'), datetime) else task.get('failed_at')
                    }
                    for task in self.completed_tasks
                ],
                'statistics': self.get_task_statistics(),
                'exported_at': datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            print(f"📄 Task history exported to {filepath}")
            return True
        except Exception as e:
            print(f"❌ Failed to export task history: {e}")
            return False
    
    def stop(self):
        """Stop the task scheduler"""
        print("🛑 Stopping task scheduler...")
        self.running = False
        
        # Cancel all current tasks
        for task_id in list(self.current_tasks.keys()):
            self.cancel_task(task_id)
        
        # Wait for threads to complete
        for thread in list(self.executor_threads.values()):
            if thread.is_alive():
                thread.join(timeout=5)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        print("✅ Task scheduler stopped")
