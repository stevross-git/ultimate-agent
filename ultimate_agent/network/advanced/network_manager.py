#!/usr/bin/env python3
"""Advanced async network manager with basic security and NAT traversal."""

import asyncio
import json
import os
import secrets
import hmac
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Callable, Optional, Tuple



class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"


@dataclass
class NetworkMessage:
    message_id: str
    sender_id: str
    recipient_id: Optional[str]
    message_type: str
    payload: bytes
    timestamp: float = field(default_factory=time.time)

    def serialize(self) -> bytes:
        header = {
            "id": self.message_id,
            "sender": self.sender_id,
            "recipient": self.recipient_id,
            "type": self.message_type,
            "timestamp": self.timestamp,
            "size": len(self.payload),
        }
        header_bytes = json.dumps(header).encode()
        return len(header_bytes).to_bytes(4, "big") + header_bytes + self.payload

    @classmethod
    def deserialize(cls, data: bytes) -> "NetworkMessage":
        header_size = int.from_bytes(data[:4], "big")
        header = json.loads(data[4:4+header_size].decode())
        payload = data[4+header_size:4+header_size+header["size"]]
        return cls(
            message_id=header["id"],
            sender_id=header["sender"],
            recipient_id=header.get("recipient"),
            message_type=header["type"],
            payload=payload,
            timestamp=header["timestamp"],
        )


class NodeAuthenticator:
    """Simple HMAC based authenticator."""

    def __init__(self, secret: bytes):
        self.secret = secret

    def sign(self, data: bytes) -> str:
        return hmac.new(self.secret, data, hashlib.sha256).hexdigest()

    def verify(self, data: bytes, signature: str) -> bool:
        expected = self.sign(data)
        return hmac.compare_digest(expected, signature)



    """Placeholder NAT traversal helper returning an unknown NAT type."""

    def __init__(self) -> None:
        self.nat_type: str = "unknown"

    async def detect(self) -> str:
        """Detect NAT type (stub)."""
        await asyncio.sleep(0)
        return self.nat_type



class AdvancedNetworkManager:
    """Asynchronous TCP network manager with minimal security features."""

    def __init__(self, node_id: str, listen_port: int = 0, secret: bytes | None = None):
        self.node_id = node_id
        self.listen_port = listen_port
        self.secret = secret or secrets.token_bytes(32)

        self.auth = NodeAuthenticator(self.secret)
        self.nat = NATTraversalManager()

        self.nat_type: str = "unknown"


        self.server: Optional[asyncio.AbstractServer] = None
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.handlers: Dict[str, Callable[[NetworkMessage], None]] = {}
        self.metrics = {"sent": 0, "received": 0}
        self.running = False

    async def start(self) -> int:
        if self.running:
            return self.listen_port
        self.server = await asyncio.start_server(self._handle_client, "0.0.0.0", self.listen_port)
        if self.listen_port == 0:
            self.listen_port = self.server.sockets[0].getsockname()[1]
        self.running = True

        # Detect NAT type asynchronously
        try:
            self.nat_type = await self.nat.detect()
        except Exception:
            self.nat_type = "unknown"

        asyncio.create_task(self.server.serve_forever())
        return self.listen_port

    async def stop(self) -> None:
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        for info in list(self.connections.values()):
            info["writer"].close()
            await info["writer"].wait_closed()
        self.connections.clear()

    async def connect(self, node_id: str, host: str, port: int) -> bool:
        if node_id in self.connections:
            return True
        try:
            reader, writer = await asyncio.open_connection(host, port)
            await self._send_auth(writer)
            ok = await self._receive_auth(reader)
            if not ok:
                writer.close()
                await writer.wait_closed()
                return False
            self.connections[node_id] = {
                "reader": reader,
                "writer": writer,
                "state": ConnectionState.AUTHENTICATED,
            }
            asyncio.create_task(self._reader_loop(node_id, reader))
            return True
        except Exception:
            return False

    async def send(self, node_id: str, msg_type: str, payload: bytes) -> bool:
        if node_id not in self.connections:
            return False
        msg = NetworkMessage(
            message_id=os.urandom(8).hex(),
            sender_id=self.node_id,
            recipient_id=node_id,
            message_type=msg_type,
            payload=payload,
        )
        data = msg.serialize()
        writer = self.connections[node_id]["writer"]
        try:
            writer.write(len(data).to_bytes(4, "big") + data)
            await writer.drain()
            self.metrics["sent"] += 1
            return True
        except Exception:
            return False


    async def disconnect(self, node_id: str) -> None:
        """Disconnect from a peer and close the connection."""
        info = self.connections.pop(node_id, None)
        if info:
            info["writer"].close()
            await info["writer"].wait_closed()

    def register_handler(self, msg_type: str, handler: Callable[[NetworkMessage], Any]):
        """Register a handler for a given message type."""

        self.handlers[msg_type] = handler

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info("peername")
        if not await self._receive_auth(reader):
            writer.close()
            await writer.wait_closed()
            return
        await self._send_auth(writer)
        node_id = f"{peer[0]}:{peer[1]}"
        self.connections[node_id] = {
            "reader": reader,
            "writer": writer,
            "state": ConnectionState.AUTHENTICATED,
        }
        await self._reader_loop(node_id, reader)

    async def _send_auth(self, writer: asyncio.StreamWriter):
        nonce = os.urandom(8)
        sig = self.auth.sign(nonce)
        writer.write(len(nonce).to_bytes(1, "big") + nonce)
        writer.write(sig.encode() + b"\n")
        await writer.drain()

    async def _receive_auth(self, reader: asyncio.StreamReader) -> bool:
        size_data = await reader.readexactly(1)
        nonce = await reader.readexactly(size_data[0])
        sig = await reader.readline()
        sig = sig.strip().decode()
        return self.auth.verify(nonce, sig)

    async def _reader_loop(self, node_id: str, reader: asyncio.StreamReader):
        try:
            while True:
                size_data = await reader.readexactly(4)
                size = int.from_bytes(size_data, "big")
                data = await reader.readexactly(size)
                message = NetworkMessage.deserialize(data)
                self.metrics["received"] += 1
                handler = self.handlers.get(message.message_type)
                if handler:

                    result = handler(message)
                    if asyncio.iscoroutine(result):
                        await result

        except Exception:
            pass
        finally:
            if node_id in self.connections:


                self.connections[node_id]["writer"].close()
                await self.connections[node_id]["writer"].wait_closed()
                del self.connections[node_id]



__all__ = [
    "AdvancedNetworkManager",
    "ConnectionState",
    "NetworkMessage",

    "NATTraversalManager",
    "NodeAuthenticator",

]
