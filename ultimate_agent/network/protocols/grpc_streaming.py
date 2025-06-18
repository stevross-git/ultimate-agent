# ultimate_agent/network/protocols/grpc_streaming.py
import grpc
import asyncio
import numpy as np
import pickle
import zlib
from concurrent import futures
from typing import AsyncIterator, Dict, Any
import ultimate_agent.network.protocols.inference_pb2 as inference_pb2
import ultimate_agent.network.protocols.inference_pb2_grpc as inference_pb2_grpc

class DistributedInferenceServicer(inference_pb2_grpc.DistributedInferenceServicer):
    """gRPC servicer for distributed AI inference"""
    
    def __init__(self, model_manager, shard_manager):
        self.model_manager = model_manager
        self.shard_manager = shard_manager
        
    async def StreamingInference(self, 
                                request_iterator: AsyncIterator[inference_pb2.InferenceChunk], 
                                context) -> AsyncIterator[inference_pb2.InferenceChunk]:
        """Handle streaming inference requests"""
        
        try:
            # Collect input chunks
            input_chunks = []
            metadata = None
            
            async for chunk in request_iterator:
                if chunk.HasField('metadata'):
                    metadata = {
                        'model_name': chunk.metadata.model_name,
                        'shard_index': chunk.metadata.shard_index,
                        'sequence_length': chunk.metadata.sequence_length,
                        'batch_size': chunk.metadata.batch_size,
                        'request_id': chunk.metadata.request_id
                    }
                
                if chunk.tensor_data:
                    input_chunks.append(chunk.tensor_data)
            
            if not metadata:
                yield inference_pb2.InferenceChunk(
                    error="Missing metadata in request"
                )
                return
            
            # Reconstruct tensor data
            tensor_data = b''.join(input_chunks)
            decompressed_data = zlib.decompress(tensor_data)
            input_tensor = pickle.loads(decompressed_data)
            
            # Process inference
            async for output_chunk in self._process_shard_inference(
                input_tensor, metadata
            ):
                yield output_chunk
                
        except Exception as e:
            yield inference_pb2.InferenceChunk(
                error=f"Inference error: {str(e)}"
            )
    
    async def _process_shard_inference(self, input_tensor: np.ndarray, 
                                     metadata: Dict) -> AsyncIterator[inference_pb2.InferenceChunk]:
        """Process inference for a specific model shard"""
        
        model_name = metadata['model_name']
        shard_index = metadata['shard_index']
        request_id = metadata['request_id']
        
        try:
            # Get model shard
            model_shard = await self.shard_manager.get_shard(model_name, shard_index)
            
            if not model_shard:
                yield inference_pb2.InferenceChunk(
                    error=f"Model shard {shard_index} not found"
                )
                return
            
            # Process inference in chunks for streaming
            output_generator = model_shard.stream_inference(input_tensor)
            
            chunk_index = 0
            async for output_tensor in output_generator:
                # Serialize and compress output
                serialized_output = pickle.dumps(output_tensor)
                compressed_output = zlib.compress(serialized_output)
                
                # Split into chunks if needed (gRPC message size limit)
                chunk_size = 4 * 1024 * 1024  # 4MB chunks
                
                for i in range(0, len(compressed_output), chunk_size):
                    chunk_data = compressed_output[i:i + chunk_size]
                    
                    chunk = inference_pb2.InferenceChunk(
                        tensor_data=chunk_data,
                        chunk_index=chunk_index,
                        is_final=(i + chunk_size >= len(compressed_output))
                    )
                    
                    if chunk_index == 0:
                        # Add metadata to first chunk
                        chunk.metadata.CopyFrom(inference_pb2.InferenceMetadata(
                            request_id=request_id,
                            shard_index=shard_index,
                            total_chunks=len(compressed_output) // chunk_size + 1
                        ))
                    
                    yield chunk
                    chunk_index += 1
                    
        except Exception as e:
            yield inference_pb2.InferenceChunk(
                error=f"Shard inference error: {str(e)}"
            )

class DistributedInferenceClient:
    """gRPC client for distributed inference"""
    
    def __init__(self, server_address: str):
        self.channel = grpc.aio.insecure_channel(server_address)
        self.stub = inference_pb2_grpc.DistributedInferenceStub(self.channel)
    
    async def stream_inference(self, input_tensor: np.ndarray, 
                             model_name: str, shard_index: int,
                             request_id: str) -> np.ndarray:
        """Send streaming inference request"""
        
        # Serialize and compress input
        serialized_input = pickle.dumps(input_tensor)
        compressed_input = zlib.compress(serialized_input)
        
        # Create request iterator
        async def request_iterator():
            # Send metadata first
            metadata_chunk = inference_pb2.InferenceChunk(
                metadata=inference_pb2.InferenceMetadata(
                    model_name=model_name,
                    shard_index=shard_index,
                    sequence_length=input_tensor.shape[1] if len(input_tensor.shape) > 1 else 1,
                    batch_size=input_tensor.shape[0] if len(input_tensor.shape) > 0 else 1,
                    request_id=request_id
                )
            )
            yield metadata_chunk
            
            # Send tensor data in chunks
            chunk_size = 4 * 1024 * 1024  # 4MB chunks
            for i in range(0, len(compressed_input), chunk_size):
                chunk_data = compressed_input[i:i + chunk_size]
                yield inference_pb2.InferenceChunk(tensor_data=chunk_data)
        
        # Stream request and collect response
        response_chunks = []
        
        async for response_chunk in self.stub.StreamingInference(request_iterator()):
            if response_chunk.error:
                raise Exception(f"Server error: {response_chunk.error}")
            
            if response_chunk.tensor_data:
                response_chunks.append(response_chunk.tensor_data)
        
        # Reconstruct response tensor
        if response_chunks:
            response_data = b''.join(response_chunks)
            decompressed_response = zlib.decompress(response_data)
            return pickle.loads(decompressed_response)
        
        return None