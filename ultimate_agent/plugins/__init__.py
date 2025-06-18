#!/usr/bin/env python3
"""
ultimate_agent/plugins/__init__.py
Plugin system for extensible functionality
"""

import os
import sys
import importlib
import importlib.util
import inspect
import threading
import time
import json
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import traceback


class PluginManager:
    """Manages dynamic plugin loading and execution"""
    
    def __init__(self, plugin_directory: str = "plugins"):
        self.plugin_directory = Path(plugin_directory)
        self.loaded_plugins = {}
        self.plugin_metadata = {}
        self.plugin_hooks = {}
        self.plugin_configs = {}
        
        # Plugin lifecycle hooks
        self.hook_types = [
            'on_agent_start', 'on_agent_stop',
            'on_task_start', 'on_task_complete', 'on_task_fail',
            'on_blockchain_transaction', 'on_ai_inference',
            'on_heartbeat', 'on_data_received'
        ]
        
        # Initialize hook storage
        for hook_type in self.hook_types:
            self.plugin_hooks[hook_type] = []
        
        # Plugin security settings
        self.sandbox_enabled = True
        self.allowed_imports = [
            'numpy', 'pandas', 'requests', 'json', 'time', 'datetime',
            'math', 'random', 'os', 'sys', 'logging'
        ]
        self.restricted_functions = ['exec', 'eval', 'open', '__import__']
        
        self.init_plugin_system()
    
    def init_plugin_system(self):
        """Initialize plugin system"""
        try:
            # Create plugin directory if it doesn't exist
            self.plugin_directory.mkdir(exist_ok=True)
            
            # Create example plugin if directory is empty
            if not any(self.plugin_directory.iterdir()):
                self._create_example_plugin()
            
            # Auto-load plugins
            self.load_all_plugins()
            
            print(f"🔌 Plugin system initialized: {len(self.loaded_plugins)} plugins loaded")
            
        except Exception as e:
            print(f"⚠️ Plugin system initialization warning: {e}")
    
    def _create_example_plugin(self):
        """Create an example plugin for demonstration"""
        example_plugin = '''#!/usr/bin/env python3
"""
Example Plugin for Ultimate Agent
Demonstrates basic plugin functionality
"""

class ExamplePlugin:
    """Example plugin that demonstrates various hooks"""
    
    def __init__(self):
        self.name = "Example Plugin"
        self.version = "1.0.0"
        self.description = "Demonstrates plugin functionality"
        self.author = "Ultimate Agent Team"
        
        # Plugin state
        self.task_count = 0
        self.start_time = None
    
    def get_metadata(self):
        """Return plugin metadata"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'hooks': ['on_agent_start', 'on_task_start', 'on_task_complete']
        }
    
    def on_agent_start(self, agent):
        """Called when agent starts"""
        import time
        self.start_time = time.time()
        print(f"🔌 {self.name}: Agent started!")
        return {'status': 'initialized', 'plugin': self.name}
    
    def on_task_start(self, task_data):
        """Called when a task starts"""
        self.task_count += 1
        task_type = task_data.get('task_type', 'unknown')
        print(f"🔌 {self.name}: Task #{self.task_count} started ({task_type})")
        return {'task_number': self.task_count, 'plugin': self.name}
    
    def on_task_complete(self, task_data):
        """Called when a task completes"""
        success = task_data.get('success', False)
        duration = task_data.get('duration', 0)
        status = "✅ succeeded" if success else "❌ failed"
        print(f"🔌 {self.name}: Task {status} in {duration:.1f}s")
        return {'plugin_response': f'Task {status}', 'plugin': self.name}
    
    def get_stats(self):
        """Return plugin statistics"""
        import time
        uptime = time.time() - self.start_time if self.start_time else 0
        return {
            'tasks_observed': self.task_count,
            'uptime_seconds': uptime,
            'plugin_name': self.name
        }

# Plugin entry point
def create_plugin():
    """Factory function to create plugin instance"""
    return ExamplePlugin()
'''
        
        example_file = self.plugin_directory / "example_plugin.py"
        with open(example_file, 'w') as f:
            f.write(example_plugin)
        
        print("📝 Created example plugin")
    
    def load_plugin(self, plugin_file: Path) -> bool:
        """Load a single plugin"""
        try:
            plugin_name = plugin_file.stem
            
            # Skip if already loaded
            if plugin_name in self.loaded_plugins:
                return True
            
            # Load plugin module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            if not spec or not spec.loader:
                print(f"⚠️ Cannot load plugin: {plugin_name}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            
            # Security check: restrict dangerous imports
            if self.sandbox_enabled:
                if not self._validate_plugin_security(plugin_file):
                    print(f"🔒 Plugin failed security check: {plugin_name}")
                    return False
            
            # Execute module
            spec.loader.exec_module(module)
            
            # Get plugin instance
            if hasattr(module, 'create_plugin'):
                plugin_instance = module.create_plugin()
            elif hasattr(module, 'Plugin'):
                plugin_instance = module.Plugin()
            else:
                print(f"⚠️ Plugin missing entry point: {plugin_name}")
                return False
            
            # Get plugin metadata
            if hasattr(plugin_instance, 'get_metadata'):
                metadata = plugin_instance.get_metadata()
            else:
                metadata = {
                    'name': plugin_name,
                    'version': '1.0.0',
                    'description': 'No description provided',
                    'hooks': []
                }
            
            # Store plugin
            self.loaded_plugins[plugin_name] = plugin_instance
            self.plugin_metadata[plugin_name] = metadata
            
            # Register hooks
            self._register_plugin_hooks(plugin_name, plugin_instance, metadata.get('hooks', []))
            
            print(f"✅ Loaded plugin: {metadata.get('name', plugin_name)} v{metadata.get('version', '1.0.0')}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load plugin {plugin_file}: {e}")
            if hasattr(e, '__traceback__'):
                traceback.print_exc()
            return False
    
    def _validate_plugin_security(self, plugin_file: Path) -> bool:
        """Validate plugin security"""
        try:
            with open(plugin_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for restricted functions
            for restricted in self.restricted_functions:
                if restricted in content:
                    print(f"🔒 Security violation: {restricted} found in {plugin_file.name}")
                    return False
            
            # Check for dangerous imports
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    # Extract import name
                    if 'import ' in line:
                        parts = line.split('import ')
                        if len(parts) > 1:
                            imported = parts[1].split()[0].split('.')[0]
                            if imported not in self.allowed_imports and not imported.startswith('ultimate_agent'):
                                print(f"🔒 Restricted import: {imported} in {plugin_file.name}")
                                return False
            
            return True
            
        except Exception as e:
            print(f"⚠️ Security validation error for {plugin_file}: {e}")
            return False
    
    def _register_plugin_hooks(self, plugin_name: str, plugin_instance: Any, hooks: List[str]):
        """Register plugin hooks"""
        for hook_name in hooks:
            if hook_name in self.hook_types:
                if hasattr(plugin_instance, hook_name):
                    hook_function = getattr(plugin_instance, hook_name)
                    self.plugin_hooks[hook_name].append({
                        'plugin_name': plugin_name,
                        'function': hook_function
                    })
                    print(f"🪝 Registered hook: {plugin_name}.{hook_name}")
    
    def load_all_plugins(self):
        """Load all plugins in the plugin directory"""
        try:
            plugin_files = list(self.plugin_directory.glob("*.py"))
            
            for plugin_file in plugin_files:
                if plugin_file.name.startswith('__'):
                    continue  # Skip __init__.py and similar
                
                self.load_plugin(plugin_file)
            
            print(f"🔌 Plugin loading complete: {len(self.loaded_plugins)} plugins active")
            
        except Exception as e:
            print(f"❌ Error loading plugins: {e}")
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a specific plugin"""
        try:
            if plugin_name not in self.loaded_plugins:
                return False
            
            # Call plugin cleanup if available
            plugin_instance = self.loaded_plugins[plugin_name]
            if hasattr(plugin_instance, 'cleanup'):
                plugin_instance.cleanup()
            
            # Remove from hooks
            for hook_type, hooks in self.plugin_hooks.items():
                self.plugin_hooks[hook_type] = [
                    hook for hook in hooks 
                    if hook['plugin_name'] != plugin_name
                ]
            
            # Remove plugin
            del self.loaded_plugins[plugin_name]
            del self.plugin_metadata[plugin_name]
            
            print(f"🗑️ Unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error unloading plugin {plugin_name}: {e}")
            return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a specific plugin"""
        try:
            plugin_file = self.plugin_directory / f"{plugin_name}.py"
            
            if not plugin_file.exists():
                return False
            
            # Unload first
            self.unload_plugin(plugin_name)
            
            # Reload
            return self.load_plugin(plugin_file)
            
        except Exception as e:
            print(f"❌ Error reloading plugin {plugin_name}: {e}")
            return False
    
    def execute_hook(self, hook_type: str, data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute all plugins registered for a specific hook"""
        results = []
        
        if hook_type not in self.plugin_hooks:
            return results
        
        for hook in self.plugin_hooks[hook_type]:
            try:
                plugin_name = hook['plugin_name']
                hook_function = hook['function']
                
                # Execute hook with timeout
                result = self._execute_with_timeout(
                    hook_function, 
                    data or {}, 
                    timeout=30.0,
                    plugin_name=plugin_name
                )
                
                if result is not None:
                    results.append({
                        'plugin': plugin_name,
                        'hook': hook_type,
                        'result': result,
                        'success': True
                    })
                
            except Exception as e:
                print(f"❌ Plugin hook error: {plugin_name}.{hook_type}: {e}")
                results.append({
                    'plugin': plugin_name,
                    'hook': hook_type,
                    'error': str(e),
                    'success': False
                })
        
        return results
    
    def _execute_with_timeout(self, function: Callable, data: Dict[str, Any], timeout: float, plugin_name: str) -> Any:
        """Execute plugin function with timeout"""
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = function(data)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            print(f"⏰ Plugin timeout: {plugin_name} exceeded {timeout}s")
            return None
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific plugin"""
        if plugin_name not in self.loaded_plugins:
            return None
        
        plugin_instance = self.loaded_plugins[plugin_name]
        metadata = self.plugin_metadata[plugin_name]
        
        info = metadata.copy()
        
        # Add runtime information
        info['loaded'] = True
        info['hooks_registered'] = len([
            hook for hooks in self.plugin_hooks.values() 
            for hook in hooks if hook['plugin_name'] == plugin_name
        ])
        
        # Get plugin stats if available
        if hasattr(plugin_instance, 'get_stats'):
            try:
                info['stats'] = plugin_instance.get_stats()
            except Exception as e:
                info['stats_error'] = str(e)
        
        return info
    
    def list_plugins(self) -> Dict[str, Dict[str, Any]]:
        """List all loaded plugins with their information"""
        return {
            name: self.get_plugin_info(name) 
            for name in self.loaded_plugins.keys()
        }
    
    def get_available_plugins(self) -> List[str]:
        """Get list of available plugin files"""
        try:
            plugin_files = list(self.plugin_directory.glob("*.py"))
            return [f.stem for f in plugin_files if not f.name.startswith('__')]
        except Exception:
            return []
    
    def create_plugin_template(self, plugin_name: str) -> bool:
        """Create a new plugin template"""
        try:
            template = f'''#!/usr/bin/env python3
"""
{plugin_name} Plugin for Ultimate Agent
Auto-generated plugin template
"""

class {plugin_name.title().replace('_', '')}Plugin:
    """Plugin for {plugin_name}"""
    
    def __init__(self):
        self.name = "{plugin_name.replace('_', ' ').title()}"
        self.version = "1.0.0"
        self.description = "Custom plugin for {plugin_name}"
        self.author = "Your Name"
    
    def get_metadata(self):
        """Return plugin metadata"""
        return {{
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'hooks': ['on_agent_start']  # Add your hooks here
        }}
    
    def on_agent_start(self, agent):
        """Called when agent starts"""
        print(f"🔌 {{self.name}}: Plugin activated!")
        return {{'status': 'active', 'plugin': self.name}}
    
    # Add more hook methods as needed:
    # def on_task_start(self, task_data):
    # def on_task_complete(self, task_data):
    # def on_blockchain_transaction(self, transaction_data):
    # def on_ai_inference(self, inference_data):
    # def on_heartbeat(self, heartbeat_data):
    
    def get_stats(self):
        """Return plugin statistics"""
        return {{
            'plugin_name': self.name,
            'status': 'active'
        }}
    
    def cleanup(self):
        """Called when plugin is unloaded"""
        print(f"🔌 {{self.name}}: Plugin cleanup")

# Plugin entry point
def create_plugin():
    """Factory function to create plugin instance"""
    return {plugin_name.title().replace('_', '')}Plugin()
'''
            
            plugin_file = self.plugin_directory / f"{plugin_name}.py"
            
            if plugin_file.exists():
                print(f"⚠️ Plugin file already exists: {plugin_name}.py")
                return False
            
            with open(plugin_file, 'w') as f:
                f.write(template)
            
            print(f"📝 Created plugin template: {plugin_name}.py")
            return True
            
        except Exception as e:
            print(f"❌ Error creating plugin template: {e}")
            return False
    
    def install_plugin_from_url(self, url: str, plugin_name: str) -> bool:
        """Install plugin from URL"""
        try:
            import requests
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            plugin_file = self.plugin_directory / f"{plugin_name}.py"
            
            with open(plugin_file, 'w') as f:
                f.write(response.text)
            
            # Load the new plugin
            success = self.load_plugin(plugin_file)
            
            if success:
                print(f"📥 Installed plugin from URL: {plugin_name}")
            else:
                # Clean up on failure
                plugin_file.unlink()
                print(f"❌ Failed to install plugin: {plugin_name}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error installing plugin from URL: {e}")
            return False
    
    def export_plugin_list(self, filepath: str) -> bool:
        """Export list of plugins and their configurations"""
        try:
            export_data = {
                'export_timestamp': time.time(),
                'plugin_directory': str(self.plugin_directory),
                'loaded_plugins': self.list_plugins(),
                'available_plugins': self.get_available_plugins(),
                'hook_registrations': {
                    hook_type: len(hooks) 
                    for hook_type, hooks in self.plugin_hooks.items()
                },
                'security_settings': {
                    'sandbox_enabled': self.sandbox_enabled,
                    'allowed_imports': self.allowed_imports,
                    'restricted_functions': self.restricted_functions
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            print(f"📄 Plugin list exported to {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to export plugin list: {e}")
            return False
    
    def get_hook_statistics(self) -> Dict[str, Any]:
        """Get statistics about hook usage"""
        hook_stats = {}
        
        for hook_type, hooks in self.plugin_hooks.items():
            hook_stats[hook_type] = {
                'registered_plugins': len(hooks),
                'plugin_names': [hook['plugin_name'] for hook in hooks]
            }
        
        return {
            'total_hook_types': len(self.hook_types),
            'active_hook_types': len([ht for ht, hooks in self.plugin_hooks.items() if len(hooks) > 0]),
            'total_hook_registrations': sum(len(hooks) for hooks in self.plugin_hooks.values()),
            'hook_details': hook_stats
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get plugin manager status"""
        return {
            'plugins_loaded': len(self.loaded_plugins),
            'plugins_available': len(self.get_available_plugins()),
            'plugin_directory': str(self.plugin_directory),
            'sandbox_enabled': self.sandbox_enabled,
            'hook_statistics': self.get_hook_statistics(),
            'loaded_plugin_names': list(self.loaded_plugins.keys())
        }
    
    def enable_sandbox(self):
        """Enable plugin sandbox mode"""
        self.sandbox_enabled = True
        print("🔒 Plugin sandbox enabled")
    
    def disable_sandbox(self):
        """Disable plugin sandbox mode (not recommended)"""
        self.sandbox_enabled = False
        print("⚠️ Plugin sandbox disabled - security risk!")
    
    def add_allowed_import(self, module_name: str):
        """Add module to allowed imports list"""
        if module_name not in self.allowed_imports:
            self.allowed_imports.append(module_name)
            print(f"✅ Added to allowed imports: {module_name}")
    
    def remove_allowed_import(self, module_name: str):
        """Remove module from allowed imports list"""
        if module_name in self.allowed_imports:
            self.allowed_imports.remove(module_name)
            print(f"🗑️ Removed from allowed imports: {module_name}")
    
    def cleanup(self):
        """Cleanup plugin manager"""
        try:
            # Unload all plugins
            plugin_names = list(self.loaded_plugins.keys())
            for plugin_name in plugin_names:
                self.unload_plugin(plugin_name)
            
            print("🔌 Plugin manager cleanup complete")
            
        except Exception as e:
            print(f"⚠️ Plugin cleanup error: {e}")
