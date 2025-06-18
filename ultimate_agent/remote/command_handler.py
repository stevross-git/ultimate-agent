import time
import os
from typing import Dict, Any


class RemoteCommandHandler:
    """Simple remote command handler."""

    def __init__(self, agent: Any):
        self.agent = agent
        self.command_handlers = {
            # basic lifecycle
            'restart_agent': self.restart_agent,
            'shutdown_agent': self.shutdown_agent,
            'get_status': self.get_status,
            # task operations
            'start_task': self.start_task,
            'cancel_task': self.cancel_task,
            'pause_task': self.pause_task,
            'resume_task': self.resume_task,
            'set_task_priority': self.set_task_priority,
            # configuration
            'update_config': self.update_config,
            'reload_config': self.reload_config,
            # tuning and diagnostics
            'set_cpu_limit': self.set_cpu_limit,
            'set_memory_limit': self.set_memory_limit,
            'enable_gpu': self.enable_gpu,
            'optimize_performance': self.optimize_performance,
            'get_detailed_status': self.get_detailed_status,
            'get_logs': self.get_logs,
            'run_diagnostics': self.run_diagnostics,
            'monitor_resources': self.monitor_resources,
            # maintenance
            'cleanup_logs': self.cleanup_logs,
            'backup_data': self.backup_data,
            'clear_cache': self.clear_cache,
            'update_agent': self.update_agent,
            'update_system': self.update_system,
            'deploy_configuration': self.deploy_configuration,
        }

    def handle_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a remote command."""
        cmd_type = command.get('command_type')
        params = command.get('parameters', {})
        command_id = command.get('command_id')

        handler = self.command_handlers.get(cmd_type)
        if not handler:
            return {'success': False, 'command_id': command_id, 'error': 'unknown_command'}
        try:
            result = handler(params)
            return {'success': True, 'command_id': command_id, 'result': result}
        except Exception as e:
            return {'success': False, 'command_id': command_id, 'error': str(e)}

    def restart_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        delay = int(params.get('delay', 1))
        self.agent.stop()
        time.sleep(delay)
        return {'action': 'restart_scheduled', 'delay': delay}

    def shutdown_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self.agent.stop()
        return {'action': 'shutdown'}

    def get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.agent.get_status()

    def start_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_type = params.get('task_type', 'data_processing')
        task_config = params.get('task_config', {})
        task_id = self.agent.start_task(task_type, task_config)
        return {'task_id': task_id, 'task_type': task_type}

    def cancel_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_id = params.get('task_id')
        if not task_id:
            raise ValueError('task_id required')
        success = False
        if hasattr(self.agent, 'task_scheduler'):
            success = self.agent.task_scheduler.cancel_task(task_id)
        elif task_id in getattr(self.agent, 'current_tasks', {}):
            del self.agent.current_tasks[task_id]
            success = True
        return {'task_id': task_id, 'cancelled': success}

    def update_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        section = params.get('section')
        updates = params.get('updates', {})
        if not section or not isinstance(updates, dict):
            raise ValueError('invalid parameters')
        for key, value in updates.items():
            self.agent.config_manager.set(section, key, str(value))
        return {'section': section, 'updated_keys': list(updates.keys())}

    def reload_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self.agent.config_manager.reload()
        return {'reloaded': True}

    def pause_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_id = params.get('task_id')
        task = getattr(self.agent, 'current_tasks', {}).get(task_id)
        if task:
            task['status'] = 'paused'
            return {'task_id': task_id, 'status': 'paused'}
        return {'error': 'task_not_found', 'task_id': task_id}

    def resume_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_id = params.get('task_id')
        task = getattr(self.agent, 'current_tasks', {}).get(task_id)
        if task:
            task['status'] = 'running'
            return {'task_id': task_id, 'status': 'running'}
        return {'error': 'task_not_found', 'task_id': task_id}

    def set_task_priority(self, params: Dict[str, Any]) -> Dict[str, Any]:
        task_id = params.get('task_id')
        priority = params.get('priority', 5)
        task = getattr(self.agent, 'current_tasks', {}).get(task_id)
        if task:
            task['priority'] = priority
            return {'task_id': task_id, 'priority': priority}
        return {'error': 'task_not_found', 'task_id': task_id}

    def set_cpu_limit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        limit = int(params.get('limit', 80))
        setattr(self.agent, 'cpu_limit', limit)
        return {'cpu_limit': limit}

    def set_memory_limit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        limit = int(params.get('limit', 80))
        setattr(self.agent, 'memory_limit', limit)
        return {'memory_limit': limit}

    def enable_gpu(self, params: Dict[str, Any]) -> Dict[str, Any]:
        enabled = bool(params.get('enabled', True))
        if hasattr(self.agent, 'ai_manager'):
            self.agent.ai_manager.gpu_available = enabled
        return {'gpu_enabled': enabled}

    def optimize_performance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {'optimized': True}

    def get_detailed_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        status = self.agent.get_status()
        import psutil
        status.update({
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
        })
        return status

    def get_logs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        lines = int(params.get('lines', 50))
        log_file = 'ultimate_agent.log'
        if not os.path.exists(log_file):
            return {'error': 'log_not_found'}
        with open(log_file, 'r') as f:
            content = f.readlines()[-lines:]
        return {'lines': len(content), 'log': ''.join(content)}

    def run_diagnostics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        import psutil
        return {
            'cpu_cores': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'disk_total': psutil.disk_usage('/').total,
        }

    def monitor_resources(self, params: Dict[str, Any]) -> Dict[str, Any]:
        duration = int(params.get('duration', 5))
        interval = float(params.get('interval', 1))
        import psutil, time as t
        samples = []
        end = t.time() + duration
        while t.time() < end:
            samples.append({
                'time': t.time(),
                'cpu': psutil.cpu_percent(),
                'mem': psutil.virtual_memory().percent,
            })
            t.sleep(interval)
        return {'samples': samples}

    def cleanup_logs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        removed = 0
        for file in os.listdir('.'):
            if file.endswith('.log'):
                os.remove(file)
                removed += 1
        return {'logs_removed': removed}

    def backup_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        db_file = 'ultimate_agent.db'
        if os.path.exists(db_file):
            backup = f'{db_file}.bak'
            import shutil
            shutil.copy2(db_file, backup)
            return {'backup': backup}
        return {'error': 'db_not_found'}

    def clear_cache(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {'cache_cleared': True}

    def update_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Pull the latest code from the git repository."""
        repo_path = params.get('repo_path', '.')
        restart = params.get('restart', False)

        import subprocess

        try:
            result = subprocess.run(
                ['git', '-C', repo_path, 'pull'],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout.strip()
            if restart:
                self.agent.stop()
            return {
                'updated': True,
                'output': output,
                'restart': restart,
            }
        except subprocess.CalledProcessError as e:
            return {
                'updated': False,
                'error': e.stderr.strip() or str(e),
            }

    def update_system(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update system packages on the host."""
        package_manager = params.get('package_manager', 'apt')
        restart = params.get('restart', False)

        import subprocess

        try:
            if package_manager == 'apt':
                subprocess.run(['apt', 'update'], check=True, capture_output=True, text=True)
                subprocess.run(['apt', 'upgrade', '-y'], check=True, capture_output=True, text=True)
            elif package_manager == 'yum':
                subprocess.run(['yum', 'update', '-y'], check=True, capture_output=True, text=True)
            else:
                return {
                    'updated': False,
                    'error': f'unknown package manager: {package_manager}'
                }

            if restart:
                self.agent.stop()

            return {
                'updated': True,
                'restart': restart
            }
        except subprocess.CalledProcessError as e:
            return {
                'updated': False,
                'error': e.stderr.strip() or str(e)
            }

    def deploy_configuration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        config = params.get('config', {})
        for section, values in config.items():
            for key, value in values.items():
                self.agent.config_manager.set(section, key, str(value))
        return {'deployed_sections': list(config.keys())}
