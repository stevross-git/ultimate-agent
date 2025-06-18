#!/usr/bin/env python3
"""
ultimate_agent/dashboard/web/routes/local_ai_routes.py
Local AI specific routes for the dashboard
"""

try:
    from flask import request, jsonify, Response
except ImportError:
    # Graceful fallback if Flask not available
    def request():
        pass
    def jsonify(data):
        return data
    def Response(*args, **kwargs):
        return None

import json
import asyncio
from typing import Dict, Any


def add_local_ai_routes(app, agent):
    """Add Local AI API routes to the dashboard"""
    
    # Only add routes if Flask is available
    if app is None:
        return
    
    @app.route('/api/v4/local-ai/status')
    def local_ai_status():
        """Get local AI system status"""
        try:
            if hasattr(agent, 'local_ai_manager') and agent.local_ai_manager:
                status = agent.local_ai_manager.get_status()
                hardware_info = agent.local_ai_manager.get_hardware_info()
                stats = agent.local_ai_manager.get_stats()
                
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
                    'error': 'Local AI not initialized',
                    'available': False
                })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/v4/local-ai/models')
    def list_local_models():
        """List available local AI models"""
        try:
            if hasattr(agent, 'local_ai_manager') and agent.local_ai_manager:
                models = agent.local_ai_manager.list_available_models()
                return jsonify({
                    'success': True,
                    'models': models
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Local AI not available'
                })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/v4/local-ai/models/download', methods=['POST'])
    def download_local_model():
        """Download a local AI model"""
        try:
            data = request.get_json() or {}
            model_name = data.get('model_name')
            
            if not model_name:
                return jsonify({
                    'success': False,
                    'error': 'model_name is required'
                })
            
            if not hasattr(agent, 'local_ai_manager') or not agent.local_ai_manager:
                return jsonify({
                    'success': False,
                    'error': 'Local AI not available'
                })
            
            # Start download asynchronously
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                agent.local_ai_manager.download_model(model_name)
            )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/v4/local-ai/inference', methods=['POST'])
    def local_ai_inference():
        """Run inference using local AI"""
        try:
            data = request.get_json() or {}
            prompt = data.get('prompt', data.get('input', ''))
            
            if not prompt:
                return jsonify({
                    'success': False,
                    'error': 'prompt or input is required'
                })
            
            if not hasattr(agent, 'local_ai_manager') or not agent.local_ai_manager:
                return jsonify({
                    'success': False,
                    'error': 'Local AI not available'
                })
            
            # Extract options
            options = {
                'task_type': data.get('task_type', 'general'),
                'temperature': data.get('temperature', 0.7),
                'max_tokens': data.get('max_tokens', 1000),
                'top_p': data.get('top_p', 0.9)
            }
            
            # Run inference
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                agent.local_ai_manager.generate_response(prompt, **options)
            )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/v4/local-ai/chat', methods=['POST'])
    def local_ai_chat():
        """Enhanced chat endpoint using local AI"""
        try:
            data = request.get_json() or {}
            message = data.get('input', data.get('message', ''))
            conversation_id = data.get('conversation_id')
            
            if not message:
                return jsonify({
                    'success': False,
                    'error': 'message or input is required'
                })
            
            if hasattr(agent, 'chat_with_ai'):
                # Use the agent's chat method
                result = agent.chat_with_ai(
                    message, 
                    conversation_id, 
                    data.get('model_type', 'general')
                )
                return jsonify(result)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Chat functionality not available'
                })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})


# Fallback function if Flask is not available
def add_local_ai_routes_fallback(app, agent):
    """Fallback function when Flask is not available"""
    print("⚠️ Local AI routes not added - Flask not available")
    return

# Export the appropriate function
try:
    from flask import Flask
    # Flask is available, use the real function
    pass
except ImportError:
    # Flask not available, use fallback
    add_local_ai_routes = add_local_ai_routes_fallback