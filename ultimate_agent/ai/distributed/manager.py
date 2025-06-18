#!/usr/bin/env python3
"""
ultimate_agent/ai/distributed/manager.py
DistributedAIManager that integrates with your existing AIModelManager

This adds distributed inference capabilities while preserving all
existing local AI functionality.
"""

import asyncio
import time
import numpy as np
from typing import Dict, Any, List, Optional, Callable
import threading
import queue

# Import your existing AI components
from ..models import AIModelManager
from ..training import AITrainingEngine
from ..inference import InferenceEngine


class ModelShard:
    """Represents a shard of a distributed model"""
    
    def __init__(self, model_name: str, shard_index: int, 
                 layer_start: int, layer_end: int, node_id: str = None):
        self.model_name = model_name
        self.shard_index = shard_index
        self.layer_start = layer_start
        self.layer_end = layer_end
        self.node_id = node_id
        self.shard_data = None
        self.loaded = False
    
    def load_shard_data(self, model_data: Any):
        """Load the actual model data for this shard"""
        # In real implementation, this would extract layers layer_start:layer_end
        self.shard_data = model_data
        self.loaded = True
    
    def can_process_layers(self, start_layer: int, end_layer: int) -> bool:
        """Check if this shard can process the given layer range"""
        return (self.layer_start <= start_layer and 
                end_layer <= self.layer_end and 
                self.loaded)


class DistributedInferenceCoordinator:
    """Coordinates inference across multiple nodes"""
    
    def __init__(self, network_manager):
        self.network_manager = network_manager
        self.active_requests = {}
        self.shard_registry = {}
        
    async def coordinate_inference(self, 
                                 model_name: str,
                                 input_data: Any,
                                 nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Coordinate distributed inference across nodes"""
        
        request_id = f"coord-{int(time.time())}-{hash(str(input_data)) % 10000}"
        
        try:
            # Get model sharding plan
            sharding_plan = self._create_sharding_plan(model_name, nodes)
            
            # Execute distributed inference pipeline
            result = await self._execute_distributed_pipeline(
                request_id, input_data, sharding_plan
            )
            
            return {
                'success': True,
                'result': result,
                'request_id': request_id,
                'nodes_used': len(nodes),
                'shards_processed': len(sharding_plan)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'request_id': request_id
            }
    
    def _create_sharding_plan(self, model_name: str, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create execution plan for distributing model across nodes"""
        
        # Simple layer-wise sharding for demonstration
        # In production, this would be more sophisticated
        
        model_config = self._get_model_config(model_name)
        total_layers = model_config.get('num_layers', 12)
        
        sharding_plan = []
        layers_per_node = total_layers // len(nodes)
        
        for i, node in enumerate(nodes):
            start_layer = i * layers_per_node
            end_layer = (i + 1) * layers_per_node if i < len(nodes) - 1 else total_layers
            
            sharding_plan.append({
                'node_id': node['node_id'],
                'connection': node['connection'],
                'shard_index': i,
                'layer_start': start_layer,
                'layer_end': end_layer,
                'estimated_latency': node['estimated_latency']
            })
        
        return sharding_plan
    
    def _get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get model configuration for sharding"""
        # Default configurations for common models
        configs = {
            'transformer': {'num_layers': 12, 'hidden_size': 768},
            'sentiment': {'num_layers': 6, 'hidden_size': 512},
            'classification': {'num_layers': 8, 'hidden_size': 512}
        }
        return configs.get(model_name, {'num_layers': 12, 'hidden_size': 768})
    
    async def _execute_distributed_pipeline(self, 
                                          request_id: str,
                                          input_data: Any, 
                                          sharding_plan: List[Dict[str, Any]]) -> Any:
        """Execute inference pipeline across shards"""
        
        current_data = input_data
        
        # Process through each shard in sequence
        for shard in sharding_plan:
            shard_result = await self._process_shard(
                request_id, current_data, shard
            )
            
            if not shard_result.get('success'):
                raise Exception(f"Shard {shard['shard_index']} failed: {shard_result.get('error')}")
            
            current_data = shard_result['output']
        
        return current_data
    
    async def _process_shard(self, 
                           request_id: str,
                           input_data: Any,
                           shard: Dict[str, Any]) -> Dict[str, Any]:
        """Process inference for a single shard"""
        
        try:
            # For demonstration, simulate distributed processing
            # In real implementation, this would send data to the node
            
            # Simulate processing time based on estimated latency
            processing_time = shard['estimated_latency'] / 1000.0
            await asyncio.sleep(min(processing_time, 1.0))
            
            # Simulate layer processing
            if isinstance(input_data, str):
                # Text processing
                output = f"processed_by_shard_{shard['shard_index']}_{input_data}"
            elif isinstance(input_data, (list, np.ndarray)):
                # Tensor processing
                output = input_data  # Pass through for demo
            else:
                output = f"shard_{shard['shard_index']}_output"
            
            return {
                'success': True,
                'output': output,
                'shard_index': shard['shard_index'],
                'processing_time': processing_time
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'shard_index': shard['shard_index']
            }


class DistributedAIManager:
    """Distributed AI manager that extends existing AIModelManager"""
    
    def __init__(self, ai_manager: AIModelManager, network_manager):
        self.ai_manager = ai_manager  # Your existing AI manager
        self.network_manager = network_manager
        self.coordinator = DistributedInferenceCoordinator(network_manager)
        
        # Distributed state
        self.distributed_models = {}
        self.model_shards = {}
        self.distributed_enabled = True
        
        # Performance tracking
        self.distributed_inference_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_latency': 0.0,
            'nodes_utilized': set()
        }
        
        print("🧠 Distributed AI Manager initialized")
    
    def register_distributed_model(self, model_name: str, 
                                 sharding_config: Dict[str, Any]) -> bool:
        """Register a model for distributed inference"""
        
        try:
            # Check if base model exists
            if model_name not in self.ai_manager.models:
                print(f"⚠️ Base model {model_name} not found in AI manager")
                return False
            
            # Create distributed model entry
            self.distributed_models[model_name] = {
                'base_model': self.ai_manager.models[model_name],
                'sharding_config': sharding_config,
                'distributed': True,
                'min_nodes': sharding_config.get('min_nodes', 2),
                'max_nodes': sharding_config.get('max_nodes', 4),
                'registered_at': time.time()
            }
            
            print(f"✅ Registered {model_name} for distributed inference")
            return True
            
        except Exception as e:
            print(f"❌ Failed to register distributed model {model_name}: {e}")
            return False
    
    async def run_distributed_inference(self, 
                                       model_name: str, 
                                       input_data: Any,
                                       prefer_distributed: bool = True) -> Dict[str, Any]:
        """Run inference with automatic local/distributed selection"""
        
        # Check if distributed inference is viable
        if (prefer_distributed and 
            self.distributed_enabled and 
            model_name in self.distributed_models):
            
            # Try distributed inference
            distributed_result = await self._try_distributed_inference(
                model_name, input_data
            )
            
            if distributed_result.get('success'):
                self._update_distributed_stats(True, distributed_result)
                return distributed_result
            else:
                print(f"⚠️ Distributed inference failed, falling back to local")
                self._update_distributed_stats(False, distributed_result)
        
        # Fallback to local inference using existing AI manager
        try:
            local_result = self.ai_manager.run_inference(model_name, input_data)
            
            # Wrap in distributed format for consistency
            return {
                'success': local_result.get('success', True),
                'result': local_result,
                'inference_type': 'local',
                'fallback_used': prefer_distributed,
                'model_name': model_name
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'inference_type': 'local_failed',
                'model_name': model_name
            }
    
    async def _try_distributed_inference(self, 
                                       model_name: str, 
                                       input_data: Any) -> Dict[str, Any]:
        """Attempt distributed inference"""
        
        try:
            # Find suitable nodes
            model_config = self.distributed_models[model_name]
            min_nodes = model_config['min_nodes']
            
            nodes = await self.network_manager.find_nodes_for_distributed_inference(
                model_name=model_name,
                num_nodes=min_nodes
            )
            
            if len(nodes) < min_nodes:
                return {
                    'success': False,
                    'error': f'Insufficient nodes: need {min_nodes}, found {len(nodes)}',
                    'inference_type': 'distributed_failed'
                }
            
            # Coordinate distributed inference
            result = await self.coordinator.coordinate_inference(
                model_name, input_data, nodes
            )
            
            result['inference_type'] = 'distributed'
            result['nodes_used'] = len(nodes)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'inference_type': 'distributed_failed'
            }
    
    def _update_distributed_stats(self, success: bool, result: Dict[str, Any]):
        """Update distributed inference statistics"""
        
        self.distributed_inference_stats['total_requests'] += 1
        
        if success:
            self.distributed_inference_stats['successful_requests'] += 1
            
            # Update latency (if available)
            if 'latency_ms' in result:
                current_avg = self.distributed_inference_stats['average_latency']
                total_requests = self.distributed_inference_stats['successful_requests']
                new_latency = result['latency_ms']
                
                # Calculate running average
                self.distributed_inference_stats['average_latency'] = (
                    (current_avg * (total_requests - 1) + new_latency) / total_requests
                )
            
            # Track nodes used
            if 'nodes_used' in result:
                self.distributed_inference_stats['nodes_utilized'].update(
                    result.get('node_ids', [])
                )
        else:
            self.distributed_inference_stats['failed_requests'] += 1
    
    # Integration methods that work with your existing architecture
    
    def get_enhanced_status(self) -> Dict[str, Any]:
        """Get status including both local and distributed AI"""
        
        # Get base AI manager status
        base_status = self.ai_manager.get_status()
        
        # Add distributed status
        distributed_status = {
            'distributed_enabled': self.distributed_enabled,
            'distributed_models': len(self.distributed_models),
            'distributed_stats': {
                **self.distributed_inference_stats,
                'nodes_utilized': len(self.distributed_inference_stats['nodes_utilized'])
            },
            'coordinator_active': self.coordinator is not None,
            'network_status': self.network_manager.get_distributed_status()
        }
        
        return {
            **base_status,
            'distributed_ai': distributed_status
        }
    
    def list_all_models(self) -> Dict[str, Dict[str, Any]]:
        """List both local and distributed models"""
        
        all_models = {}
        
        # Add local models
        for model_name, model_info in self.ai_manager.models.items():
            all_models[model_name] = {
                **model_info,
                'type': 'local',
                'distributed_available': model_name in self.distributed_models
            }
        
        # Add distributed model info
        for model_name, dist_config in self.distributed_models.items():
            if model_name in all_models:
                all_models[model_name].update({
                    'distributed_config': dist_config,
                    'min_nodes_required': dist_config['min_nodes']
                })
        
        return all_models
    
    def enable_distributed_for_model(self, model_name: str) -> bool:
        """Enable distributed inference for existing model"""
        
        if model_name not in self.ai_manager.models:
            return False
        
        # Default sharding configuration
        sharding_config = {
            'strategy': 'layer_wise',
            'min_nodes': 2,
            'max_nodes': 4,
            'chunk_size': 'auto'
        }
        
        return self.register_distributed_model(model_name, sharding_config)
    
    def disable_distributed_for_model(self, model_name: str) -> bool:
        """Disable distributed inference for model"""
        
        if model_name in self.distributed_models:
            del self.distributed_models[model_name]
            print(f"🔄 Disabled distributed inference for {model_name}")
            return True
        
        return False
    
    # Methods that maintain compatibility with existing TaskScheduler
    
    def create_distributed_inference_task(self, model_name: str, 
                                        input_data: Any) -> Callable:
        """Create task function for distributed inference"""
        
        async def distributed_task():
            return await self.run_distributed_inference(
                model_name, input_data, prefer_distributed=True
            )
        
        return distributed_task
    
    def get_distributed_task_types(self) -> List[str]:
        """Get available distributed task types"""
        
        base_types = ['distributed_inference']
        
        # Add model-specific distributed tasks
        for model_name in self.distributed_models:
            base_types.append(f'distributed_{model_name}_inference')
        
        return base_types
    
    def close(self):
        """Cleanup distributed AI manager"""
        
        self.distributed_models.clear()
        self.model_shards.clear()
        
        print("🧠 Distributed AI Manager closed")


# Integration function for your existing agent
def enhance_ai_manager(ai_manager: AIModelManager, network_manager) -> DistributedAIManager:
    """Enhance existing AI manager with distributed capabilities"""
    
    distributed_ai = DistributedAIManager(ai_manager, network_manager)
    
    # Auto-register suitable models for distributed inference
    for model_name, model_info in ai_manager.models.items():
        model_type = model_info.get('type', '')
        
        # Register models that benefit from distribution
        if model_type in ['nlp_advanced', 'vision_advanced', 'transformer']:
            distributed_ai.enable_distributed_for_model(model_name)
    
    return distributed_ai