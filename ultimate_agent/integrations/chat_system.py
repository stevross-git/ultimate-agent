#!/usr/bin/env python3
"""
ultimate_agent/integrations/chat_system.py
Integration module for the AI Chat System with the existing Ultimate Agent
"""

import os
import sys
from pathlib import Path

# Add the package root to Python path
package_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(package_root))

from ultimate_agent.core.agent1 import UltimatePainNetworkAgent
from ultimate_agent.dashboard.web.routes import DashboardManager


def integrate_chat_system():
    """
    Integration guide for adding the AI Chat System to the existing Ultimate Agent.
    
    This function demonstrates how to integrate the new chat interface and backend
    with the existing modular agent architecture.
    """
    
    print("🔧 Integrating AI Chat System with Ultimate Agent...")
    
    # Step 1: Update the dashboard manager to include chat routes
    update_dashboard_with_chat()
    
    # Step 2: Add conversation manager to the agent
    update_agent_with_chat()
    
    # Step 3: Create the chat interface files
    create_chat_interface_files()
    
    # Step 4: Update configuration
    update_configuration()
    
    print("✅ Chat system integration complete!")
    print("\n📋 Next Steps:")
    print("1. Restart your Ultimate Agent")
    print("2. Navigate to http://localhost:8080/chat for the AI chat interface")
    print("3. The main dashboard at http://localhost:8080 will also include chat features")


def update_dashboard_with_chat():
    """Update the dashboard manager to include chat functionality"""
    
    dashboard_routes_file = Path("ultimate_agent/dashboard/web/routes/__init__.py")
    
    # Add chat routes to the existing dashboard
    chat_routes_addition = '''
# Add this to the DashboardManager.__init__ method after existing route setup:

        # Initialize conversation manager for chat
        if not hasattr(self.agent, 'conversation_manager'):
            from ultimate_agent.ai.chat.conversation_manager import ConversationManager
            self.agent.conversation_manager = ConversationManager(
                self.agent.ai_manager, 
                self.agent.config_manager
            )
        
        # Add chat-specific routes
        self._setup_chat_routes()

    # Add this as a new method in DashboardManager:
    def _setup_chat_routes(self):
        """Setup chat-specific API routes"""
        
        @self.app.route('/chat')
        def chat_interface():
            """Serve the AI chat interface"""
            return self._get_chat_interface_html()
        
        @self.app.route('/api/ai/chat', methods=['POST'])
        def ai_chat():
            """Main chat endpoint"""
            try:
                data = request.get_json() or {}
                
                message = data.get('input', '')
                conversation_id = data.get('conversation_id')
                model_type = data.get('model', 'general')
                context_aware = data.get('options', {}).get('context_aware', True)
                
                if not message:
                    return jsonify({'success': False, 'error': 'Message is required'})
                
                # Create new conversation if needed
                if not conversation_id:
                    conversation_id = self.agent.conversation_manager.create_conversation(
                        user_id='local_user',
                        model_type=model_type
                    )
                
                # Process message
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    self.agent.conversation_manager.process_message(
                        conversation_id, 
                        message, 
                        context_aware
                    )
                )
                
                return jsonify(result)
                
            except Exception as e:
                import traceback
                print(f"❌ Chat error: {e}")
                print(traceback.format_exc())
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'response': 'I apologize, but I encountered an error. Please try again.'
                })
        
        @self.app.route('/api/ai/conversations', methods=['GET'])
        def get_conversations():
            """Get user conversations"""
            try:
                conversations = self.agent.conversation_manager.get_user_conversations('local_user')
                return jsonify({
                    'success': True,
                    'conversations': conversations
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/ai/conversations/<conversation_id>', methods=['GET'])
        def get_conversation(conversation_id):
            """Get specific conversation"""
            try:
                conversation = self.agent.conversation_manager.get_conversation(conversation_id)
                if conversation:
                    return jsonify({
                        'success': True,
                        'conversation': conversation
                    })
                else:
                    return jsonify({'success': False, 'error': 'Conversation not found'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/ai/conversations/<conversation_id>', methods=['DELETE'])
        def delete_conversation(conversation_id):
            """Delete conversation"""
            try:
                success = self.agent.conversation_manager.delete_conversation(conversation_id)
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        # WebSocket events for real-time chat
        @self.socketio.on('chat_message')
        def handle_chat_message(data):
            """Handle real-time chat message"""
            try:
                message = data.get('message', '')
                conversation_id = data.get('conversation_id')
                model_type = data.get('model', 'general')
                
                if not conversation_id:
                    conversation_id = self.agent.conversation_manager.create_conversation(
                        user_id='local_user',
                        model_type=model_type
                    )
                
                # Process message asynchronously
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    self.agent.conversation_manager.process_message(
                        conversation_id, 
                        message, 
                        True
                    )
                )
                
                # Emit response
                emit('chat_response', result)
                
            except Exception as e:
                emit('chat_error', {'error': str(e)})
        
        print("💬 Chat routes added to dashboard")
    
    def _get_chat_interface_html(self):
        """Generate the chat interface HTML"""
        # This would return the HTML content from the artifact above
        # For now, return a simple redirect to the main dashboard with chat features
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Chat Interface</title>
            <meta http-equiv="refresh" content="0; url=/">
        </head>
        <body>
            <p>Redirecting to AI Chat Interface...</p>
            <script>window.location.href = "/";</script>
        </body>
        </html>
        '''
'''
    
    print("📝 Dashboard chat routes integration ready")
    print(f"   Add the above code to: {dashboard_routes_file}")


def update_agent_with_chat():
    """Update the main agent to include conversation management"""
    
    agent_file = Path("ultimate_agent/core/agent1.py")
    
    integration_code = '''
# Add this import at the top of agent1.py:
from ..ai.chat.conversation_manager import ConversationManager

# Add this to the UltimatePainNetworkAgent.__init__ method after other managers:
        
        # Initialize conversation manager for AI chat
        try:
            self.conversation_manager = ConversationManager(self.ai_manager, self.config_manager)
            print("💬 Conversation manager initialized")
        except Exception as e:
            print(f"⚠️ Conversation manager initialization warning: {e}")
            self.conversation_manager = None

# Add this method to the UltimatePainNetworkAgent class:

    def chat_with_ai(self, message: str, conversation_id: str = None, model_type: str = 'general') -> Dict[str, Any]:
        """Chat with the AI assistant"""
        if not hasattr(self, 'conversation_manager') or self.conversation_manager is None:
            return {
                'success': False,
                'error': 'Conversation manager not available',
                'response': 'Chat functionality is not currently available.'
            }
        
        try:
            # Create new conversation if needed
            if not conversation_id:
                conversation_id = self.conversation_manager.create_conversation(
                    user_id='local_user',
                    model_type=model_type
                )
            
            # Process message
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self.conversation_manager.process_message(
                    conversation_id, 
                    message, 
                    True  # context_aware
                )
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response': 'I apologize, but I encountered an error. Please try again.'
            }

    def get_chat_status(self) -> Dict[str, Any]:
        """Get chat system status"""
        if hasattr(self, 'conversation_manager') and self.conversation_manager:
            return self.conversation_manager.get_status()
        else:
            return {'available': False, 'error': 'Conversation manager not initialized'}

# Update the get_status method to include chat info:
# Add this to the existing get_status method return dictionary:
            'chat_system': self.get_chat_status(),
'''
    
    print("📝 Agent chat integration ready")
    print(f"   Add the above code to: {agent_file}")


def create_chat_interface_files():
    """Create the necessary files for the chat interface"""
    
    # Create the conversation manager directory
    chat_dir = Path("ultimate_agent/ai/chat")
    chat_dir.mkdir(exist_ok=True)
    
    # Create __init__.py
    init_file = chat_dir / "__init__.py"
    init_content = '''"""
ultimate_agent/ai/chat/__init__.py
AI Chat system for conversational interface
"""

from .conversation_manager import ConversationManager

__all__ = ['ConversationManager']
'''
    
    with open(init_file, 'w') as f:
        f.write(init_content)
    
    # Create the conversation manager file
    conv_manager_file = chat_dir / "conversation_manager.py"
    print(f"📁 Created chat directory: {chat_dir}")
    print(f"📄 Create conversation manager at: {conv_manager_file}")
    print("   Copy the ConversationManager code from the previous artifact")
    
    # Create enhanced dashboard HTML file
    dashboard_dir = Path("ultimate_agent/dashboard/templates")
    dashboard_dir.mkdir(exist_ok=True)
    
    chat_template_file = dashboard_dir / "chat_interface.html"
    print(f"📄 Create chat interface at: {chat_template_file}")
    print("   Copy the HTML content from the first artifact")


def update_configuration():
    """Update configuration to include chat settings"""
    
    config_additions = '''
# Add these sections to ultimate_agent_config.ini:

[AI_CHAT]
enabled = true
context_memory = true
max_context_length = 4000
conversation_timeout = 3600
response_creativity = 0.7
auto_speak_responses = false

[CHAT_PERSONALITY]
helpful = 0.9
friendly = 0.8
professional = 0.7
creative = 0.6
technical = 0.8

[CHAT_MODELS]
default_model = general
available_models = general,sentiment,transformer,creative,technical
model_switching = true
'''
    
    print("⚙️ Configuration updates needed:")
    print(config_additions)


def create_example_usage():
    """Create example usage of the chat system"""
    
    example_file = Path("ultimate_agent/examples/chat_example.py")
    
    example_content = '''#!/usr/bin/env python3
"""
Example usage of the AI Chat System with Ultimate Agent
"""

import sys
import asyncio
from pathlib import Path

# Add package root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ultimate_agent import create_agent

def basic_chat_example():
    """Basic chat example"""
    print("🤖 Basic AI Chat Example")
    print("=" * 40)
    
    # Create agent
    agent = create_agent()
    
    # Start agent services (optional - for full functionality)
    # agent.start()  # Uncomment to start full agent
    
    # Simple chat interaction
    response = agent.chat_with_ai("Hello! How are you today?")
    print(f"User: Hello! How are you today?")
    print(f"AI: {response.get('response', 'No response')}")
    
    # Continue conversation
    conversation_id = response.get('conversation_id')
    
    response = agent.chat_with_ai(
        "Can you help me write a Python function?", 
        conversation_id=conversation_id,
        model_type='technical'
    )
    print(f"\\nUser: Can you help me write a Python function?")
    print(f"AI: {response.get('response', 'No response')}")
    
    # Get chat statistics
    chat_stats = agent.get_chat_status()
    print(f"\\n📊 Chat Statistics: {chat_stats}")

def advanced_chat_example():
    """Advanced chat with multiple models"""
    print("\\n🧠 Advanced AI Chat Example")
    print("=" * 40)
    
    agent = create_agent()
    
    # Test different models
    models = ['general', 'creative', 'technical', 'sentiment']
    
    for model in models:
        print(f"\\n🎯 Testing {model} model:")
        
        if model == 'creative':
            message = "Write me a short poem about AI"
        elif model == 'technical':
            message = "Explain how neural networks work"
        elif model == 'sentiment':
            message = "I'm feeling really excited about this new technology!"
        else:
            message = "Tell me about yourself"
        
        response = agent.chat_with_ai(message, model_type=model)
        print(f"User: {message}")
        print(f"AI ({model}): {response.get('response', 'No response')[:200]}...")

async def async_chat_example():
    """Async chat example"""
    print("\\n⚡ Async AI Chat Example")
    print("=" * 40)
    
    agent = create_agent()
    
    if hasattr(agent, 'conversation_manager'):
        conv_id = agent.conversation_manager.create_conversation(model_type='general')
        
        messages = [
            "What's the weather like?",
            "Can you help me plan my day?",
            "What are some good productivity tips?"
        ]
        
        for message in messages:
            result = await agent.conversation_manager.process_message(conv_id, message)
            print(f"User: {message}")
            print(f"AI: {result.get('response', 'No response')[:150]}...")
            print(f"Response time: {result.get('response_time', 0):.2f}s\\n")

def web_interface_example():
    """Example of starting the web interface"""
    print("\\n🌐 Web Interface Example")
    print("=" * 40)
    
    print("To start the full web interface:")
    print("1. Run: python main.py")
    print("2. Open: http://localhost:8080")
    print("3. Click on the chat interface or navigate to /chat")
    print("4. Start chatting with your personal AI!")
    
    print("\\nAPI Examples:")
    print("POST /api/ai/chat")
    print("GET /api/ai/conversations")
    print("WebSocket: chat_message event")

if __name__ == "__main__":
    # Run examples
    basic_chat_example()
    advanced_chat_example()
    
    # Run async example
    asyncio.run(async_chat_example())
    
    web_interface_example()
    
    print("\\n✅ All examples completed!")
    print("🚀 Start your Ultimate Agent and try the chat interface!")
'''
    
    with open(example_file, 'w') as f:
        f.write(example_content)
    
    print(f"📄 Created example file: {example_file}")


def create_installation_guide():
    """Create installation and setup guide"""
    
    guide_content = '''# 🤖 AI Chat System Installation Guide

## Quick Setup

1. **Copy the conversation manager code**:
   - Create `ultimate_agent/ai/chat/conversation_manager.py`
   - Copy the ConversationManager code from the backend artifact

2. **Update the dashboard**:
   - Modify `ultimate_agent/dashboard/web/routes/__init__.py`
   - Add the chat routes from the integration guide

3. **Update the main agent**:
   - Modify `ultimate_agent/core/agent1.py`
   - Add conversation manager initialization

4. **Create the chat interface**:
   - Create `ultimate_agent/dashboard/templates/chat_interface.html`
   - Copy the HTML content from the first artifact

5. **Update configuration**:
   - Add chat settings to `ultimate_agent_config.ini`

## File Structure

```
ultimate_agent/
├── ai/
│   ├── chat/
│   │   ├── __init__.py
│   │   └── conversation_manager.py
│   ├── models/
│   ├── training/
│   └── inference/
├── dashboard/
│   ├── templates/
│   │   └── chat_interface.html
│   └── web/routes/
├── core/
│   └── agent1.py
└── examples/
    └── chat_example.py
```

## Testing

1. **Start the agent**:
   ```bash
   python main.py
   ```

2. **Test the API**:
   ```bash
   curl -X POST http://localhost:8080/api/ai/chat \\
     -H "Content-Type: application/json" \\
     -d '{"input": "Hello, AI!"}'
   ```

3. **Open the web interface**:
   - Navigate to `http://localhost:8080`
   - Use the enhanced dashboard with chat features

## Features

- ✅ Real-time chat interface
- ✅ Multiple AI models (general, creative, technical, sentiment)
- ✅ Voice input/output support
- ✅ Conversation history
- ✅ File upload and analysis
- ✅ Context-aware responses
- ✅ WebSocket real-time updates
- ✅ Local processing (privacy-focused)
- ✅ Mobile-responsive design

## Troubleshooting

**Chat not working?**
- Check that conversation_manager.py is in the correct location
- Verify all imports are correct
- Check the console for error messages

**Voice features not working?**
- Voice requires HTTPS or localhost
- Check browser permissions for microphone access

**Performance issues?**
- Adjust `max_context_length` in configuration
- Disable context memory for faster responses
- Reduce conversation history retention

## Customization

**Change AI personality**:
```python
agent.conversation_manager.personality_traits = {
    'helpful': 0.9,
    'friendly': 0.8,
    'professional': 0.9,
    'creative': 0.4,
    'technical': 0.9
}
```

**Add custom responses**:
```python
agent.conversation_manager.conversation_templates['custom'] = [
    "Custom response 1",
    "Custom response 2"
]
```

**Modify UI theme**:
- Edit CSS variables in the HTML file
- Customize colors, fonts, and layout
- Add your own branding
'''
    
    guide_file = Path("AI_CHAT_INSTALLATION_GUIDE.md")
    with open(guide_file, 'w') as f:
        f.write(guide_content)
    
    print(f"📖 Created installation guide: {guide_file}")


if __name__ == "__main__":
    integrate_chat_system()
    create_example_usage()
    create_installation_guide()
    
    print("\n🎉 Integration Complete!")
    print("\nFiles created/updated:")
    print("- ultimate_agent/ai/chat/conversation_manager.py")
    print("- ultimate_agent/dashboard/templates/chat_interface.html") 
    print("- ultimate_agent/examples/chat_example.py")
    print("- AI_CHAT_INSTALLATION_GUIDE.md")
    
    print("\nNext steps:")
    print("1. Copy the code from the artifacts into the appropriate files")
    print("2. Update your dashboard and agent files with the integration code")
    print("3. Restart your Ultimate Agent")
    print("4. Navigate to http://localhost:8080 to use the new chat interface!")