# ultimate_agent/network/protocols/webrtc_inference.py
import asyncio
import json
from aiortc import RTCPeerConnection, RTCDataChannel, RTCConfiguration, RTCIceServer
from aiortc.contrib.signaling import BYE, add_signaling_arguments, create_signaling
import numpy as np
import pickle
import zlib

class WebRTCInferenceNode:
    """WebRTC-based inference node for browser compatibility"""
    
    def __init__(self, signaling_server: str = None):
        self.pc = RTCPeerConnection(configuration=RTCConfiguration(
            iceServers=[
                RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
                RTCIceServer(urls=["stun:stun1.l.google.com:19302"])
            ]
        ))
        self.signaling = None
        self.data_channels = {}
        self.inference_handlers = {}
        
        if signaling_server:
            self.signaling = create_signaling(signaling_server)
    
    async def start(self):
        """Start WebRTC node"""
        if self.signaling:
            await self.signaling.connect()
        
        # Set up peer connection event handlers
        @self.pc.on("datachannel")
        def on_datachannel(channel: RTCDataChannel):
            self._setup_datachannel(channel)
        
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"WebRTC connection state: {self.pc.connectionState}")
    
    def _setup_datachannel(self, channel: RTCDataChannel):
        """Setup data channel for inference communication"""
        
        @channel.on("open")
        def on_open():
            print(f"Data channel {channel.label} opened")
            self.data_channels[channel.label] = channel
        
        @channel.on("message")
        async def on_message(message):
            if isinstance(message, str):
                await self._handle_control_message(channel, json.loads(message))
            else:
                await self._handle_tensor_data(channel, message)
    
    async def _handle_control_message(self, channel: RTCDataChannel, message: Dict):
        """Handle control messages"""
        msg_type = message.get('type')
        
        if msg_type == 'inference_request':
            # Prepare for tensor data
            request_id = message['request_id']
            model_name = message['model_name']
            self.inference_handlers[request_id] = {
                'channel': channel,
                'model_name': model_name,
                'chunks': [],
                'expected_chunks': message.get('total_chunks', 1)
            }
            
            # Send acknowledgment
            await self._send_control_message(channel, {
                'type': 'inference_ack',
                'request_id': request_id
            })
        
        elif msg_type == 'inference_complete':
            request_id = message['request_id']
            if request_id in self.inference_handlers:
                await self._process_inference_request(request_id)
    
    async def _handle_tensor_data(self, channel: RTCDataChannel, data: bytes):
        """Handle incoming tensor data"""
        # Data format: [request_id:32][chunk_index:4][data]
        request_id = data[:32].decode().strip()
        chunk_index = int.from_bytes(data[32:36], 'big')
        tensor_data = data[36:]
        
        if request_id in self.inference_handlers:
            handler = self.inference_handlers[request_id]
            handler['chunks'].append((chunk_index, tensor_data))
            
            # Check if all chunks received
            if len(handler['chunks']) >= handler['expected_chunks']:
                await self._process_inference_request(request_id)
    
    async def _process_inference_request(self, request_id: str):
        """Process complete inference request"""
        handler = self.inference_handlers[request_id]
        channel = handler['channel']
        model_name = handler['model_name']
        
        try:
            # Reconstruct tensor data
            sorted_chunks = sorted(handler['chunks'], key=lambda x: x[0])
            tensor_data = b''.join([chunk[1] for chunk in sorted_chunks])
            
            # Decompress and deserialize
            decompressed_data = zlib.decompress(tensor_data)
            input_tensor = pickle.loads(decompressed_data)
            
            # Run inference (this would call your AI manager)
            output_tensor = await self._run_model_inference(model_name, input_tensor)
            
            # Serialize and compress result
            serialized_output = pickle.dumps(output_tensor)
            compressed_output = zlib.compress(serialized_output)
            
            # Send result back
            await self._send_tensor_response(channel, request_id, compressed_output)
            
        except Exception as e:
            await self._send_control_message(channel, {
                'type': 'inference_error',
                'request_id': request_id,
                'error': str(e)
            })
        finally:
            # Cleanup
            if request_id in self.inference_handlers:
                del self.inference_handlers[request_id]
    
    async def _send_tensor_response(self, channel: RTCDataChannel, 
                                  request_id: str, data: bytes):
        """Send tensor response in chunks"""
        chunk_size = 16 * 1024  # 16KB chunks for WebRTC
        total_chunks = len(data) // chunk_size + (1 if len(data) % chunk_size else 0)
        
        # Send response header
        await self._send_control_message(channel, {
            'type': 'inference_response',
            'request_id': request_id,
            'total_chunks': total_chunks
        })
        
        # Send data chunks
        for i in range(0, len(data), chunk_size):
            chunk_data = data[i:i + chunk_size]
            chunk_index = i // chunk_size
            
            # Format: [request_id:32][chunk_index:4][data]
            message = (
                request_id.ljust(32).encode()[:32] +
                chunk_index.to_bytes(4, 'big') +
                chunk_data
            )
            
            channel.send(message)
        
        # Send completion message
        await self._send_control_message(channel, {
            'type': 'inference_response_complete',
            'request_id': request_id
        })
    
    async def _send_control_message(self, channel: RTCDataChannel, message: Dict):
        """Send control message"""
        channel.send(json.dumps(message))
    
    async def connect_to_peer(self, peer_id: str) -> RTCDataChannel:
        """Connect to peer and create data channel"""
        # Create data channel
        channel = self.pc.createDataChannel(f"inference-{peer_id}")
        self._setup_datachannel(channel)
        
        # Create and send offer
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        
        if self.signaling:
            await self.signaling.send(offer)
            
            # Wait for answer
            while True:
                obj = await self.signaling.receive()
                
                if isinstance(obj, RTCSessionDescription):
                    await self.pc.setRemoteDescription(obj)
                    break
                elif obj is BYE:
                    print("Peer disconnected")
                    break
        
        return channel