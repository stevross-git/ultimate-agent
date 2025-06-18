# ultimate_agent/ai/distributed/attention_protocol.py
import asyncio
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class AttentionShard:
    shard_id: int
    head_start: int
    head_end: int
    node_id: str
    layer_index: int

class DistributedAttentionCoordinator:
    """Coordinates multi-head attention across nodes"""
    
    def __init__(self, model_config: Dict):
        self.model_config = model_config
        self.num_heads = model_config['num_attention_heads']
        self.head_dim = model_config['hidden_size'] // self.num_heads
        self.shards = {}
        self.node_connections = {}
    
    def register_attention_shard(self, shard: AttentionShard, 
                               connection):
        """Register an attention shard with its node connection"""
        self.shards[shard.shard_id] = shard
        self.node_connections[shard.node_id] = connection
    
    async def distributed_attention(self,
                                  query: np.ndarray,
                                  key: np.ndarray,
                                  value: np.ndarray,
                                  layer_index: int,
                                  request_id: str) -> np.ndarray:
        """Perform distributed multi-head attention"""
        if not all(isinstance(x, np.ndarray) for x in [query, key, value]):
            raise ValueError("All inputs must be numpy arrays")

        if not (query.shape == key.shape == value.shape):
            raise ValueError(f"Shape mismatch: query={query.shape}, key={key.shape}, value={value.shape}")

        if len(query.shape) != 3:
            raise ValueError("Expected 3D tensors (batch, sequence, hidden)")

        if not isinstance(layer_index, int) or layer_index < 0:
            raise ValueError("Layer index must be a non-negative integer")

        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("Request ID must be a non-empty string")

        batch_size, seq_len, hidden_size = query.shape
        
        # Split Q, K, V across attention heads
        query_heads = self._split_heads(query)  # [batch, heads, seq, head_dim]
        key_heads = self._split_heads(key)
        value_heads = self._split_heads(value)
        
        # Distribute heads across shards
        shard_tasks = []
        layer_shards = [s for s in self.shards.values() if s.layer_index == layer_index]
        
        for shard in layer_shards:
            # Extract heads for this shard
            shard_query = query_heads[:, shard.head_start:shard.head_end]
            shard_key = key_heads[:, shard.head_start:shard.head_end] 
            shard_value = value_heads[:, shard.head_start:shard.head_end]
            
            # Send to shard node
            task = self._compute_attention_shard(
                shard, shard_query, shard_key, shard_value, request_id
            )
            shard_tasks.append(task)
        
        # Collect results from all shards
        shard_results = await asyncio.gather(*shard_tasks)
        
        # Concatenate attention outputs
        attention_output = np.concatenate(shard_results, axis=1)  # Concat on head dim
        
        # Reshape back to [batch, seq, hidden]
        return self._merge_heads(attention_output)
    
    async def _compute_attention_shard(self, 
                                     shard: AttentionShard,
                                     query: np.ndarray,
                                     key: np.ndarray,
                                     value: np.ndarray,
                                     request_id: str) -> np.ndarray:
        """Compute attention for a specific shard"""
        
        connection = self.node_connections[shard.node_id]
        
        # Prepare request
        request_data = {
            'type': 'attention_computation',
            'request_id': request_id,
            'shard_id': shard.shard_id,
            'layer_index': shard.layer_index,
            'query_shape': query.shape,
            'key_shape': key.shape,
            'value_shape': value.shape
        }
        
        # Send tensors
        await connection.send_control_message(request_data)
        await connection.send_tensor(query, f"{request_id}_query")
        await connection.send_tensor(key, f"{request_id}_key") 
        await connection.send_tensor(value, f"{request_id}_value")
        
        # Receive result
        response = await connection.receive_tensor()
        
        if response['type'] == 'attention_result':
            return response['tensor']
        else:
            raise Exception(f"Attention computation failed: {response.get('error')}")
    
    def _split_heads(self, tensor: np.ndarray) -> np.ndarray:
        """Split tensor into attention heads"""
        batch_size, seq_len, hidden_size = tensor.shape
        
        # Reshape to [batch, seq, heads, head_dim]
        tensor = tensor.reshape(batch_size, seq_len, self.num_heads, self.head_dim)
        
        # Transpose to [batch, heads, seq, head_dim]
        return tensor.transpose(0, 2, 1, 3)
    
    def _merge_heads(self, tensor: np.ndarray) -> np.ndarray:
        """Merge attention heads back"""
        batch_size, num_heads, seq_len, head_dim = tensor.shape
        
        # Transpose to [batch, seq, heads, head_dim]
        tensor = tensor.transpose(0, 2, 1, 3)
        
        # Reshape to [batch, seq, hidden_size]
        return tensor.reshape(batch_size, seq_len, num_heads * head_dim)

class AttentionShardProcessor:
    """Processes attention computation for a specific shard"""
    
    def __init__(self, shard_config: Dict):
        self.shard_config = shard_config
        self.head_start = shard_config['head_start']
        self.head_end = shard_config['head_end']
        self.num_heads = self.head_end - self.head_start
        
    async def compute_attention(self, 
                              query: np.ndarray,
                              key: np.ndarray,
                              value: np.ndarray) -> np.ndarray:
        """Compute multi-head attention for assigned heads"""
        
        batch_size, num_heads, seq_len, head_dim = query.shape
        
        # Compute attention scores
        scores = np.matmul(query, key.transpose(0, 1, 3, 2))  # [batch, heads, seq, seq]
        scores = scores / np.sqrt(head_dim)
        
        # Apply softmax
        attention_probs = self._softmax(scores)
        
        # Apply attention to values
        attention_output = np.matmul(attention_probs, value)  # [batch, heads, seq, head_dim]
        
        return attention_output
    
    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Numerically stable softmax"""
        x_max = np.max(x, axis=-1, keepdims=True)
        x_shifted = np.clip(x - x_max, -700, 700)
        exp_x = np.exp(x_shifted)
        return exp_x / (np.sum(exp_x, axis=-1, keepdims=True) + 1e-8)
