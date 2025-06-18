# ultimate_agent/network/protocols/tensor_protocol.py
import struct
import numpy as np
import lz4
from typing import Dict, Any, Optional
from enum import Enum

class TensorType(Enum):
    FLOAT32 = 0
    FLOAT16 = 1
    INT32 = 2
    INT8 = 3
    BOOL = 4

class TensorProtocol:
    """Optimized binary protocol for tensor transmission"""
    
    # Protocol header format
    HEADER_FORMAT = "!IIIIII"  # magic, version, msg_type, data_length, checksum, flags
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MAGIC_NUMBER = 0x41494E46  # "AINF" in hex
    VERSION = 1
    
    # Message types
    MSG_INFERENCE_REQUEST = 1
    MSG_INFERENCE_RESPONSE = 2
    MSG_ERROR = 3
    MSG_HEARTBEAT = 4
    
    # Flags
    FLAG_COMPRESSED = 0x01
    FLAG_ENCRYPTED = 0x02
    FLAG_STREAMING = 0x04
    
    @staticmethod
    def serialize_tensor(tensor: np.ndarray, 
                        compress: bool = True,
                        compression_level: int = 3) -> bytes:
        """Serialize numpy tensor to optimized binary format"""
        
        # Determine tensor type
        dtype_map = {
            np.float32: TensorType.FLOAT32,
            np.float16: TensorType.FLOAT16, 
            np.int32: TensorType.INT32,
            np.int8: TensorType.INT8,
            np.bool_: TensorType.BOOL
        }
        
        tensor_type = dtype_map.get(tensor.dtype.type, TensorType.FLOAT32)
        
        # Tensor metadata
        metadata = struct.pack("!BBIII",
            tensor_type.value,      # 1 byte: tensor type
            len(tensor.shape),      # 1 byte: number of dimensions
            tensor.size,            # 4 bytes: total elements
            0,                      # 4 bytes: reserved
            0                       # 4 bytes: reserved
        )
        
        # Shape information
        shape_data = struct.pack(f"!{len(tensor.shape)}I", *tensor.shape)
        
        # Tensor data
        tensor_bytes = tensor.tobytes()
        
        # Compression
        if compress:
            tensor_bytes = lz4.block.compress(tensor_bytes, compression=compression_level)
        
        # Combine all parts
        payload = metadata + shape_data + tensor_bytes
        
        return payload
    
    @staticmethod
    def deserialize_tensor(data: bytes, compressed: bool = True) -> np.ndarray:
        """Deserialize binary data back to numpy tensor"""
        
        offset = 0
        
        # Parse metadata
        tensor_type_val, ndims, total_elements, _, _ = struct.unpack("!BBIII", data[offset:offset+14])
        offset += 14
        
        tensor_type = TensorType(tensor_type_val)
        
        # Parse shape
        shape = struct.unpack(f"!{ndims}I", data[offset:offset+ndims*4])
        offset += ndims * 4
        
        # Parse tensor data
        tensor_bytes = data[offset:]
        
        # Decompress if needed
        if compressed:
            tensor_bytes = lz4.block.decompress(tensor_bytes)
        
        # Convert back to numpy
        dtype_map = {
            TensorType.FLOAT32: np.float32,
            TensorType.FLOAT16: np.float16,
            TensorType.INT32: np.int32,
            TensorType.INT8: np.int8,
            TensorType.BOOL: np.bool_
        }
        
        dtype = dtype_map[tensor_type]
        tensor = np.frombuffer(tensor_bytes, dtype=dtype).reshape(shape)
        
        return tensor
    
    @staticmethod
    def create_message(msg_type: int, payload: bytes, 
                      compressed: bool = False, 
                      encrypted: bool = False,
                      streaming: bool = False) -> bytes:
        """Create complete protocol message"""
        
        flags = 0
        if compressed:
            flags |= TensorProtocol.FLAG_COMPRESSED
        if encrypted:
            flags |= TensorProtocol.FLAG_ENCRYPTED  
        if streaming:
            flags |= TensorProtocol.FLAG_STREAMING
        
        # Calculate checksum (simple CRC32)
        import zlib
        checksum = zlib.crc32(payload) & 0xffffffff
        
        # Create header
        header = struct.pack(TensorProtocol.HEADER_FORMAT,
            TensorProtocol.MAGIC_NUMBER,
            TensorProtocol.VERSION,
            msg_type,
            len(payload),
            checksum,
            flags
        )
        
        return header + payload
    
    @staticmethod
    def parse_message(data: bytes) -> Optional[Dict[str, Any]]:
        """Parse complete protocol message"""
        
        if len(data) < TensorProtocol.HEADER_SIZE:
            return None
        
        # Parse header
        magic, version, msg_type, data_length, checksum, flags = struct.unpack(
            TensorProtocol.HEADER_FORMAT, data[:TensorProtocol.HEADER_SIZE]
        )
        
        # Validate magic number and version
        if magic != TensorProtocol.MAGIC_NUMBER:
            raise ValueError("Invalid magic number")
        
        if version != TensorProtocol.VERSION:
            raise ValueError(f"Unsupported version: {version}")
        
        # Extract payload
        if len(data) < TensorProtocol.HEADER_SIZE + data_length:
            return None  # Incomplete message
        
        payload = data[TensorProtocol.HEADER_SIZE:TensorProtocol.HEADER_SIZE + data_length]
        
        # Verify checksum
        import zlib
        calculated_checksum = zlib.crc32(payload) & 0xffffffff
        if calculated_checksum != checksum:
            raise ValueError("Checksum mismatch")
        
        return {
            'type': msg_type,
            'payload': payload,
            'compressed': bool(flags & TensorProtocol.FLAG_COMPRESSED),
            'encrypted': bool(flags & TensorProtocol.FLAG_ENCRYPTED),
            'streaming': bool(flags & TensorProtocol.FLAG_STREAMING),
            'remaining_data': data[TensorProtocol.HEADER_SIZE + data_length:]
        }

class StreamingTensorSocket:
    """TCP socket optimized for streaming tensor data"""
    
    def __init__(self, socket):
        self.socket = socket
        self.buffer = b""
        
    async def send_tensor(self, tensor: np.ndarray, request_id: str = ""):
        """Send tensor with streaming support"""
        
        # Serialize tensor
        tensor_data = TensorProtocol.serialize_tensor(tensor, compress=True)
        
        # Create message payload with request ID
        payload = request_id.encode().ljust(32, b'\0') + tensor_data
        
        # Create message
        message = TensorProtocol.create_message(
            TensorProtocol.MSG_INFERENCE_REQUEST,
            payload,
            compressed=True,
            streaming=True
        )
        
        # Send in chunks to avoid blocking
        chunk_size = 64 * 1024  # 64KB chunks
        for i in range(0, len(message), chunk_size):
            chunk = message[i:i + chunk_size]
            await self.socket.send(chunk)
    
    async def receive_tensor(self) -> Optional[Dict[str, Any]]:
        """Receive tensor with streaming support"""
        
        while True:
            # Try to parse a complete message
            message = TensorProtocol.parse_message(self.buffer)
            
            if message:
                # Remove processed data from buffer
                payload_size = len(message['payload'])
                total_size = TensorProtocol.HEADER_SIZE + payload_size
                self.buffer = message['remaining_data']
                
                # Extract request ID and tensor data
                request_id = message['payload'][:32].decode().strip('\0')
                tensor_data = message['payload'][32:]
                
                # Deserialize tensor
                tensor = TensorProtocol.deserialize_tensor(
                    tensor_data, 
                    compressed=message['compressed']
                )
                
                return {
                    'request_id': request_id,
                    'tensor': tensor,
                    'type': message['type']
                }
            
            # Need more data
            try:
                chunk = await self.socket.recv(64 * 1024)
                if not chunk:
                    break  # Connection closed
                self.buffer += chunk
            except Exception:
                break
        
        return None