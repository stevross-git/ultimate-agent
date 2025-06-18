# ultimate_agent/network/p2p/kademlia_discovery.py
import asyncio
import hashlib
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from kademlia.network import Server as KademliaServer
import msgpack

@dataclass
class NodeCapabilities:
    node_id: str
    gpu_memory_gb: float
    cpu_cores: int
    network_bandwidth_mbps: float
    available_models: List[str]
    current_load: float  # 0.0 to 1.0
    model_shards: Dict[str, List[int]]  # model_name -> shard_indices
    inference_latency_p95: float  # milliseconds
    last_heartbeat: float

class AIKademliaDiscovery:
    """Kademlia DHT optimized for AI inference node discovery"""
    
    def __init__(self, node_id: str, listen_port: int = 8468):
        self.node_id = node_id
        self.listen_port = listen_port
        self.server = KademliaServer()
        self.capabilities = NodeCapabilities(
            node_id=node_id,
            gpu_memory_gb=0.0,
            cpu_cores=0,
            network_bandwidth_mbps=0.0,
            available_models=[],
            current_load=0.0,
            model_shards={},
            inference_latency_p95=0.0,
            last_heartbeat=0.0
        )
        
    async def start_network(self, bootstrap_nodes: List[Tuple[str, int]] = None):
        """Start the Kademlia network"""
        await self.server.listen(self.listen_port)
        
        if bootstrap_nodes:
            await self.server.bootstrap(bootstrap_nodes)
        
        # Register our capabilities
        await self._register_capabilities()
        
        # Start heartbeat loop
        asyncio.create_task(self._heartbeat_loop())
        
    async def _register_capabilities(self):
        """Register node capabilities in DHT"""
        key = f"node:capabilities:{self.node_id}"
        capabilities_data = msgpack.packb({
            'node_id': self.capabilities.node_id,
            'gpu_memory_gb': self.capabilities.gpu_memory_gb,
            'cpu_cores': self.capabilities.cpu_cores,
            'network_bandwidth_mbps': self.capabilities.network_bandwidth_mbps,
            'available_models': self.capabilities.available_models,
            'current_load': self.capabilities.current_load,
            'model_shards': self.capabilities.model_shards,
            'inference_latency_p95': self.capabilities.inference_latency_p95,
            'last_heartbeat': time.time()
        })
        
        await self.server.set(key, capabilities_data)
        
        # Register by model type for faster discovery
        for model_name in self.capabilities.available_models:
            model_key = f"model:{model_name}:nodes"
            await self._add_to_model_registry(model_key, self.node_id)
    
    async def discover_nodes_for_model(self, model_name: str, 
                                     min_gpu_memory: float = 0.0,
                                     max_latency_ms: float = 1000.0,
                                     min_nodes: int = 1) -> List[NodeCapabilities]:
        """Discover nodes capable of running specific model"""
        model_key = f"model:{model_name}:nodes"
        
        try:
            node_list_data = await self.server.get(model_key)
            if not node_list_data:
                return []
            
            node_ids = msgpack.unpackb(node_list_data)
            suitable_nodes = []
            
            for node_id in node_ids:
                if node_id == self.node_id:
                    continue
                    
                capabilities = await self._get_node_capabilities(node_id)
                if capabilities and self._is_node_suitable(
                    capabilities, model_name, min_gpu_memory, max_latency_ms
                ):
                    suitable_nodes.append(capabilities)
            
            # Sort by load and latency
            suitable_nodes.sort(key=lambda n: (n.current_load, n.inference_latency_p95))
            
            return suitable_nodes[:min_nodes * 2]  # Return extra for redundancy
            
        except Exception as e:
            print(f"Error discovering nodes for {model_name}: {e}")
            return []
    
    async def _get_node_capabilities(self, node_id: str) -> Optional[NodeCapabilities]:
        """Get capabilities of a specific node"""
        key = f"node:capabilities:{node_id}"
        
        try:
            data = await self.server.get(key)
            if not data:
                return None
            
            caps_dict = msgpack.unpackb(data)
            return NodeCapabilities(**caps_dict)
            
        except Exception as e:
            print(f"Error getting capabilities for {node_id}: {e}")
            return None
    
    def _is_node_suitable(self, capabilities: NodeCapabilities, 
                         model_name: str, min_gpu_memory: float, 
                         max_latency_ms: float) -> bool:
        """Check if node meets requirements"""
        return (
            model_name in capabilities.available_models and
            capabilities.gpu_memory_gb >= min_gpu_memory and
            capabilities.inference_latency_p95 <= max_latency_ms and
            capabilities.current_load < 0.8 and  # Not overloaded
            time.time() - capabilities.last_heartbeat < 30  # Recent heartbeat
        )
    
    async def _heartbeat_loop(self):
        """Periodic heartbeat to update capabilities"""
        while True:
            try:
                # Update current system metrics
                await self._update_capabilities()
                await self._register_capabilities()
                await asyncio.sleep(10)  # Heartbeat every 10 seconds
            except Exception as e:
                print(f"Heartbeat error: {e}")
                await asyncio.sleep(5)