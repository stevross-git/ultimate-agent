"""Common protocol messages for Quantum P2P."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import time

class MessageType(str, Enum):
    NODE_ANNOUNCE = "node_announce"
    NODE_QUERY = "node_query"
    NODE_RESPONSE = "node_response"
    MODEL_ANNOUNCE = "model_announce"
    MODEL_REQUEST = "model_request"
    MODEL_SHARD_TRANSFER = "model_shard_transfer"
    MODEL_SYNC = "model_sync"
    INFERENCE_REQUEST = "inference_request"
    INFERENCE_RESPONSE = "inference_response"
    PARTIAL_RESULT = "partial_result"
    HEARTBEAT = "heartbeat"
    NETWORK_UPDATE = "network_update"
    RESULT_CONSENSUS = "result_consensus"
    FAULT_NOTIFICATION = "fault_notification"
    QUANTUM_KEY_EXCHANGE = "quantum_key_exchange"
    QUANTUM_ENCRYPTED_MESSAGE = "quantum_encrypted_message"

class QuantumEncryptedPayload(BaseModel):
    encrypted_data: str = Field(..., description="Hex encoded")
    quantum_signature: str = Field(..., description="HMAC signature")
    entanglement_id: str = Field(...)
    encryption_timestamp: float = Field(default_factory=time.time)
    original_type: str = Field(...)
    key_rotation_id: Optional[str] = None
    nonce: str = Field(...)
    sequence_number: int = Field(default=0)

class RouteInfo(BaseModel):
    route: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    latency_estimate: float = 0.0
    bandwidth_estimate: float = 0.0
    failure_rate: float = 0.0
    optimization_reason: str = ""

__all__ = ["MessageType", "QuantumEncryptedPayload", "RouteInfo"]
