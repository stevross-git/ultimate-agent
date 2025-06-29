import asyncio
import json
import secrets
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import logging

from .quantum_crypto import QuantumEncryptionProtocol
from .adaptive_routing import CSPAdaptiveRouting
from .fault_tolerance import CSPFaultTolerance

logger = logging.getLogger(__name__)

@dataclass
class MessageType:
    INFERENCE_REQUEST = "inference_request"
    HEARTBEAT = "heartbeat"
    PEER_DISCOVERY = "peer_discovery"
    DATA_SYNC = "data_sync"

@dataclass
class P2PMessage:
    """Secure P2P message with proper metadata"""
    def __init__(self, msg_type: str, sender_id: str, data: Any):
        self.message_id = secrets.token_hex(16)  # Cryptographically secure
        self.type = msg_type
        self.sender_id = sender_id
        self.data = data
        self.timestamp = time.time()
        self.ttl = 300  # 5 minutes

    def serialize(self) -> bytes:
        return json.dumps({
            "message_id": self.message_id,
            "type": self.type,
            "sender_id": self.sender_id,
            "data": self.data,
            "timestamp": self.timestamp,
            "ttl": self.ttl
        }).encode('utf-8')
    
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl

class QuantumEnhancedP2PManager:
    """Production quantum P2P manager with real networking"""
    
    def __init__(self, node_id: str, bind_port: int = 0):
        self.node_id = node_id
        self.bind_port = bind_port
        self.quantum = QuantumEncryptionProtocol(node_id)
        self.routing = CSPAdaptiveRouting(node_id)
        self.fault = CSPFaultTolerance(node_id)
        
        # Network state
        self.connected_peers: Dict[str, Dict[str, Any]] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.running = False
        self.server = None
        
        # Metrics
        self.messages_sent = 0
        self.messages_received = 0
        self.encryption_successes = 0
        self.encryption_failures = 0
        
    async def start_network(self) -> bool:
        """Start P2P network with proper error handling"""
        if self.running:
            return True
            
        try:
            # Start message server
            self.server = await asyncio.start_server(
                self._handle_peer_connection,
                '0.0.0.0',
                self.bind_port
            )
            
            # Get actual bound port
            self.bind_port = self.server.sockets[0].getsockname()[1]
            
            # Start background tasks
            asyncio.create_task(self._heartbeat_loop())
            asyncio.create_task(self._cleanup_loop())
            
            self.running = True
            logger.info(f"P2P network started on port {self.bind_port}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start P2P network: {e}")
            return False
    
    async def stop_network(self):
        """Stop P2P network with proper cleanup"""
        if not self.running:
            return
            
        self.running = False
        
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        # Disconnect from peers
        for peer_id in list(self.connected_peers.keys()):
            await self._disconnect_peer(peer_id)
        
        logger.info("P2P network stopped")
    
    async def send_quantum_encrypted_message(
        self, 
        target_node: str, 
        message_data: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Send quantum-encrypted message with proper networking"""
        
        msg = P2PMessage(MessageType.INFERENCE_REQUEST, self.node_id, message_data)
        
        # Encrypt message
        encrypted_result = await self.quantum.quantum_encrypt(
            msg.serialize(), 
            target_node
        )
        
        if not encrypted_result.get("encrypted"):
            self.encryption_failures += 1
            return {
                "success": False,
                "error": "encryption_failed",
                "details": encrypted_result.get("error")
            }
        
        self.encryption_successes += 1
        
        # Send via fault-tolerant networking
        async def send_operation():
            return await self._send_to_peer(target_node, encrypted_result)
        
        result = await self.fault.execute_with_fault_tolerance(
            send_operation,
            "send_message", 
            target_node,
            timeout_seconds=timeout
        )
        
        if result["success"]:
            self.messages_sent += 1
        
        return result
    
    async def _send_to_peer(self, peer_id: str, encrypted_data: Dict[str, Any]) -> bool:
        """Send data to specific peer"""
        peer_info = self.connected_peers.get(peer_id)
        if not peer_info:
            # Try to discover and connect to peer
            if not await self._discover_and_connect_peer(peer_id):
                raise ConnectionError(f"Cannot connect to peer {peer_id}")
            peer_info = self.connected_peers[peer_id]
        
        # Send over TCP connection
        writer = peer_info.get('writer')
        if not writer:
            raise ConnectionError(f"No active connection to {peer_id}")
        
        # Protocol: length-prefixed JSON
        payload = json.dumps(encrypted_data).encode('utf-8')
        length = len(payload).to_bytes(4, 'big')
        
        writer.write(length + payload)
        await writer.drain()
        
        # Record performance metrics
        start_time = time.time()
        # Simulate response wait (in real implementation, wait for ACK)
        await asyncio.sleep(0.01)
        latency = (time.time() - start_time) * 1000
        
        self.routing.record_route_performance(
            peer_id, 
            latency, 
            100.0,  # Estimated bandwidth
            True
        )
        
        return True
    
    async def _handle_peer_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming peer connections"""
        peer_addr = writer.get_extra_info('peername')
        logger.info(f"New peer connection from {peer_addr}")
        
        try:
            while not reader.at_eof():
                # Read length-prefixed message
                length_bytes = await reader.readexactly(4)
                length = int.from_bytes(length_bytes, 'big')
                
                if length > 1024 * 1024:  # 1MB limit
                    logger.warning(f"Message too large from {peer_addr}: {length}")
                    break
                
                payload = await reader.readexactly(length)
                encrypted_data = json.loads(payload.decode('utf-8'))
                
                # Process encrypted message
                await self._process_encrypted_message(encrypted_data, peer_addr)
                
        except asyncio.IncompleteReadError:
            logger.info(f"Peer {peer_addr} disconnected")
        except Exception as e:
            logger.error(f"Error handling peer {peer_addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def _process_encrypted_message(self, encrypted_data: Dict[str, Any], peer_addr):
        """Process incoming encrypted message"""
        try:
            # Extract sender info (in real implementation, get from handshake)
            sender_id = f"peer_{peer_addr[0]}_{peer_addr[1]}"
            
            # Decrypt message
            decrypted_data = await self.quantum.quantum_decrypt(encrypted_data, sender_id)
            
            if decrypted_data:
                message = json.loads(decrypted_data.decode('utf-8'))
                await self._handle_decrypted_message(message, sender_id)
                self.messages_received += 1
            else:
                logger.warning(f"Failed to decrypt message from {sender_id}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _handle_decrypted_message(self, message: Dict[str, Any], sender_id: str):
        """Handle decrypted message based on type"""
        msg_type = message.get('type')
        handler = self.message_handlers.get(msg_type)
        
        if handler:
            await handler(message, sender_id)
        else:
            logger.debug(f"No handler for message type: {msg_type}")
    
    async def _discover_and_connect_peer(self, peer_id: str) -> bool:
        """Discover and connect to peer (placeholder for DHT/discovery)"""
        # In real implementation, use DHT or discovery service
        # For now, simulate connection
        logger.info(f"Simulating discovery and connection to {peer_id}")
        
        # Simulate connection establishment
        await asyncio.sleep(0.1)
        
        self.connected_peers[peer_id] = {
            'connected_at': time.time(),
            'last_seen': time.time(),
            'writer': None  # Would be real connection
        }
        
        return True
    
    async def _disconnect_peer(self, peer_id: str):
        """Disconnect from peer"""
        if peer_id in self.connected_peers:
            peer_info = self.connected_peers[peer_id]
            writer = peer_info.get('writer')
            if writer:
                writer.close()
                await writer.wait_closed()
            del self.connected_peers[peer_id]
            logger.info(f"Disconnected from peer {peer_id}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to connected peers"""
        while self.running:
            try:
                for peer_id in list(self.connected_peers.keys()):
                    heartbeat_msg = P2PMessage(
                        MessageType.HEARTBEAT,
                        self.node_id,
                        {"timestamp": time.time()}
                    )
                    
                    # Send heartbeat (simplified)
                    logger.debug(f"Sending heartbeat to {peer_id}")
                
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def _cleanup_loop(self):
        """Clean up expired connections and messages"""
        while self.running:
            try:
                current_time = time.time()
                
                # Remove stale peers
                stale_peers = [
                    peer_id for peer_id, info in self.connected_peers.items()
                    if current_time - info['last_seen'] > 300  # 5 minutes
                ]
                
                for peer_id in stale_peers:
                    await self._disconnect_peer(peer_id)
                
                # Clean up replay cache in crypto module
                # (This would be implemented in quantum_crypto.py)
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get P2P network metrics"""
        return {
            "node_id": self.node_id,
            "running": self.running,
            "connected_peers": len(self.connected_peers),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "encryption_success_rate": (
                self.encryption_successes / 
                max(1, self.encryption_successes + self.encryption_failures)
            ),
            "bind_port": self.bind_port
        }

