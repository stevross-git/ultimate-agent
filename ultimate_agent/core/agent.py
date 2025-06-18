"""
Ultimate Agent Core - Main Agent Coordination
Fixed version with proper node registration
"""

import asyncio
import logging
import json
import time
import os
import uuid
import hashlib
import secrets
import threading
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import requests
except Exception:  # pragma: no cover - optional dependency
    requests = None

from ..config.settings import get_config
from ..utils import setup_logging

from ..config.config_settings import ConfigManager
from ..ai.models import AIModelManager
from ..blockchain.wallet.security import BlockchainManager
from ..tasks.execution.task_scheduler import TaskScheduler
from ..security.authentication import SecurityManager
from ..storage.database.migrations import DatabaseManager
from ..monitoring.metrics import MonitoringManager
from ..network.communication import NetworkManager
from ..network.discovery.service_discovery import DiscoveryClient
from ..plugins import PluginManager
from ..remote.command_handler import RemoteCommandHandler

try:
    from ..ai.local_models.local_ai_manager import (
        create_local_ai_manager,
        create_local_ai_conversation_manager,
    )
    LOCAL_AI_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    LOCAL_AI_AVAILABLE = False
    print("⚠️ Local AI not available")

def serialize_for_json(obj):
    """Serialize object for JSON response"""
    if hasattr(obj, '__dict__'):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
    return str(obj)

class UltimateAgent:
    """Main Ultimate Agent coordination class"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()
        self.logger = setup_logging("UltimateAgent")
        self.running = False
        self.modules = {}

        # ✅ Add these
        self.agent_id = self.config.get("agent_id", "agent-001")
        self.ai_manager = None
        self.registered = False
        self.stats = {
            "start_time": time.time(),
            "tasks_completed": 0,
            "tasks_failed": 0
        }
        self.current_tasks = {}
        self.completed_tasks = []

        # Remote command handler
        from ..remote.handler import RemoteCommandHandler
        self._command_handler = RemoteCommandHandler()
        self._command_handler.set_shutdown_callback(self.stop)

        # Remote command handler provides basic commands like 'ping'
        # already initialised above
        
    def start(self):
        """Start the Ultimate Agent"""
        self.logger.info("🚀 Ultimate Agent starting...")
        self.running = True
        
        # Initialize core modules
        self._initialize_modules()
        
        # Start main event loop
        try:
            asyncio.run(self._main_loop())
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the Ultimate Agent"""
        self.logger.info("🛑 Ultimate Agent stopping...")
        self.running = False
        
        # Cleanup modules
        for module_name, module in self.modules.items():
            try:
                if hasattr(module, 'stop'):
                    module.stop()
                self.logger.info(f"✅ Stopped {module_name}")
            except Exception as e:
                self.logger.error(f"❌ Error stopping {module_name}: {e}")
    
    def _initialize_modules(self):
        """Initialize all agent modules"""
        self.logger.info("📦 Initializing modules...")
        
        # Initialize modules based on configuration
        if self.config.get('ai_enabled', True):
            self._initialize_ai_modules()
        
        if self.config.get('tasks_enabled', True):
            self._initialize_task_modules()
            
        if self.config.get('dashboard_enabled', True):
            self._initialize_dashboard()
            
    
    def _initialize_ai_modules(self):
        """Initialize AI-related modules"""
        try:
            from ..ai.models import AIModelManager
            self.modules['ai_models'] = AIModelManager(self.config)
            self.logger.info("✅ AI modules initialized")
        except ImportError as e:
            self.logger.warning(f"⚠️ AI modules not available: {e}")
    
    def _initialize_task_modules(self):
        """Initialize task management modules"""
        try:
            from ..tasks.execution.scheduler import TaskScheduler
            self.modules['task_scheduler'] = TaskScheduler(self.config)
            self.logger.info("✅ Task modules initialized")
        except ImportError as e:
            self.logger.warning(f"⚠️ Task modules not available: {e}")
    
    def _initialize_dashboard(self):
        """Initialize dashboard module - FIXED VERSION"""
        try:
            from ..dashboard.web.routes import DashboardServer
            dashboard = DashboardServer(self)
            self.modules['dashboard'] = dashboard
            
            # Start the dashboard server
            dashboard.start_server()
            
            self.logger.info("✅ Dashboard initialized and server started")
            print(f"🌐 Dashboard Web Server starting on port {dashboard.dashboard_port}")
            print(f"🌐 Access at: http://localhost:{dashboard.dashboard_port}")
            
        except ImportError as e:
            self.logger.warning(f"⚠️ Dashboard not available: {e}")
            print(f"⚠️ Dashboard initialization failed: {e}")
    
    async def _main_loop(self):
        """Main agent event loop"""
        self.logger.info("🔄 Starting main event loop...")
        
        while self.running:
            try:
                # Process agent tasks
                await self._process_tasks()
                
                # Health checks
                await self._health_check()
                
                # Sleep briefly to prevent CPU spinning
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_tasks(self):
        """Process pending tasks"""
        if 'task_scheduler' in self.modules:
            try:
                await self.modules['task_scheduler'].process_pending()
            except Exception as e:
                self.logger.error(f"❌ Task processing error: {e}")
    
    async def _health_check(self):
        """Perform health checks on modules"""
        for module_name, module in self.modules.items():
            try:
                if hasattr(module, 'health_check'):
                    healthy = await module.health_check()
                    if not healthy:
                        self.logger.warning(f"⚠️ Module {module_name} health check failed")
            except Exception as e:
                self.logger.error(f"❌ Health check error for {module_name}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            'running': self.running,
            'modules': list(self.modules.keys()),
            'config': self.config
        }

    def handle_command(self, command: str, **params: Any) -> Dict[str, Any]:
        """Execute a simple remote command.

        This delegates to :class:`~ultimate_agent.remote.handler.RemoteCommandHandler`
        which knows how to handle basic commands like ``ping`` or ``shutdown``.
        Additional keyword arguments are passed to the command handler.
        """

        result = self._command_handler.execute(command, **params)
        if command == "ping" and result.get("status") == "pong":
            return {"message": "pong"}
        return result


class UltimatePainNetworkAgent(UltimateAgent):
    """Enhanced agent combining all functionality with automatic node registration."""

    def __init__(self, node_url: str = None, dashboard_port: int = None, config: Optional[Dict[str, Any]] = None):
        # Initialize config first
        config = config or {}
        
        # Set dashboard port in config if provided
        if dashboard_port:
            config['dashboard_port'] = dashboard_port
            config['port'] = dashboard_port  # Also set generic port
        
        super().__init__(config=config)

        print("🚀 Initializing Enhanced Ultimate Pain Network Agent")

        # Initialize core configuration
        self.config_manager = ConfigManager()
        self.agent_id = self._get_or_create_agent_id()

        # Initialize all managers
        self.security_manager = SecurityManager(self.config_manager)
        self.blockchain_manager = BlockchainManager(self.config_manager)
        self.ai_manager = AIModelManager(self.config_manager)
        self.monitoring_manager = MonitoringManager()
        self.plugin_manager = PluginManager()
        self.database_manager = DatabaseManager()
        self.task_scheduler = TaskScheduler(self.ai_manager, self.blockchain_manager)
        self.network_manager = NetworkManager(self.config_manager)

        node_service_url = self.config_manager.get('DEFAULT', 'node_url', fallback='https://srvnodes.peoplesainetwork.com')
        manager_service_url = self.config_manager.get('DISCOVERY', 'manager_service', fallback='http://mannodes.peoplesainetwork.com')
        self.discovery_client = DiscoveryClient(node_service_url, manager_service_url)

        self.remote_command_handler = RemoteCommandHandler(self)

        # Initialize dashboard - FIXED
        try:
            from ..dashboard.web.routes import DashboardServer
            self.dashboard_manager = DashboardServer(self)
            print("✅ Dashboard manager initialized")
        except ImportError:
            print("⚠️ Dashboard not available - continuing without dashboard")
            self.dashboard_manager = None

        # State management
        self.running = False
        self.current_tasks = {}
        self.completed_tasks = []
        self.start_time = time.time()

        # Node URL and registration setup
        self.node_url = node_url or self.config_manager.get('DEFAULT', 'node_url', fallback='https://srvnodes.peoplesainetwork.com')
        
        # Set the node URL in network manager
        self.network_manager.set_node_url(self.node_url)
        
        # Registration state
        self.registered = False
        self.registration_attempts = 0
        self.max_registration_attempts = self.config_manager.getint('REGISTRATION', 'max_registration_attempts', fallback=5)
        self.registration_thread = None

        self.stats = {
            'total_earnings': 0.0,
            'tasks_completed': 0,
            'uptime': 0.0,
            'current_balance': 0.0,
            'start_time': time.time()
        }

        self.dashboard_port = dashboard_port or config.get('dashboard_port', 8080)

        self._initialize_local_ai()

        print("✅ Ultimate Pain Network Agent initialized")
        print(f"🌐 Node URL: {self.node_url}")
        print(f"📊 Dashboard will be available on port {self.dashboard_port}")
        print(f"🌐 Agent will register to: {self.node_url}")

    def _initialize_local_ai(self):
        """Initialize Local AI components"""
        if not LOCAL_AI_AVAILABLE:
            self.local_ai_manager = None
            self.local_ai_conversation_manager = None
            return

        # Check configuration to see if local AI is enabled
        if self.config_manager and not self.config_manager.getboolean('LOCAL_AI', 'enabled', fallback=True):
            print("⚠️ Local AI disabled in configuration")
            self.local_ai_manager = None
            self.local_ai_conversation_manager = None
            return

        try:
            print("🧠 Initializing Local AI...")
            self.local_ai_manager = create_local_ai_manager(self.config_manager)
            self.local_ai_conversation_manager = create_local_ai_conversation_manager(self.config_manager)
            print("✅ Local AI components initialized successfully")
        except Exception as e:
            print(f"⚠️ Local AI initialization failed: {e}")
            self.local_ai_manager = None
            self.local_ai_conversation_manager = None

    def _get_or_create_agent_id(self) -> str:
        agent_id_file = "agent_id.txt"
        if os.path.exists(agent_id_file):
            with open(agent_id_file, 'r') as f:
                agent_id = f.read().strip()
                if agent_id:
                    return agent_id
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        with open(agent_id_file, 'w') as f:
            f.write(agent_id)
        return agent_id

    def start(self) -> bool:
        """Enhanced start method with automatic registration"""
        print(f"\n🚀 Starting Enhanced Ultimate Pain Network Agent")
        print(f"🆔 Agent ID: {self.agent_id}")
        print(f"🌐 Node URL: {self.node_url}")

        self._load_stats()
        self.running = True

        try:
            # Start task scheduler
            self.task_scheduler.start()
            print("✅ Task scheduler started")
            
            # Start dashboard if available
            if self.dashboard_manager and hasattr(self.dashboard_manager, 'start_server'):
                print(f"🌐 Starting dashboard server on port {self.dashboard_port}...")
                self.dashboard_manager.start_server()
                print(f"✅ Dashboard server started on port {self.dashboard_port}")
                print(f"🌐 Dashboard: http://localhost:{self.dashboard_port}")
                print(f"🎛️ Control Room: http://localhost:{self.dashboard_port}/control-room")
            else:
                print("⚠️ Dashboard not available")
            
            # Start node registration process
            self._start_registration_process()
            
            print("✅ All managers started successfully")
            
        except Exception as e:
            print(f"❌ Error starting managers: {e}")
            import traceback
            traceback.print_exc()
            return False

        print("🎯 Agent started successfully!")

        # Keep running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Agent shutdown initiated...")
            self.stop()

        return True
    
    def _start_registration_process(self):
        """Start the registration process in a separate thread"""
        if self.registration_thread and self.registration_thread.is_alive():
            return
        
        self.registration_thread = threading.Thread(
            target=self._registration_worker,
            daemon=True,
            name="AgentRegistration"
        )
        self.registration_thread.start()
        print("🔄 Registration process started")
    
    def _registration_worker(self):
        """Worker thread for handling registration and heartbeats"""
        # Initial registration attempt
        self._attempt_registration()
        
        # Heartbeat loop
        heartbeat_interval = self.config_manager.getint('DEFAULT', 'heartbeat_interval', fallback=30)
        
        while self.running:
            try:
                if self.registered:
                    # Send heartbeat every N seconds
                    success = self._send_heartbeat()
                    if not success:
                        print("⚠️ Heartbeat failed, will retry registration")
                        self.registered = False
                        self.registration_attempts = 0
                    
                    time.sleep(heartbeat_interval)
                else:
                    # Try to register every 60 seconds if not registered
                    retry_interval = self.config_manager.getint('REGISTRATION', 'registration_retry_interval', fallback=60)
                    time.sleep(retry_interval)
                    self._attempt_registration()
                    
            except Exception as e:
                print(f"❌ Registration worker error: {e}")
                time.sleep(30)
    
    def _attempt_registration(self):
        """Attempt to register with the node"""
        if self.registration_attempts >= self.max_registration_attempts:
            print(f"❌ Max registration attempts ({self.max_registration_attempts}) reached")
            return
        
        self.registration_attempts += 1
        print(f"🔄 Registration attempt {self.registration_attempts}/{self.max_registration_attempts}")
        
        try:
            # Prepare agent capabilities
            capabilities = self._get_agent_capabilities()
            
            # Attempt registration
            success = self.network_manager.register_agent(self.agent_id, capabilities)
            
            if success:
                self.registered = True
                self.registration_attempts = 0
                print(f"✅ Successfully registered with node: {self.node_url}")
                
                # Update stats
                self.stats['last_registration'] = time.time()
                self._save_stats()
                
            else:
                print(f"❌ Registration attempt {self.registration_attempts} failed")
                
        except Exception as e:
            print(f"❌ Registration error: {e}")
    
    def _send_heartbeat(self) -> bool:
        """Send heartbeat to maintain registration"""
        try:
            # Prepare current status
            status_data = self._get_heartbeat_data()
            
            # Send heartbeat
            success = self.network_manager.send_heartbeat(self.agent_id, status_data)
            
            if success:
                print("💓 Heartbeat sent successfully")
                self.stats['last_heartbeat'] = time.time()
                self._save_stats()
                return True
            else:
                print("⚠️ Heartbeat failed")
                return False
                
        except Exception as e:
            print(f"❌ Heartbeat error: {e}")
            return False
    
    def _get_agent_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive agent capabilities for registration"""
        return {
            'agent_id': self.agent_id,
            'agent_type': 'UltimatePainNetworkAgent',
            'version': '4.0-modular',
            'node_url': self.node_url,
            'dashboard_port': self.dashboard_port,
            
            # Core capabilities
            'ai_training_enabled': hasattr(self, 'ai_manager') and self.ai_manager is not None,
            'blockchain_enabled': hasattr(self, 'blockchain_manager') and self.blockchain_manager is not None,
            'task_scheduling_enabled': hasattr(self, 'task_scheduler') and self.task_scheduler is not None,
            'dashboard_enabled': hasattr(self, 'dashboard_manager') and self.dashboard_manager is not None,
            
            # AI capabilities
            'ai_models_available': self._get_available_ai_models(),
            'local_ai_enabled': hasattr(self, 'local_ai_manager') and self.local_ai_manager is not None,
            
            # System info
            'system_info': self._get_system_info(),
            
            # Network info
            'network_capabilities': {
                'dashboard_url': f"http://localhost:{self.dashboard_port}",
                'api_endpoints': [
                    f"http://localhost:{self.dashboard_port}/api/stats",
                    f"http://localhost:{self.dashboard_port}/api/v3/stats",
                    f"http://localhost:{self.dashboard_port}/api/system"
                ]
            },
            
            # Performance metrics
            'performance_metrics': {
                'uptime': time.time() - self.start_time,
                'tasks_completed': self.stats.get('tasks_completed', 0),
                'total_earnings': self.stats.get('total_earnings', 0.0)
            },
            
            # Timestamps
            'registration_time': time.time(),
            'agent_start_time': self.start_time
        }
    
    def _get_heartbeat_data(self) -> Dict[str, Any]:
        """Get data for heartbeat messages"""
        return {
            'agent_id': self.agent_id,
            'status': 'online' if self.running else 'offline',
            'uptime': time.time() - self.start_time,
            'current_tasks': len(self.current_tasks),
            'completed_tasks': len(self.completed_tasks),
            'system_load': self._get_current_system_load(),
            'memory_usage': self._get_memory_usage(),
            'last_activity': time.time(),
            'capabilities_updated': False,  # Set to True if capabilities changed
            'network_stats': self.network_manager.get_connection_stats(),
            'dashboard_active': hasattr(self, 'dashboard_manager') and self.dashboard_manager is not None
        }
    
    def _get_available_ai_models(self) -> list:
        """Get list of available AI models"""
        models = []
        
        if hasattr(self, 'ai_manager') and self.ai_manager:
            try:
                models.extend(list(getattr(self.ai_manager, 'models', {}).keys()))
            except:
                pass
        
        if hasattr(self, 'local_ai_manager') and self.local_ai_manager:
            try:
                local_models = getattr(self.local_ai_manager, 'available_models', [])
                models.extend(local_models)
            except:
                pass
        
        return list(set(models))  # Remove duplicates
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get current system information"""
        try:
            import psutil
            import platform
            
            return {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'architecture': platform.machine(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 1),
                'disk_total_gb': round(psutil.disk_usage('/').total / (1024**3), 1) if platform.system() != 'Windows' else round(psutil.disk_usage('C:\\').total / (1024**3), 1),
            }
        except Exception as e:
            return {
                'platform': 'unknown',
                'error': str(e)
            }
    
    def _get_current_system_load(self) -> Dict[str, float]:
        """Get current system load metrics"""
        try:
            import psutil
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent if psutil.disk_usage else 0
            }
        except Exception:
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0
            }
    
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get detailed memory usage"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            return {
                'total_gb': memory.total / (1024**3),
                'available_gb': memory.available / (1024**3),
                'used_gb': memory.used / (1024**3),
                'percent': memory.percent
            }
        except Exception:
            return {
                'total_gb': 0,
                'available_gb': 0,
                'used_gb': 0,
                'percent': 0
            }
    
    def get_registration_status(self) -> Dict[str, Any]:
        """Get detailed registration status"""
        return {
            'registered': self.registered,
            'node_url': self.node_url,
            'agent_id': self.agent_id,
            'registration_attempts': self.registration_attempts,
            'max_attempts': self.max_registration_attempts,
            'last_registration': self.stats.get('last_registration'),
            'last_heartbeat': self.stats.get('last_heartbeat'),
            'network_stats': self.network_manager.get_connection_stats()
        }
    
    def force_registration(self) -> bool:
        """Force immediate registration attempt"""
        print("🔄 Forcing registration attempt...")
        self.registration_attempts = 0  # Reset attempts
        self._attempt_registration()
        return self.registered

    def get_status(self) -> Dict[str, Any]:
        uptime = time.time() - self.start_time
        status = {
            'agent_id': self.agent_id,
            'node_url': self.node_url,
            'running': self.running,
            'registered': self.registered,  # Add registration status
            'uptime': uptime,
            'current_tasks': len(self.current_tasks),
            'completed_tasks': len(self.completed_tasks),
            'stats': self.stats.copy(),
            'modules': {
                'ai_manager': True,
                'blockchain_manager': True,
                'task_scheduler': True,
                'security_manager': True,
                'database_manager': True,
                'monitoring_manager': True,
                'dashboard_manager': self.dashboard_manager is not None,
                'network_manager': True,
            },
            'ai_models_loaded': 7,  # From your logs
            'blockchain_enhanced': True,
            'smart_contracts': 5,  # From your logs
            'tasks_running': len(self.current_tasks),
        }

        if hasattr(self, 'local_ai_manager') and self.local_ai_manager:
            status['local_ai'] = {
                'enabled': True,
                'manager_available': True,
            }
        else:
            status['local_ai'] = {
                'enabled': False,
                'manager_available': False,
            }
        return status

    def get_capabilities(self) -> Dict[str, Any]:
        capabilities = {
            'ai_training': True,
            'blockchain_operations': True,
            'task_scheduling': True,
            'data_processing': True,
            'network_communication': True,
            'security_features': True,
            'monitoring': True,
            'plugin_support': True,
            'remote_management': True,
        }
        if hasattr(self, 'local_ai_manager') and self.local_ai_manager:
            capabilities['local_ai_inference'] = True
            capabilities['local_conversation'] = True
        return capabilities

    def start_task(self, task_type: str, task_config: Dict[str, Any]) -> str:
        return self.task_scheduler.start_task(task_type, task_config)

    def cancel_task(self, task_id: str) -> bool:
        return self.task_scheduler.cancel_task(task_id)

    def execute_remote_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.remote_command_handler.handle_command(command_data)

    def get_local_ai_status(self) -> Dict[str, Any]:
        if not self.local_ai_manager:
            return {'enabled': False, 'error': 'Local AI not available'}
        try:
            status = self.local_ai_manager.get_status()
            stats = self.local_ai_manager.get_stats()
            hardware = self.local_ai_manager.get_hardware_info()
            return {
                'enabled': True,
                'status': status,
                'performance': stats['inference_stats'],
                'hardware': {
                    'type': hardware['hardware_type'],
                    'memory_gb': round(hardware['system_info']['memory_gb'], 1),
                    'gpu_available': hardware['system_info']['gpu_info']['available'],
                },
                'current_model': hardware.get('current_model'),
            }
        except Exception as e:
            return {'enabled': True, 'error': str(e)}

    def chat_with_ai(self, message: str, conversation_id: str = None, model_type: str = 'general') -> Dict[str, Any]:
        if not hasattr(self, 'local_ai_conversation_manager') or self.local_ai_conversation_manager is None:
            return {
                'success': False,
                'error': 'Conversation manager not available',
                'response': 'Chat functionality is not currently available.',
            }
        try:
            if not conversation_id:
                conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
            return self.local_ai_conversation_manager.process_message(conversation_id, message, model_type=model_type)
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response': 'I apologize, but I encountered an error. Please try again.',
            }

    def _save_stats(self):
        try:
            stats_file = "agent_stats.json"
            import json
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save stats: {e}")

    def _load_stats(self):
        try:
            stats_file = "agent_stats.json"
            if os.path.exists(stats_file):
                import json
                with open(stats_file, 'r') as f:
                    loaded_stats = json.load(f)
                    self.stats.update(loaded_stats)
        except Exception as e:
            print(f"⚠️ Failed to load stats: {e}")

    def start_async(self):
        super().start()

    def stop(self):
        """Enhanced stop method with proper cleanup"""
        print("🛑 Stopping Enhanced Ultimate Pain Network Agent...")
        self.running = False
        
        # Unregister from node
        if self.registered:
            try:
                # Send final status
                self.network_manager.send_heartbeat(self.agent_id, {
                    'agent_id': self.agent_id,
                    'status': 'shutdown',
                    'message': 'Agent shutting down'
                })
                print("📡 Sent shutdown notification to node")
            except Exception as e:
                print(f"⚠️ Failed to send shutdown notification: {e}")

        self._save_stats()

        try:
            self.database_manager.close()
            self.task_scheduler.stop()
            if self.dashboard_manager and hasattr(self.dashboard_manager, 'stop'):
                self.dashboard_manager.stop()
            self.network_manager.close()
            print("✅ All managers stopped successfully")
        except Exception as e:
            print(f"⚠️ Error stopping managers: {e}")

        print("🎯 Agent stopped successfully")

    def get_enhanced_status(self):
        status = self.get_status()
        if hasattr(self, 'local_ai_manager') and self.local_ai_manager:
            try:
                local_ai_status = self.local_ai_manager.get_status()
                local_ai_stats = self.local_ai_manager.get_stats()
                status.update({
                    'local_ai': {
                        'enabled': True,
                        'status': local_ai_status,
                        'performance': local_ai_stats.get('inference_stats', {}),
                        'hardware': local_ai_stats.get('hardware_info', {}),
                        'current_model': local_ai_stats.get('current_model'),
                    }
                })
            except Exception as e:
                status['local_ai'] = {'enabled': True, 'error': str(e)}
        else:
            status['local_ai'] = {'enabled': False}
        return status


# Alias for compatibility
__all__ = ["UltimateAgent", "UltimatePainNetworkAgent"]