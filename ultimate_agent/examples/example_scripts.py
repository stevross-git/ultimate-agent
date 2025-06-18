#!/usr/bin/env python3
"""
examples/basic_usage.py
Basic usage example for the Enhanced Ultimate Agent
"""

import time
import asyncio
from ultimate_agent import (
    create_agent, 
    print_banner, 
    print_module_status,
    get_available_modules,
    check_dependencies
)

def basic_agent_example():
    """Basic agent usage example"""
    print("🚀 Enhanced Ultimate Agent - Basic Usage Example")
    print("=" * 60)
    
    # Show system banner and module status
    print_banner()
    print_module_status()
    
    # Check dependencies
    deps = check_dependencies()
    print(f"\n🔍 Dependencies: {len(deps.get('missing_required', []))} missing")
    
    # Create agent with custom configuration
    agent = create_agent(

        node_url="https://srvnodes.peoplesainetwork.com",
        dashboard_port=8080,




    )
    
    print(f"\n🎯 Agent created: {agent.agent_id}")
    print(f"💰 Wallet: {agent.blockchain_manager.earnings_wallet}")
    print(f"🧠 AI Models: {len(agent.ai_manager.models)}")
    
    # Start some tasks before running the agent
    print("\n🎮 Starting sample tasks...")
    
    task_ids = []
    
    # Start AI training tasks
    if hasattr(agent.ai_manager, 'training_engine'):
        task_ids.append(agent.start_task('neural_network_training', {
            'epochs': 5,
            'learning_rate': 0.01
        }))
        print(f"  ✅ Neural network training started: {task_ids[-1]}")
    
    # Start blockchain task
    task_ids.append(agent.start_task('blockchain_transaction', {
        'amount': 0.1
    }))
    print(f"  ✅ Blockchain transaction started: {task_ids[-1]}")
    
    # Start data processing
    task_ids.append(agent.start_task('data_processing', {
        'dataset_size': 1000
    }))
    print(f"  ✅ Data processing started: {task_ids[-1]}")
    
    print(f"\n🎯 Started {len(task_ids)} tasks")
    print(f"🌐 Dashboard available at: http://localhost:{agent.dashboard_port}")
    print("\n🚀 Starting agent...")
    
    try:
        # Start the agent (this will run indefinitely)
        agent.start()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down agent...")
        agent.stop()
        print("✅ Agent stopped successfully")


def advanced_agent_example():
    """Advanced agent configuration example"""
    print("🎯 Enhanced Ultimate Agent - Advanced Configuration Example")
    print("=" * 60)
    
    # Create agent with advanced configuration
    agent = create_agent()
    
    # Configure AI training
    agent.config_manager.set('AI_TRAINING', 'gpu_enabled', 'true')
    agent.config_manager.set('AI_TRAINING', 'max_concurrent_training', '3')
    
    # Configure blockchain
    agent.config_manager.set('BLOCKCHAIN', 'multi_currency_support', 'true')
    agent.config_manager.set('BLOCKCHAIN', 'smart_contracts_enabled', 'true')
    
    # Configure monitoring
    agent.config_manager.set('MONITORING', 'metrics_enabled', 'true')
    agent.config_manager.set('MONITORING', 'performance_tracking', 'true')
    
    # Enable plugins
    agent.config_manager.set('PLUGINS', 'enabled', 'true')
    agent.config_manager.set('PLUGINS', 'auto_load', 'true')
    
    print("⚙️ Advanced configuration applied")
    
    # Start monitoring
    if hasattr(agent, 'monitoring_manager'):
        agent.monitoring_manager.start_monitoring()
        print("📊 Monitoring started")
    
    # Load plugins
    if hasattr(agent, 'plugin_manager'):
        agent.plugin_manager.load_all_plugins()
        plugins = agent.plugin_manager.list_plugins()
        print(f"🔌 Loaded {len(plugins)} plugins")
    
    # Get comprehensive status
    status = agent.get_status()
    print(f"\n📊 Agent Status:")
    print(f"  • Tasks Running: {status.get('tasks_running', 0)}")
    print(f"  • Total Earnings: {status.get('total_earnings', 0):.4f} ETH")
    print(f"  • AI Models: {status.get('ai_models_loaded', 0)}")
    print(f"  • Blockchain Balance: {status.get('blockchain_balance', 0):.4f}")
    
    print("\n🚀 Starting advanced agent...")
    
    try:
        agent.start()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down advanced agent...")
        agent.stop()


def multi_agent_example():
    """Multi-agent deployment example"""
    print("🌐 Enhanced Ultimate Agent - Multi-Agent Example")
    print("=" * 60)
    
    agents = []
    
    # Create AI-specialized agent
    ai_agent = create_agent(dashboard_port=8081)
    ai_agent.config_manager.set('AI_TRAINING', 'enabled', 'true')
    ai_agent.config_manager.set('AI_TRAINING', 'max_concurrent_training', '5')
    ai_agent.config_manager.set('BLOCKCHAIN', 'enabled', 'false')
    agents.append(('AI Agent', ai_agent))
    
    # Create blockchain-specialized agent
    blockchain_agent = create_agent(dashboard_port=8082)
    blockchain_agent.config_manager.set('AI_TRAINING', 'enabled', 'false')
    blockchain_agent.config_manager.set('BLOCKCHAIN', 'enabled', 'true')
    blockchain_agent.config_manager.set('BLOCKCHAIN', 'smart_contracts_enabled', 'true')
    agents.append(('Blockchain Agent', blockchain_agent))
    
    # Create monitoring agent
    monitor_agent = create_agent(dashboard_port=8083)
    monitor_agent.config_manager.set('MONITORING', 'metrics_enabled', 'true')
    monitor_agent.config_manager.set('AI_TRAINING', 'enabled', 'false')
    monitor_agent.config_manager.set('BLOCKCHAIN', 'enabled', 'false')
    agents.append(('Monitor Agent', monitor_agent))
    
    print(f"🎯 Created {len(agents)} specialized agents")
    
    for name, agent in agents:
        print(f"  • {name}: {agent.agent_id} (port {agent.dashboard_port})")
    
    print("\n🚀 Starting all agents...")
    
    # Start all agents in separate threads
    import threading
    
    threads = []
    for name, agent in agents:
        thread = threading.Thread(
            target=agent.start,
            name=f"{name}Thread",
            daemon=True
        )
        thread.start()
        threads.append(thread)
        print(f"  ✅ {name} started")
    
    print(f"\n🌐 Dashboards available at:")
    for name, agent in agents:
        print(f"  • {name}: http://localhost:{agent.dashboard_port}")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down all agents...")
        for name, agent in agents:
            agent.stop()
            print(f"  ✅ {name} stopped")


def plugin_development_example():
    """Plugin development and usage example"""
    print("🔌 Enhanced Ultimate Agent - Plugin Development Example")
    print("=" * 60)
    
    agent = create_agent()
    
    if not hasattr(agent, 'plugin_manager'):
        print("❌ Plugin manager not available")
        return
    
    plugin_manager = agent.plugin_manager
    
    # Create a custom plugin
    plugin_code = '''
class CustomAnalyticsPlugin:
    def __init__(self):
        self.name = "Custom Analytics"
        self.version = "1.0.0"
        self.task_analytics = {}
    
    def get_metadata(self):
        return {
            'name': self.name,
            'version': self.version,
            'hooks': ['on_task_start', 'on_task_complete'],
            'description': 'Provides custom task analytics'
        }
    
    def on_task_start(self, task_data):
        task_id = task_data.get('task_id')
        self.task_analytics[task_id] = {
            'start_time': time.time(),
            'task_type': task_data.get('task_type', 'unknown')
        }
        print(f"🔌 Analytics: Tracking task {task_id}")
        return {'tracked': True}
    
    def on_task_complete(self, task_data):
        task_id = task_data.get('task_id')
        if task_id in self.task_analytics:
            analytics = self.task_analytics[task_id]
            duration = time.time() - analytics['start_time']
            success = task_data.get('success', False)
            
            print(f"🔌 Analytics: Task {task_id} completed in {duration:.1f}s ({'✅' if success else '❌'})")
            
            # Store analytics
            analytics.update({
                'duration': duration,
                'success': success,
                'end_time': time.time()
            })
        
        return {'analyzed': True}
    
    def get_stats(self):
        completed_tasks = [a for a in self.task_analytics.values() if 'duration' in a]
        avg_duration = sum(a['duration'] for a in completed_tasks) / len(completed_tasks) if completed_tasks else 0
        success_rate = sum(1 for a in completed_tasks if a['success']) / len(completed_tasks) if completed_tasks else 0
        
        return {
            'total_tasks': len(self.task_analytics),
            'completed_tasks': len(completed_tasks),
            'average_duration': avg_duration,
            'success_rate': success_rate
        }

def create_plugin():
    import time
    return CustomAnalyticsPlugin()
'''
    
    # Save plugin to file
    import os
    plugin_dir = plugin_manager.plugin_directory
    plugin_file = plugin_dir / "custom_analytics.py"
    
    with open(plugin_file, 'w') as f:
        f.write(plugin_code)
    
    print(f"📝 Created custom plugin: {plugin_file}")
    
    # Load the plugin
    success = plugin_manager.load_plugin(plugin_file)
    if success:
        print("✅ Plugin loaded successfully")
        
        # List all plugins
        plugins = plugin_manager.list_plugins()
        print(f"🔌 Available plugins: {list(plugins.keys())}")
        
        # Start some tasks to trigger plugin hooks
        print("\n🎮 Starting tasks to demonstrate plugin hooks...")
        
        task_ids = []
        for i in range(3):
            task_id = agent.start_task('data_processing')
            task_ids.append(task_id)
            print(f"  ✅ Started task {task_id}")
            time.sleep(1)  # Small delay
        
        # Wait a bit for tasks to complete
        print("\n⏳ Waiting for tasks to complete...")
        time.sleep(10)
        
        # Get plugin stats
        if 'custom_analytics' in plugin_manager.loaded_plugins:
            plugin_instance = plugin_manager.loaded_plugins['custom_analytics']
            stats = plugin_instance.get_stats()
            print(f"\n📊 Plugin Analytics:")
            print(f"  • Total Tasks: {stats['total_tasks']}")
            print(f"  • Completed: {stats['compl