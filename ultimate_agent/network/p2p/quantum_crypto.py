import asyncio
import secrets
import hashlib
import hmac
import time
from typing import Dict, Optional, Tuple, Any
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class QuantumKey:
    """Secure quantum key with metadata"""
    key_id: str
    symmetric_key: bytes
    created_at: float
    peer_id: str
    sequence_number: int = 0
    
    def is_expired(self, ttl_seconds: int = 3600) -> bool:
        return time.time() - self.created_at > ttl_seconds

class QuantumEncryptionProtocol:
    """Production crypto implementation with quantum-resistant fallbacks"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.key_store: Dict[str, QuantumKey] = {}
        self.replay_cache: Dict[str, float] = {}
        self.sequence_numbers: Dict[str, int] = {}
        
        # Generate node keypair
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        
    async def quantum_encrypt(self, data: bytes, target_node: str) -> Dict[str, Any]:
        """Encrypt data with quantum-resistant methods"""
        try:
            # Get or create shared key
            quantum_key = await self._get_or_create_key(target_node)
            
            # Generate nonce and increment sequence
            nonce = secrets.token_bytes(12)
            quantum_key.sequence_number += 1
            
            # Derive encryption key using HKDF
            derived_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=nonce,
                info=f"{self.node_id}:{target_node}".encode()
            ).derive(quantum_key.symmetric_key)
            
            # Encrypt with AES-GCM (quantum-resistant for now)
            cipher = Cipher(
                algorithms.AES(derived_key),
                modes.GCM(nonce)
            )
            encryptor = cipher.encryptor()
            
            # Add sequence number to AAD
            seq_bytes = quantum_key.sequence_number.to_bytes(8, 'big')
            encryptor.authenticate_additional_data(seq_bytes)
            
            ciphertext = encryptor.update(data) + encryptor.finalize()
            
            # Create HMAC for integrity
            hmac_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"hmac_salt",
                info=b"quantum_p2p_hmac"
            ).derive(quantum_key.symmetric_key)
            
            message_hmac = hmac.new(
                hmac_key,
                nonce + seq_bytes + ciphertext + encryptor.tag,
                hashlib.sha256
            ).digest()
            
            return {
                "encrypted": True,
                "nonce": nonce.hex(),
                "ciphertext": ciphertext.hex(),
                "tag": encryptor.tag.hex(),
                "sequence": quantum_key.sequence_number,
                "key_id": quantum_key.key_id,
                "hmac": message_hmac.hex()
            }
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return {"encrypted": False, "error": str(e)}
    
    async def quantum_decrypt(self, encrypted_data: Dict[str, Any], sender_node: str) -> Optional[bytes]:
        """Decrypt quantum-encrypted data with replay protection"""
        try:
            key_id = encrypted_data["key_id"]
            if key_id not in self.key_store:
                logger.error(f"Unknown key ID: {key_id}")
                return None
                
            quantum_key = self.key_store[key_id]
            
            # Check sequence number for replay protection
            sequence = encrypted_data["sequence"]
            last_seq = self.sequence_numbers.get(sender_node, 0)
            
            if sequence <= last_seq:
                logger.error(f"Replay attack detected: {sequence} <= {last_seq}")
                return None
                
            # Verify HMAC first
            nonce = bytes.fromhex(encrypted_data["nonce"])
            ciphertext = bytes.fromhex(encrypted_data["ciphertext"])
            tag = bytes.fromhex(encrypted_data["tag"])
            received_hmac = bytes.fromhex(encrypted_data["hmac"])
            
            hmac_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"hmac_salt",
                info=b"quantum_p2p_hmac"
            ).derive(quantum_key.symmetric_key)
            
            seq_bytes = sequence.to_bytes(8, 'big')
            expected_hmac = hmac.new(
                hmac_key,
                nonce + seq_bytes + ciphertext + tag,
                hashlib.sha256
            ).digest()
            
            if not hmac.compare_digest(received_hmac, expected_hmac):
                logger.error("HMAC verification failed")
                return None
            
            # Derive decryption key
            derived_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=nonce,
                info=f"{sender_node}:{self.node_id}".encode()
            ).derive(quantum_key.symmetric_key)
            
            # Decrypt
            cipher = Cipher(
                algorithms.AES(derived_key),
                modes.GCM(nonce, tag)
            )
            decryptor = cipher.decryptor()
            decryptor.authenticate_additional_data(seq_bytes)
            
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Update sequence number
            self.sequence_numbers[sender_node] = sequence
            
            return plaintext
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    async def _get_or_create_key(self, peer_id: str) -> QuantumKey:
        """Get existing key or create new one"""
        key_id = f"{self.node_id}:{peer_id}"
        
        if key_id in self.key_store:
            key = self.key_store[key_id]
            if not key.is_expired():
                return key
                
        # Generate new symmetric key
        symmetric_key = secrets.token_bytes(32)
        
        quantum_key = QuantumKey(
            key_id=key_id,
            symmetric_key=symmetric_key,
            created_at=time.time(),
            peer_id=peer_id
        )
        
        self.key_store[key_id] = quantum_key
        logger.info(f"Created new quantum key for {peer_id}")
        
        return quantum_key
