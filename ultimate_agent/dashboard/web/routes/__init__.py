#!/usr/bin/env python3
"""
ultimate_agent/dashboard/web/routes/__init__.py
Complete and Fixed Web dashboard and API routes
"""

import threading
import secrets
import time
import os
import json
import asyncio
from typing import Dict, Any

# Import with graceful fallbacks
try:
    from flask import Flask, jsonify, request, send_from_directory, Response
    from flask_cors import CORS
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    print("⚠️ Flask not available - Dashboard will not start")
    Flask = CORS = SocketIO = emit = None
    FLASK_AVAILABLE = False
    
    # Create dummy classes for graceful fallback
    class DummyFlask:
        def route(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    
    def jsonify(data):
        return data
    
    def Response(*args, **kwargs):
        return None


class DashboardServer:
    """Enhanced Dashboard Server with complete functionality"""

    def __init__(self, agent):
        if not FLASK_AVAILABLE:
            print("❌ Flask not available - Dashboard disabled")
            self.app = None
            self.socketio = None
            self.running = False
            return

        self.agent = agent
        self.app = Flask(__name__)
        self.app.secret_key = secrets.token_hex(16)
        
        # Enable CORS for all routes
        CORS(self.app, cors_allowed_origins="*")
        
        # WebSocket setup
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*", 
            async_mode='threading',
            logger=False,
            engineio_logger=False
        )
        
        # Dashboard state
        self.running = False
        self.server_thread = None
        self.dashboard_port = getattr(agent, 'dashboard_port', 8080)
        
        # Setup routes and WebSocket events
        self._setup_api_routes()
        self._setup_websocket_events()
        
        print(f"🌐 Dashboard server initialized on port {self.dashboard_port}")
    
    def _setup_api_routes(self):
        """Setup all API routes"""
        if not self.app:
            return

        @self.app.route('/favicon.ico')
        def favicon():
            try:
                return send_from_directory(
                    os.path.join(os.path.dirname(__file__), '..', 'static'),
                    'favicon.ico',
                    mimetype='image/vnd.microsoft.icon'
                )
            except:
                return '', 404

        @self.app.route('/')
        def dashboard():
            """Main dashboard page"""
            return self._get_dashboard_html()

        @self.app.route('/control-room')
        def control_room():
            """Control room interface"""
            return self._get_control_room_html()

        @self.app.route('/ai-chat')
        def ai_chat():
            """AI Chat interface"""
            return self._get_ai_chat_html()

        @self.app.route('/local-ai-chat')
        def local_ai_chat_page():
            """Local AI chat interface"""
            return self._get_local_ai_chat_html()

        # ==================== API ENDPOINTS ====================
        
        @self.app.route('/api/stats')
        def get_stats():
            """Get basic agent statistics"""
            try:
                return jsonify(self.agent.get_status())
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/v3/stats')
        def get_v3_stats():
            """Get v3 compatible statistics"""
            try:
                return jsonify(self.agent.get_status())
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/v3/stats/enhanced')
        def get_enhanced_stats():
            """Get enhanced statistics"""
            try:
                stats = self.agent.get_status()
                # Add enhanced information
                stats.update({
                    'ai_training_enabled': hasattr(self.agent, 'ai_manager'),
                    'blockchain_enhanced': hasattr(self.agent, 'blockchain_manager'),
                    'task_control_enabled': hasattr(self.agent, 'task_scheduler'),
                    'modular_architecture': True,
                    'dashboard_version': '4.0',
                    'api_version': 'v3'
                })
                return jsonify(stats)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/system')
        def get_system():
            """Get system information"""
            try:
                import psutil
                import platform
                
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                return jsonify({
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_mb": memory.used / (1024 * 1024),
                    "disk_percent": disk.percent,
                    "status": "online",
                    "platform": platform.system(),
                    "python_version": platform.python_version(),
                    "architecture": platform.machine()
                })
            except Exception as e:
                return jsonify({
                    "cpu_percent": 0,
                    "memory_percent": 0,
                    "memory_mb": 0,
                    "disk_percent": 0,
                    "status": "error",
                    "error": str(e)
                }), 500
        
        @self.app.route('/api/activity')
        def get_activity():
            """Get current activity"""
            try:
                current_tasks = len(getattr(self.agent, 'current_tasks', {}))
                stats = getattr(self.agent, 'stats', {})
                start_time = stats.get('start_time', time.time())
                
                return jsonify({
                    "tasks_running": current_tasks,
                    "tasks_completed": stats.get("tasks_completed", 0),
                    "tasks_failed": stats.get("tasks_failed", 0),
                    "activity_level": "high" if current_tasks > 2 else "normal",
                    "uptime_hours": (time.time() - start_time) / 3600
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/training')
        def get_training():
            """Get AI training information"""
            try:
                if hasattr(self.agent, 'ai_manager'):
                    ai_status = self.agent.ai_manager.get_status()
                    return jsonify({
                        "models_training": ai_status.get('active_training_sessions', 0),
                        "total_models": ai_status.get('models_loaded', 0),
                        "training_active": ai_status.get('active_training_sessions', 0) > 0,
                        "gpu_available": ai_status.get('gpu_available', False),
                        "training_capabilities": ai_status.get('training_capabilities', []),
                        "advanced_training_enabled": ai_status.get('training_engine_active', False)
                    })
                else:
                    return jsonify({
                        "models_training": 0,
                        "total_models": 0,
                        "training_active": False,
                        "gpu_available": False,
                        "training_capabilities": [],
                        "advanced_training_enabled": False
                    })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/network')
        def get_network():
            """Get network status"""
            try:
                return jsonify({
                    "node_url": getattr(self.agent, 'node_url', 'unknown'),
                    "registered": getattr(self.agent, 'registered', False),
                    "network_status": "connected" if getattr(self.agent, 'registered', False) else "disconnected",
                    "agent_id": getattr(self.agent, 'agent_id', 'unknown'),
                    "connection_quality": "good" if getattr(self.agent, 'registered', False) else "poor"
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/tasks')
        def get_tasks():
            """Get current tasks"""
            try:
                current_tasks = getattr(self.agent, 'current_tasks', {})
                completed_tasks = len(getattr(self.agent, 'completed_tasks', []))
                
                scheduler_status = {}
                if hasattr(self.agent, 'task_scheduler'):
                    try:
                        scheduler_status = self.agent.task_scheduler.get_scheduler_status()
                    except:
                        scheduler_status = {'status': 'available'}
                
                return jsonify({
                    'current_tasks': current_tasks,
                    'completed_tasks': completed_tasks,
                    'scheduler_status': scheduler_status
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/start_task', methods=['POST'])
        def start_task():
            """Start a new task"""
            try:
                data = request.get_json() or {}
                task_type = data.get('type', 'data_processing')
                task_config = data.get('config', {})
                
                # Try task scheduler first
                if hasattr(self.agent, 'task_scheduler'):
                    task_id = self.agent.task_scheduler.start_task(task_type, task_config)
                    return jsonify({'success': True, 'task_id': task_id})
                # Fallback to agent method
                elif hasattr(self.agent, 'start_task'):
                    task_id = self.agent.start_task(task_type, task_config)
                    return jsonify({'success': True, 'task_id': task_id})
                else:
                    return jsonify({'success': False, 'error': 'Task system not available'})
                    
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/cancel_task/<task_id>', methods=['POST'])
        def cancel_task(task_id):
            """Cancel a running task"""
            try:
                if hasattr(self.agent, 'task_scheduler'):
                    success = self.agent.task_scheduler.cancel_task(task_id)
                    return jsonify({'success': success})
                elif hasattr(self.agent, 'cancel_task'):
                    success = self.agent.cancel_task(task_id)
                    return jsonify({'success': success})
                else:
                    return jsonify({'success': False, 'error': 'Task cancellation not available'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/capabilities')
        def get_capabilities():
            """Get agent capabilities"""
            try:
                if hasattr(self.agent, 'get_capabilities'):
                    capabilities = self.agent.get_capabilities()
                else:
                    capabilities = {
                        'ai_models': hasattr(self.agent, 'ai_manager'),
                        'blockchain': hasattr(self.agent, 'blockchain_manager'),
                        'task_scheduling': hasattr(self.agent, 'task_scheduler'),
                        'monitoring': hasattr(self.agent, 'monitoring_manager'),
                        'dashboard': True
                    }
                
                # Add dashboard-specific capabilities
                capabilities.update({
                    'dashboard_enabled': True,
                    'websocket_enabled': True,
                    'api_version': 'v4',
                    'modular_architecture': True,
                    'real_time_monitoring': True
                })
                
                return jsonify(capabilities)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # ==================== ENHANCED API ENDPOINTS ====================
        
        @self.app.route('/api/v3/blockchain/enhanced')
        def get_blockchain_enhanced():
            """Get enhanced blockchain information"""
            try:
                if hasattr(self.agent, 'blockchain_manager'):
                    blockchain_status = self.agent.blockchain_manager.get_status()
                    return jsonify(blockchain_status)
                else:
                    return jsonify({'error': 'Blockchain manager not available'})
            except Exception as e:
                return jsonify({'error': f'Blockchain error: {str(e)}'})
        
        @self.app.route('/api/v3/ai/capabilities')
        def get_ai_capabilities():
            """Get AI capabilities"""
            try:
                if hasattr(self.agent, 'ai_manager'):
                    ai_status = self.agent.ai_manager.get_status()
                    if hasattr(self.agent.ai_manager, 'get_model_stats'):
                        model_stats = self.agent.ai_manager.get_model_stats()
                        ai_status.update(model_stats)
                    return jsonify(ai_status)
                else:
                    return jsonify({'error': 'AI manager not available'})
            except Exception as e:
                return jsonify({'error': f'AI capabilities error: {str(e)}'})
        
        @self.app.route('/api/database/stats')
        def get_database_stats():
            """Get database statistics"""
            try:
                if hasattr(self.agent, 'database_manager'):
                    stats = self.agent.database_manager.get_database_stats()
                    return jsonify(stats)
                else:
                    return jsonify({'error': 'Database manager not available'})
            except Exception as e:
                return jsonify({'error': f'Database error: {str(e)}'})
        
        @self.app.route('/api/performance/metrics')
        def get_performance_metrics():
            """Get performance metrics"""
            try:
                if hasattr(self.agent, 'monitoring_manager'):
                    metrics = self.agent.monitoring_manager.get_current_metrics()
                    return jsonify(metrics)
                else:
                    return jsonify({'error': 'Monitoring manager not available'})
            except Exception as e:
                return jsonify({'error': f'Monitoring error: {str(e)}'})

        # ==================== REMOTE MANAGEMENT ====================
        
        @self.app.route('/api/v4/remote/command', methods=['POST'])
        def remote_command():
            """Execute a remote management command"""
            try:
                data = request.get_json() or {}
                if hasattr(self.agent, 'execute_remote_command'):
                    result = self.agent.execute_remote_command(data)
                    return jsonify(result)
                elif hasattr(self.agent, 'handle_command'):
                    result = self.agent.handle_command(data.get('command', ''), **data)
                    return jsonify(result)
                else:
                    return jsonify({'success': False, 'error': 'Remote commands not supported'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/v4/remote/capabilities')
        def remote_capabilities():
            """List available remote management commands"""
            try:
                if hasattr(self.agent, 'remote_command_handler'):
                    commands = list(self.agent.remote_command_handler.command_handlers.keys())
                    return jsonify({'commands': commands})
                else:
                    return jsonify({'commands': ['ping', 'status', 'shutdown']})
            except Exception as e:
                return jsonify({'error': str(e)})

        # ==================== LOCAL AI ENDPOINTS ====================
        
        @self.app.route('/api/v4/local-ai/status')
        def local_ai_status():
            """Get local AI status"""
            try:
                if hasattr(self.agent, 'get_local_ai_status'):
                    status = self.agent.get_local_ai_status()
                    return jsonify(status)
                elif hasattr(self.agent, 'local_ai_manager'):
                    status = self.agent.local_ai_manager.get_status()
                    hardware_info = self.agent.local_ai_manager.get_hardware_info()
                    stats = self.agent.local_ai_manager.get_stats()
                    
                    return jsonify({
                        'success': True,
                        'status': status,
                        'hardware': hardware_info,
                        'performance': stats,
                        'api_version': '4.1'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Local AI not available',
                        'available': False
                    })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/v4/local-ai/chat', methods=['POST'])
        def local_ai_chat():
            """Chat with local AI"""
            try:
                data = request.get_json() or {}
                message = data.get('input', data.get('message', ''))
                conversation_id = data.get('conversation_id')
                model_type = data.get('model_type', 'general')
                
                if not message:
                    return jsonify({
                        'success': False,
                        'error': 'message is required'
                    })
                
                if hasattr(self.agent, 'chat_with_ai'):
                    result = self.agent.chat_with_ai(message, conversation_id, model_type)
                    return jsonify(result)
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Chat functionality not available'
                    })
                    
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        # ==================== AI INFERENCE ENDPOINTS ====================
        
        @self.app.route('/api/ai/inference', methods=['POST'])
        def ai_inference():
            """General AI inference endpoint"""
            try:
                data = request.get_json() or {}
                model = data.get('model', 'general')
                input_text = data.get('input', data.get('prompt', ''))
                
                if not input_text:
                    return jsonify({'success': False, 'error': 'Input text required'})
                
                if hasattr(self.agent, 'ai_manager'):
                    # Use asyncio to handle async AI manager methods
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        result = loop.run_until_complete(
                            self.agent.ai_manager.run_inference(model, input_text, **data)
                        )
                        return jsonify(result)
                    finally:
                        loop.close()
                else:
                    return jsonify({'success': False, 'error': 'AI manager not available'})
                    
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/ai/chat', methods=['POST'])
        def ai_chat_endpoint():
            """AI Chat endpoint"""
            try:
                data = request.get_json() or {}
                message = data.get('input', data.get('message', ''))
                
                if not message:
                    return jsonify({'success': False, 'error': 'Message required'})
                
                # Generate a simple AI response for demonstration
                response = f"I understand you're asking about: {message}. As your AI assistant, I'm here to help with various tasks including analysis, creative writing, and general conversation."
                
                return jsonify({
                    'success': True,
                    'response': response,
                    'model_used': 'general',
                    'processing_time': 0.5,
                    'confidence': 0.85
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        # ==================== ERROR HANDLERS ====================
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({'error': 'Endpoint not found'}), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({'error': 'Internal server error'}), 500

    def _setup_websocket_events(self):
        """Setup WebSocket event handlers"""
        if not self.socketio:
            return

        @self.socketio.on('connect')
        def handle_connect(auth=None):
            """Handle client connection"""
            try:
                emit('connected', {
                    'agent_id': getattr(self.agent, 'agent_id', 'unknown'),
                    'version': '4.0-modular',
                    'status': 'online',
                    'enhanced_features': True,
                    'modular_architecture': True,
                    'timestamp': time.time()
                })
                print("📱 Dashboard client connected")
            except Exception as e:
                print(f"WebSocket connect error: {e}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            print("📱 Dashboard client disconnected")
        
        @self.socketio.on('request_stats')
        def handle_stats_request():
            """Handle stats request"""
            try:
                emit('stats_update', self.agent.get_status())
            except Exception as e:
                emit('error', {'message': str(e)})
        
        @self.socketio.on('request_enhanced_stats')
        def handle_enhanced_stats_request():
            """Handle enhanced stats request"""
            try:
                stats = self.agent.get_status()
                stats.update({
                    'modular_architecture': True,
                    'dashboard_connected': True,
                    'real_time_updates': True
                })
                emit('enhanced_stats_update', stats)
            except Exception as e:
                emit('error', {'message': str(e)})
        
        @self.socketio.on('request_real_time_data')
        def handle_real_time_data_request():
            """Handle real-time data request"""
            try:
                import psutil
                
                real_time_data = {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'tasks_running': len(getattr(self.agent, 'current_tasks', {})),
                    'timestamp': time.time()
                }
                
                if hasattr(self.agent, 'task_scheduler'):
                    try:
                        scheduler_status = self.agent.task_scheduler.get_scheduler_status()
                        real_time_data['scheduler'] = scheduler_status
                    except:
                        pass
                
                emit('real_time_data', real_time_data)
            except Exception as e:
                emit('error', {'message': str(e)})

        @self.socketio.on('remote_command')
        def handle_remote_command(data):
            """Handle remote command execution"""
            try:
                if hasattr(self.agent, 'execute_remote_command'):
                    result = self.agent.execute_remote_command(data)
                elif hasattr(self.agent, 'handle_command'):
                    result = self.agent.handle_command(data.get('command', ''), **data)
                else:
                    result = {'success': False, 'error': 'Remote commands not supported'}
                
                emit('remote_command_response', result)
            except Exception as e:
                emit('remote_command_response', {'success': False, 'error': str(e)})
    
    def broadcast_task_progress(self, task_id: str, progress: float, details: Dict = None):
        """Broadcast task progress to connected clients"""
        if self.socketio:
            self.socketio.emit('task_progress', {
                'task_id': task_id,
                'progress': progress,
                'details': details,
                'timestamp': time.time()
            })
    
    def broadcast_task_completion(self, task_id: str, completion_data: Dict):
        """Broadcast task completion to connected clients"""
        if self.socketio:
            self.socketio.emit('task_completed', {
                'task_id': task_id,
                **completion_data,
                'timestamp': time.time()
            })
    
    def broadcast_system_alert(self, alert_type: str, message: str, severity: str = 'info'):
        """Broadcast system alert to connected clients"""
        if self.socketio:
            self.socketio.emit('system_alert', {
                'type': alert_type,
                'message': message,
                'severity': severity,
                'timestamp': time.time()
            })

    def _get_dashboard_html(self):
        """Generate main dashboard HTML"""
        agent_id = getattr(self.agent, 'agent_id', 'unknown')
        node_url = getattr(self.agent, 'node_url', 'unknown')
        version = '4.0-modular'
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ultimate Agent v{version} - Dashboard</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; background: #f5f7fa; }}
                .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 30px; border-radius: 15px; text-align: center; margin-bottom: 30px; }}
                .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                               gap: 20px; margin-bottom: 30px; }}
                .status-card {{ background: white; padding: 25px; border-radius: 12px; 
                               box-shadow: 0 4px 20px rgba(0,0,0,0.1); border-left: 4px solid #667eea; }}
                .status-value {{ font-size: 2.5em; font-weight: bold; color: #667eea; margin-bottom: 10px; }}
                .status-label {{ color: #666; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; }}
                .controls {{ background: white; padding: 30px; border-radius: 12px; 
                            box-shadow: 0 4px 20px rgba(0,0,0,0.1); margin-bottom: 30px; }}
                .btn-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
                .btn {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; 
                       padding: 15px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; 
                       transition: transform 0.2s, box-shadow 0.2s; }}
                .btn:hover {{ transform: translateY(-2px); box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3); }}
                .system-info {{ background: white; padding: 25px; border-radius: 12px; 
                               box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
                .real-time {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                .loading {{ display: inline-block; width: 20px; height: 20px; border: 3px solid #f3f3f3; 
                           border-top: 3px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite; }}
                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
                .toast {{ position: fixed; top: 20px; right: 20px; background: #28a745; color: white; 
                         padding: 15px 20px; border-radius: 8px; z-index: 1000; transform: translateX(100%); 
                         transition: transform 0.3s; }}
                .toast.show {{ transform: translateX(0); }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 Ultimate Agent Dashboard v{version}</h1>
                    <p>Agent ID: {agent_id} | Node: {node_url}</p>
                    <div style="margin-top: 15px;">
                        <span style="background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; margin: 5px;">
                            🌐 Port: {self.dashboard_port}
                        </span>
                        <span style="background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; margin: 5px;">
                            🏗️ Modular Architecture
                        </span>
                    </div>
                </div>
                
                <div class="real-time" id="realTimeStatus">
                    <h3>📊 Real-time Status</h3>
                    <div id="realTimeData">
                        <span class="loading"></span> Loading system data...
                    </div>
                </div>
                
                <div class="status-grid" id="statusGrid">
                    <div class="status-card">
                        <div class="status-value" id="tasksCompleted">--</div>
                        <div class="status-label">Tasks Completed</div>
                    </div>
                    <div class="status-card">
                        <div class="status-value" id="tasksRunning">--</div>
                        <div class="status-label">Active Tasks</div>
                    </div>
                    <div class="status-card">
                        <div class="status-value" id="uptime">--</div>
                        <div class="status-label">Uptime</div>
                    </div>
                    <div class="status-card">
                        <div class="status-value" id="nodeStatus">--</div>
                        <div class="status-label">Network Status</div>
                    </div>
                </div>
                
                <div class="controls">
                    <h3>🎮 Agent Controls</h3>
                    <div class="btn-grid">
                        <button class="btn" onclick="startTask('ai_training')">🧠 Start AI Training</button>
                        <button class="btn" onclick="startTask('data_processing')">📊 Process Data</button>
                        <button class="btn" onclick="startTask('blockchain_task')">💰 Blockchain Task</button>
                        <button class="btn" onclick="startTask('sentiment_analysis')">😊 Sentiment Analysis</button>
                        <button class="btn" onclick="refreshStats()">🔄 Refresh Stats</button>
                        <button class="btn" onclick="openControlRoom()">🎛️ Control Room</button>
                        <button class="btn" onclick="openAIChat()">💬 AI Chat</button>
                        <button class="btn" onclick="openLocalAIChat()">🤖 Local AI Chat</button>
                        <button class="btn" onclick="showSystemInfo()">ℹ️ System Info</button>
                    </div>
                </div>
                
                <div class="system-info" id="systemInfo" style="display: none;">
                    <h3>💻 System Information</h3>
                    <div id="systemDetails">Loading...</div>
                </div>
            </div>
            
            <script>
                let socket;
                
                // Initialize
                document.addEventListener('DOMContentLoaded', () => {{
                    initSocket();
                    refreshStats();
                    setInterval(refreshStats, 5000);
                    setInterval(updateRealTime, 2000);
                }});
                
                function initSocket() {{
                    try {{
                        socket = io();
                        socket.on('connect', () => {{
                            console.log('Connected to agent dashboard');
                            showToast('Connected to agent', 'success');
                        }});
                        socket.on('stats_update', updateStatsDisplay);
                        socket.on('real_time_data', updateRealTimeDisplay);
                        socket.on('task_completed', onTaskCompleted);
                        socket.on('system_alert', showSystemAlert);
                    }} catch (e) {{
                        console.log('WebSocket not available, using HTTP only');
                    }}
                }}
                
                async function refreshStats() {{
                    try {{
                        const response = await fetch('/api/v3/stats/enhanced');
                        const stats = await response.json();
                        updateStatsDisplay(stats);
                    }} catch (error) {{
                        console.error('Failed to refresh stats:', error);
                    }}
                }}
                
                function updateStatsDisplay(stats) {{
                    document.getElementById('tasksCompleted').textContent = stats.tasks_completed || 0;
                    document.getElementById('tasksRunning').textContent = Object.keys(stats.current_tasks || {{}}).length;
                    document.getElementById('uptime').textContent = formatUptime(stats.uptime || 0);
                    document.getElementById('nodeStatus').textContent = stats.registered ? '🟢 Online' : '🔴 Offline';
                }}
                
                function updateRealTime() {{
                    if (socket) {{
                        socket.emit('request_real_time_data');
                    }}
                }}
                
                function updateRealTimeDisplay(data) {{
                    document.getElementById('realTimeData').innerHTML = `
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                            <div><strong>CPU:</strong> ${{(data.cpu_percent || 0).toFixed(1)}}%</div>
                            <div><strong>Memory:</strong> ${{(data.memory_percent || 0).toFixed(1)}}%</div>
                            <div><strong>Tasks:</strong> ${{data.tasks_running || 0}}</div>
                            <div><strong>Updated:</strong> ${{new Date().toLocaleTimeString()}}</div>
                        </div>
                    `;
                }}
                
                async function startTask(taskType) {{
                    try {{
                        showToast('Starting task...', 'info');
                        const response = await fetch('/api/start_task', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ type: taskType }})
                        }});
                        
                        const result = await response.json();
                        if (result.success) {{
                            showToast(`Task ${{taskType}} started successfully!`, 'success');
                            refreshStats();
                        }} else {{
                            showToast(`Failed to start task: ${{result.error}}`, 'error');
                        }}
                    }} catch (error) {{
                        showToast(`Error: ${{error.message}}`, 'error');
                    }}
                }}
                
                function openControlRoom() {{
                    window.open('/control-room', '_blank');
                }}
                
                function openAIChat() {{
                    window.open('/ai-chat', '_blank');
                }}

                function openLocalAIChat() {{
                    window.open('/local-ai-chat', '_blank');
                }}

                async function showSystemInfo() {{
                    const systemDiv = document.getElementById('systemInfo');
                    if (systemDiv.style.display === 'none') {{
                        try {{
                            const response = await fetch('/api/system');
                            const data = await response.json();
                            document.getElementById('systemDetails').innerHTML = `
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                                    <div><strong>Platform:</strong> ${{data.platform}}</div>
                                    <div><strong>Architecture:</strong> ${{data.architecture}}</div>
                                    <div><strong>Python:</strong> ${{data.python_version}}</div>
                                    <div><strong>CPU Usage:</strong> ${{data.cpu_percent?.toFixed(1)}}%</div>
                                    <div><strong>Memory:</strong> ${{(data.memory_mb/1024).toFixed(1)}} GB</div>
                                    <div><strong>Status:</strong> ${{data.status}}</div>
                                </div>
                            `;
                            systemDiv.style.display = 'block';
                        }} catch (error) {{
                            document.getElementById('systemDetails').innerHTML = 'Error loading system info';
                        }}
                    }} else {{
                        systemDiv.style.display = 'none';
                    }}
                }}
                
                function formatUptime(seconds) {{
                    const hours = Math.floor(seconds / 3600);
                    const minutes = Math.floor((seconds % 3600) / 60);
                    return hours > 0 ? `${{hours}}h ${{minutes}}m` : `${{minutes}}m`;
                }}
                
                function showToast(message, type = 'info') {{
                    const toast = document.createElement('div');
                    toast.className = 'toast';
                    toast.textContent = message;
                    toast.style.background = {{
                        'success': '#28a745',
                        'error': '#dc3545',
                        'info': '#17a2b8'
                    }}[type] || '#17a2b8';
                    
                    document.body.appendChild(toast);
                    setTimeout(() => toast.classList.add('show'), 100);
                    setTimeout(() => {{
                        toast.classList.remove('show');
                        setTimeout(() => toast.remove(), 300);
                    }}, 3000);
                }}
                
                function onTaskCompleted(data) {{
                    showToast(`Task ${{data.task_id}} completed!`, 'success');
                    refreshStats();
                }}
                
                function showSystemAlert(alert) {{
                    showToast(alert.message, alert.severity);
                }}
                
                console.log('🚀 Ultimate Agent Dashboard v{version} Ready');
            </script>
        </body>
        </html>
        """

    def _get_control_room_html(self):
        """Return control room interface"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ultimate Agent - Control Room</title>
            <style>
                body { 
                    font-family: 'Courier New', monospace; 
                    background: radial-gradient(circle at center, #0a0a0a, #1a1a2e); 
                    color: #00ff00; 
                    margin: 0; 
                    height: 100vh; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                }
                .control-panel { 
                    background: rgba(0, 20, 0, 0.9); 
                    border: 2px solid #00ff00; 
                    border-radius: 15px; 
                    padding: 40px; 
                    width: 80%; 
                    max-width: 800px; 
                    box-shadow: 0 0 30px #00ff00; 
                    animation: glow 2s ease-in-out infinite alternate;
                }
                @keyframes glow {
                    from { box-shadow: 0 0 20px #00ff00; }
                    to { box-shadow: 0 0 40px #00ff00; }
                }
                .title { 
                    text-align: center; 
                    font-size: 2.5em; 
                    margin-bottom: 30px; 
                    text-shadow: 0 0 10px #00ff00; 
                }
                .status-grid { 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                    gap: 20px; 
                    margin: 30px 0; 
                }
                .status-box { 
                    background: rgba(0, 50, 0, 0.5); 
                    border: 1px solid #00ff00; 
                    padding: 20px; 
                    text-align: center; 
                    border-radius: 10px; 
                }
                .port-info {
                    text-align: center;
                    font-size: 1.5em;
                    background: rgba(0, 100, 0, 0.3);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                    border: 1px solid #00ff00;
                }
            </style>
        </head>
        <body>
            <div class="control-panel">
                <h1 class="title">🎛️ ULTIMATE AGENT CONTROL ROOM</h1>
                
                <div class="port-info">
                    🌐 DASHBOARD ACTIVE ON PORT """ + str(self.dashboard_port) + """<br>
                    <small>External Access: Enabled</small>
                </div>
                
                <div class="status-grid">
                    <div class="status-box">
                        <h3>NETWORK STATUS</h3>
                        <div id="network">🔗 CONNECTED</div>
                    </div>
                    <div class="status-box">
                        <h3>SYSTEM STATUS</h3>
                        <div id="system">⚡ OPERATIONAL</div>
                    </div>
                    <div class="status-box">
                        <h3>DASHBOARD</h3>
                        <div id="dashboard">🟢 ACTIVE</div>
                    </div>
                    <div class="status-box">
                        <h3>AGENT STATUS</h3>
                        <div id="agent">🤖 ONLINE</div>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <p>🔗 <a href="/" style="color: #00ff00;">Return to Dashboard</a></p>
                    <p>💬 <a href="/ai-chat" style="color: #00ff00;">Open AI Chat</a></p>
                </div>
            </div>
            
            <script>
                // Simulate some dynamic updates
                setInterval(() => {
                    const time = new Date().toLocaleTimeString();
                    document.getElementById('system').innerHTML = `⚡ OPERATIONAL<br><small>${time}</small>`;
                }, 1000);
            </script>
        </body>
        </html>
        """

    def _get_ai_chat_html(self):
        """Return AI chat interface"""
        template_path = os.path.join(
            os.path.dirname(__file__), '..', 'templates', 'ai_chat_interface.html'
        )
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"<p>Error loading template: {e}</p>"

    def _get_local_ai_chat_html(self):
        """Return Local AI chat interface"""
        template_path = os.path.join(
            os.path.dirname(__file__), '..', 'templates', 'ai.html'
        )
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"<p>Error loading template: {e}</p>"
    
    def start_server(self):
        """Start dashboard server in separate thread"""
        if not FLASK_AVAILABLE or self.running:
            return
            
        self.running = True
        self.server_thread = threading.Thread(
            target=self._run_server, 
            daemon=True, 
            name="DashboardServer"
        )
        self.server_thread.start()
        print(f"🌐 Dashboard server started on port {self.dashboard_port}")
        print(f"🌐 Access at: http://localhost:{self.dashboard_port}")
    
    def _run_server(self):
        """Run the dashboard server"""
        if not FLASK_AVAILABLE:
            return
            
        try:
            self.socketio.run(
                self.app,
                host='0.0.0.0',  # Accept external connections
                port=self.dashboard_port,
                debug=False,
                use_reloader=False,
                log_output=False
            )
        except Exception as e:
            print(f"❌ Dashboard server error: {e}")
            self.running = False
    
    def stop(self):
        """Stop dashboard server"""
        if self.running:
            self.running = False
            print("🌐 Dashboard server stopping...")


# Backward compatibility alias
DashboardManager = DashboardServer

# Export for imports
__all__ = ['DashboardServer', 'DashboardManager']