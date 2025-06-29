"""Simplified quantum encryption utilities."""

import hashlib
import hmac
import secrets
from typing import Dict

from painet_common.protocol.messages import QuantumEncryptedPayload


class QuantumEncryptionProtocol:
    """Basic XOR + HMAC based encryption"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.keys: Dict[str, bytes] = {}

    def _ensure_key(self, peer_id: str) -> bytes:
        if peer_id not in self.keys:
            self.keys[peer_id] = secrets.token_bytes(32)
        return self.keys[peer_id]

    def quantum_key_distribution(self, peer_id: str) -> str:
        self.keys[peer_id] = secrets.token_bytes(32)
        return peer_id

    def quantum_encrypt(self, data: bytes, peer_id: str) -> QuantumEncryptedPayload:
        key = self._ensure_key(peer_id)
        encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        signature = hmac.new(key, data, hashlib.sha256).hexdigest()
        return QuantumEncryptedPayload(
            encrypted_data=encrypted.hex(),
            quantum_signature=signature,
            entanglement_id=peer_id,
            original_type="",
            nonce=secrets.token_hex(8),
            sequence_number=0,
        )

    def quantum_decrypt(self, payload: QuantumEncryptedPayload, peer_id: str) -> bytes:
        key = self._ensure_key(peer_id)
        encrypted = bytes.fromhex(payload.encrypted_data)
        data = bytes(b ^ key[i % len(key)] for i, b in enumerate(encrypted))
        expected = hmac.new(key, data, hashlib.sha256).hexdigest()
        if expected != payload.quantum_signature:
            raise ValueError("HMAC mismatch")
        return data
