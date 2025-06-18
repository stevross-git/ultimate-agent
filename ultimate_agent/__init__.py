#!/usr/bin/env python3
"""
ultimate_agent/__init__.py
Enhanced Ultimate Pain Network Agent - Modular Architecture

A comprehensive, modular AI agent system with advanced capabilities including:
- AI training and inference
- Blockchain and smart contract integration  
- Task scheduling and management
- Real-time monitoring and analytics
- Multi-cloud support
- Plugin extensibility
- Enterprise security features
"""

__version__ = "3.0.0-modular"
__author__ = "Ultimate Agent Team"
__description__ = "Enhanced Ultimate Pain Network Agent with Modular Architecture"

# Core module imports
from .core.agent1 import UltimatePainNetworkAgent
from .config.config_settings import ConfigManager

# Optional imports with graceful fallbacks
try:
    from .ai.models import AIModelManager
    from .ai.training import AITrainingEngine
    from .ai.inference import InferenceEngine
except Exception as e:
    print(f"⚠️ AI modules not available: {e}")
    AIModelManager = None
    AITrainingEngine = None
    InferenceEngine = None

try:
    from .blockchain.wallet.security import BlockchainManager
    from .blockchain.contracts import SmartContractManager
    from .blockchain.incentives import EconomyManager, TokenFiatExchange
except Exception as e:
    print(f"⚠️ Blockchain modules not available: {e}")
    BlockchainManager = None
    SmartContractManager = None
    EconomyManager = None
    TokenFiatExchange = None

try:
    from .tasks.execution.scheduler import TaskScheduler
    from .tasks.simulation import TaskSimulator
    from .tasks.control import TaskControlClient
except Exception as e:
    print(f"⚠️ Task modules not available: {e}")
    TaskScheduler = None
    TaskSimulator = None
    TaskControlClient = None

try:
    from .storage.database.migrations import DatabaseManager
except Exception as e:
    print(f"⚠️ Database module not available: {e}")
    DatabaseManager = None

try:
    from .dashboard.web.routes import DashboardServer as DashboardManager  # Fixed import
except Exception as e:
    print(f"⚠️ Dashboard module not available: {e}")
    DashboardManager = None

try:
    from .network.advanced.integration import create_network_manager as NetworkManager
except Exception as e:
    try:
        from .network.communication import NetworkManager  # fallback
    except Exception as e2:
        print(f"⚠️ Network module not available: {e2}")
        NetworkManager = None

try:
    from .security.authentication import SecurityManager
except Exception as e:
    print(f"⚠️ Security module not available: {e}")
    SecurityManager = None

try:
    from .monitoring.metrics import MonitoringManager
except Exception as e:
    print(f"⚠️ Monitoring module not available: {e}")
    MonitoringManager = None

try:
    from .plugins import PluginManager
except Exception as e:
    print(f"⚠️ Plugin module not available: {e}")
    PluginManager = None

try:
    from .remote.command_handler import RemoteCommandHandler
except Exception as e:
    print(f"⚠️ Remote management module not available: {e}")
    RemoteCommandHandler = None

try:
    from .cloud import CloudManager
except Exception as e:
    print(f"⚠️ Cloud module not available: {e}")
    CloudManager = None

try:
    from .utils import AgentUtils, AsyncTaskRunner, PerformanceProfiler
except Exception as e:
    print(f"⚠️ Utils module not available: {e}")
    AgentUtils = None
    AsyncTaskRunner = None
    PerformanceProfiler = None


def get_version():
    """Get agent version"""
    return __version__


def get_available_modules():
    """Get list of available modules"""
    modules = {
        'core': UltimatePainNetworkAgent is not None,
        'config': ConfigManager is not None,
        'ai_models': AIModelManager is not None,
        'ai_training': AITrainingEngine is not None,
        'ai_inference': InferenceEngine is not None,
        'blockchain': BlockchainManager is not None,
        'smart_contracts': SmartContractManager is not None,
        'task_scheduler': TaskScheduler is not None,
        'task_simulation': TaskSimulator is not None,
        'task_control': TaskControlClient is not None,
        'database': DatabaseManager is not None,
        'dashboard': DashboardManager is not None,
        'network': NetworkManager is not None,
        'security': SecurityManager is not None,
        'monitoring': MonitoringManager is not None,
        'plugins': PluginManager is not None,
        'cloud': CloudManager is not None,
        'utils': AgentUtils is not None,
        'remote_management': RemoteCommandHandler is not None
    }
    
    available = [name for name, available in modules.items() if available]
    total = len(modules)
    
    return {
        'available_modules': available,
        'total_modules': total,
        'available_count': len(available),
        'availability_rate': len(available) / total * 100,
        'module_status': modules
    }


def create_agent(**kwargs):
    """Factory function to create agent instance"""
    if UltimatePainNetworkAgent is None:
        raise ImportError("Core agent module not available")
    
    return UltimatePainNetworkAgent(**kwargs)


def check_dependencies():
    """Check if required dependencies are available"""
    if AgentUtils:
        return AgentUtils.check_dependencies()
    else:
        # Fallback dependency check
        required_deps = ['requests', 'flask', 'numpy', 'psutil']
        missing = []
        
        for dep in required_deps:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)
        
        return {
            'all_required_available': len(missing) == 0,
            'missing_required': missing,
            'total_required': len(required_deps)
        }


def print_banner():
    """Print agent banner"""
    banner = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  🚀 ENHANCED ULTIMATE PAIN NETWORK AGENT                     ║
║                          Version {__version__:<20}                           ║
║                           🏗️ MODULAR ARCHITECTURE                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  📦 MODULAR COMPONENTS:                                                      ║
║    🎯 Core Agent          - Main coordination and control                   ║
║    ⚙️  Configuration       - Centralized settings management               ║
║    🧠 AI Engine           - Advanced training and inference                 ║
║    💰 Blockchain          - Multi-currency wallet & smart contracts        ║
║    🎮 Task Management     - Intelligent scheduling and execution            ║
║    💾 Data Storage        - Persistent database and analytics               ║
║    🌐 Web Dashboard       - Real-time monitoring interface                  ║
║    📡 Network             - Node communication and protocols                ║
║    🔒 Security            - Authentication and encryption                   ║
║    📊 Monitoring          - Performance metrics and alerts                  ║
║    🔌 Plugin System       - Extensible functionality                        ║
║    ☁️  Cloud Integration   - Multi-cloud service support                    ║
║    🛠️  Utilities          - Common tools and helpers                        ║
║                                                                              ║
║  ✨ FEATURES:                                                               ║
║    • Modular Design       • Real-time Analytics    • Smart Contracts       ║
║    • AI Training          • Task Automation        • Cloud Integration      ║
║    • Security & Auth      • Plugin Extensibility   • Multi-platform        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_module_status():
    """Print status of all modules"""
    module_info = get_available_modules()
    
    print(f"\n📦 MODULE STATUS ({module_info['available_count']}/{module_info['total_modules']} available):")
    print("─" * 70)
    
    status_map = {
        'core': '🎯 Core Agent',
        'config': '⚙️ Configuration',
        'ai_models': '🧠 AI Models',
        'ai_training': '🎓 AI Training',
        'ai_inference': '🔮 AI Inference',
        'blockchain': '💰 Blockchain',
        'smart_contracts': '📜 Smart Contracts',
        'task_scheduler': '📋 Task Scheduler',
        'task_simulation': '🎮 Task Simulation',
        'task_control': '🎯 Task Control',
        'database': '💾 Database',
        'dashboard': '🌐 Dashboard',
        'network': '📡 Network',
        'security': '🔒 Security',
        'monitoring': '📊 Monitoring',
        'plugins': '🔌 Plugins',
        'cloud': '☁️ Cloud',
        'utils': '🛠️ Utils'
    }
    
    for module, status in module_info['module_status'].items():
        name = status_map.get(module, module)
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {name:<25} {'Available' if status else 'Not Available'}")
    
    print(f"\n🎯 Availability Rate: {module_info['availability_rate']:.1f}%")


# Module exports
__all__ = [
    # Core
    'UltimatePainNetworkAgent',
    'ConfigManager',
    
    # AI
    'AIModelManager',
    'AITrainingEngine', 
    'InferenceEngine',
    
    # Blockchain
    'BlockchainManager',
    'SmartContractManager',
    'EconomyManager',
    'TokenFiatExchange',
    
    # Tasks
    'TaskScheduler',
    'TaskSimulator',
    'TaskControlClient',
    
    # Infrastructure
    'DatabaseManager',
    'DashboardManager',
    'NetworkManager',
    'SecurityManager',
    'MonitoringManager',
    
    # Extensions
    'PluginManager',
    'CloudManager',
    'RemoteCommandHandler',
    
    # Utilities
    'AgentUtils',
    'AsyncTaskRunner',
    'PerformanceProfiler',
    
    # Factory and utility functions
    'create_agent',
    'get_version',
    'get_available_modules',
    'check_dependencies',
    'print_banner',
    'print_module_status'
]


# Package metadata
__package_info__ = {
    'name': 'ultimate_agent',
    'version': __version__,
    'description': __description__,
    'author': __author__,
    'architecture': 'modular',
    'python_requires': '>=3.7',
    'platforms': ['Windows', 'Linux', 'macOS'],
    'features': [
        'AI Training & Inference',
        'Blockchain Integration',
        'Task Management',
        'Real-time Monitoring',
        'Plugin System',
        'Cloud Integration',
        'Enterprise Security'
    ]
}
