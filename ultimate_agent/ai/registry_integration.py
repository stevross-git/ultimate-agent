#!/usr/bin/env python3
"""
AI Registry Integration for Ultimate Agent
Connects the agent to the AI Model Registry for model discovery
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class AIModelInfo:
    id: str
    name: str
    type: str
    provider: str
    endpoint: str
    capabilities: List[str]
    communication_schema: Dict[str, Any]

class RegistryClient:
    def __init__(self, registry_url: str = "http://localhost:3001"):
        self.registry_url = registry_url.rstrip('/')
        self.session = None
        self.logger = logging.getLogger(__name__)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def register_agent(self, agent_info: Dict[str, Any]) -> bool:
        """Register this agent with the registry"""
        try:
            async with self.session.post(
                f"{self.registry_url}/api/agents/register",
                json=agent_info
            ) as response:
                result = await response.json()
                if result.get('success'):
                    self.logger.info(f"✅ Agent registered: {agent_info.get('name')}")
                    return True
                else:
                    self.logger.error(f"❌ Registration failed: {result.get('error')}")
                    return False
        except Exception as e:
            self.logger.error(f"❌ Registration error: {str(e)}")
            return False
    
    async def find_models(self, criteria: Dict[str, Any] = None) -> List[AIModelInfo]:
        """Find models matching criteria"""
        try:
            if criteria is None:
                # Get all models
                async with self.session.get(f"{self.registry_url}/api/models") as response:
                    data = await response.json()
                    models_data = data.get('models', [])
            else:
                # Search with criteria
                async with self.session.post(
                    f"{self.registry_url}/api/models/find",
                    json=criteria
                ) as response:
                    data = await response.json()
                    models_data = data.get('models', [])
            
            models = []
            for model_data in models_data:
                models.append(AIModelInfo(
                    id=model_data['id'],
                    name=model_data['name'],
                    type=model_data['type'],
                    provider=model_data['provider'],
                    endpoint=model_data['endpoint'],
                    capabilities=model_data.get('capabilities', []),
                    communication_schema=model_data.get('communicationSchema', {})
                ))
            
            return models
            
        except Exception as e:
            self.logger.error(f"❌ Error finding models: {str(e)}")
            return []
    
    async def get_model_communication(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get communication details for a model"""
        try:
            async with self.session.get(
                f"{self.registry_url}/api/models/{model_id}/communication"
            ) as response:
                data = await response.json()
                return data.get('communication')
        except Exception as e:
            self.logger.error(f"❌ Error getting model communication: {str(e)}")
            return None

# Integration with existing Ultimate Agent
class UltimateAgentRegistryIntegration:
    def __init__(self, agent_instance, registry_url: str = "http://localhost:3001"):
        self.agent = agent_instance
        self.registry_url = registry_url
        self.registry_client = None
        self.registered_models = {}
        
    async def initialize(self):
        """Initialize registry integration"""
        self.registry_client = RegistryClient(self.registry_url)
        await self.registry_client.__aenter__()
        
        # Register this agent
        agent_info = {
            'name': f"ultimate-agent-{self.agent.agent_id}",
            'type': 'ultimate-agent',
            'endpoint': f"http://localhost:{self.agent.dashboard_port}",
            'capabilities': [
                'ai-training',
                'blockchain',
                'task-scheduling',
                'data-processing'
            ],
            'availableModels': list(self.agent.ai_manager.models.keys()) if hasattr(self.agent, 'ai_manager') else [],
            'dashboardPort': self.agent.dashboard_port,
            'nodeUrl': self.agent.node_url
        }
        
        await self.registry_client.register_agent(agent_info)
        
        # Register local models with the registry
        await self.register_local_models()
    
    async def register_local_models(self):
        """Register local AI models with the registry"""
        if not hasattr(self.agent, 'ai_manager'):
            return
            
        for model_name, model_info in self.agent.ai_manager.models.items():
            model_data = {
                'name': model_name,
                'type': model_info.get('type', 'llm'),
                'provider': 'local',
                'endpoint': f"http://localhost:{self.agent.dashboard_port}/api/ai/{model_name}",
                'description': f"Local model on Ultimate Agent {self.agent.agent_id}",
                'capabilities': model_info.get('capabilities', ['text-generation']),
                'communicationSchema': {
                    'requestFormat': 'ultimate-agent',
                    'responseFormat': 'ultimate-agent',
                    'authMethod': 'none'
                },
                'registeredBy': f"ultimate-agent-{self.agent.agent_id}"
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.registry_url}/api/models/register",
                        json=model_data
                    ) as response:
                        result = await response.json()
                        if result.get('success'):
                            print(f"✅ Registered model: {model_name}")
                            self.registered_models[model_name] = result['model']['id']
            except Exception as e:
                print(f"❌ Failed to register model {model_name}: {str(e)}")
    
    async def discover_external_models(self, task_type: str = None) -> List[AIModelInfo]:
        """Discover external AI models for delegation"""
        criteria = {}
        if task_type:
            criteria['capability'] = task_type
            
        # Find models not from this agent
        criteria['registeredBy'] = {'$ne': f"ultimate-agent-{self.agent.agent_id}"}
        
        return await self.registry_client.find_models(criteria)
    
    async def delegate_to_external_model(self, model_id: str, prompt: str) -> Optional[str]:
        """Delegate a task to an external model"""
        communication = await self.registry_client.get_model_communication(model_id)
        if not communication:
            return None
            
        # Use the JavaScript client's logic adapted for Python
        # This would need to be implemented based on the model's communication schema
        return await self._communicate_with_model(communication, prompt)
    
    async def _communicate_with_model(self, communication: Dict[str, Any], prompt: str) -> Optional[str]:
        """Communicate with external model using its schema"""
        try:
            schema = communication.get('communicationSchema', {})
            endpoint = communication.get('endpoint')
            
            # Build request based on schema
            if schema.get('requestFormat') == 'openai-compatible':
                request_data = {
                    'model': communication.get('name'),
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 150
                }
                endpoint_path = '/v1/chat/completions'
            elif schema.get('requestFormat') == 'ollama':
                request_data = {
                    'model': communication.get('name'),
                    'prompt': prompt,
                    'stream': False
                }
                endpoint_path = '/api/generate'
            else:
                # Default format
                request_data = {'prompt': prompt}
                endpoint_path = '/'
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{endpoint}{endpoint_path}",
                    json=request_data
                ) as response:
                    result = await response.json()
                    
                    # Parse response based on schema
                    if schema.get('responseFormat') == 'openai-compatible':
                        return result.get('choices', [{}])[0].get('message', {}).get('content')
                    elif schema.get('responseFormat') == 'ollama':
                        return result.get('response')
                    else:
                        return result.get('text', str(result))
                        
        except Exception as e:
            print(f"❌ Error communicating with model: {str(e)}")
            return None
    
    async def cleanup(self):
        """Cleanup registry integration"""
        if self.registry_client:
            await self.registry_client.__aexit__(None, None, None)

# Add to Ultimate Agent initialization
def integrate_registry(agent_instance, registry_url: str = "http://localhost:3001"):
    """Add registry integration to Ultimate Agent"""
    integration = UltimateAgentRegistryIntegration(agent_instance, registry_url)
    
    # Add as async task
    async def init_registry():
        await integration.initialize()
    
    # Schedule initialization
    asyncio.create_task(init_registry())
    
    # Add methods to agent
    agent_instance.registry_integration = integration
    agent_instance.discover_models = integration.discover_external_models
    agent_instance.delegate_task = integration.delegate_to_external_model
    
    return integration