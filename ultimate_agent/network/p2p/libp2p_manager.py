# ultimate_agent/network/p2p/libp2p_manager.py
import asyncio
from libp2p import new_host
from libp2p.network.stream.net_stream_interface import INetStream
from libp2p.peer.peerinfo import info_from_p2p_addr
from libp2p.typing import TProtocol
import json

class LibP2PInferenceNetwork:
    """libp2p-based P2P network for AI inference"""
    
    INFERENCE_PROTOCOL_ID = TProtocol("/ai-inference/1.0.0")
    MODEL_SYNC_PROTOCOL_ID = TProtocol("/model-sync/1.0.0") 
    HEARTBEAT_PROTOCOL_ID = TProtocol("/heartbeat/1.0.0")
    
    def __init__(self, listen_addrs: List[str] = None):
        self.host = None
        self.listen_addrs = listen_addrs or ["/ip4/0.0.0.0/tcp/0"]
        self.connected_peers = {}
        self.inference_handlers = {}
        
    async def start(self):
        """Start the libp2p host"""
        self.host = new_host()
        
        # Set protocol handlers
        self.host.set_stream_handler(
            self.INFERENCE_PROTOCOL_ID, 
            self._handle_inference_stream
        )
        self.host.set_stream_handler(
            self.MODEL_SYNC_PROTOCOL_ID,
            self._handle_model_sync_stream  
        )
        self.host.set_stream_handler(
            self.HEARTBEAT_PROTOCOL_ID,
            self._handle_heartbeat_stream
        )
        
        # Start listening
        await self.host.get_network().listen(*self.listen_addrs)
        
        print(f"libp2p host started. Peer ID: {self.host.get_id()}")
        print(f"Listening on: {self.host.get_addrs()}")
    
    async def connect_to_peer(self, peer_addr: str):
        """Connect to a peer"""
        try:
            peer_info = info_from_p2p_addr(peer_addr)
            await self.host.connect(peer_info)
            self.connected_peers[str(peer_info.peer_id)] = peer_info
            print(f"Connected to peer: {peer_info.peer_id}")
        except Exception as e:
            print(f"Failed to connect to {peer_addr}: {e}")
    
    async def send_inference_request(self, peer_id: str, request_data: Dict) -> Dict:
        """Send inference request to peer"""
        try:
            stream = await self.host.new_stream(
                peer_id, 
                [self.INFERENCE_PROTOCOL_ID]
            )
            
            # Send request
            request_json = json.dumps(request_data).encode()
            await stream.write(len(request_json).to_bytes(4, 'big'))
            await stream.write(request_json)
            
            # Read response
            response_length = int.from_bytes(await stream.read(4), 'big')
            response_data = await stream.read(response_length)
            
            await stream.close()
            
            return json.loads(response_data.decode())
            
        except Exception as e:
            print(f"Error sending inference request to {peer_id}: {e}")
            return {"error": str(e)}
    
    async def _handle_inference_stream(self, stream: INetStream):
        """Handle incoming inference requests"""
        try:
            # Read request
            request_length = int.from_bytes(await stream.read(4), 'big')
            request_data = json.loads((await stream.read(request_length)).decode())
            
            # Process inference request
            response = await self._process_inference_request(request_data)
            
            # Send response
            response_json = json.dumps(response).encode()
            await stream.write(len(response_json).to_bytes(4, 'big'))
            await stream.write(response_json)
            
        except Exception as e:
            print(f"Error handling inference stream: {e}")
        finally:
            await stream.close()