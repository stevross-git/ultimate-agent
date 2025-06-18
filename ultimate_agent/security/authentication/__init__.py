#!/usr/bin/env python3
"""
ultimate_agent/security/authentication/__init__.py
Security and authentication management
"""

import time
import hashlib
import secrets
import platform
import uuid
import base64
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import hmac


class SecurityManager:
    """Manages security, authentication, and encryption"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.encryption_key = None
        self.auth_tokens = {}
        self.failed_attempts = {}
        self.security_events = []
        self.api_keys = {}
        
        # Security configuration
        self.max_login_attempts = self.config.getint('SECURITY', 'max_login_attempts', fallback=3)
        self.token_expiry = self.config.getint('SECURITY', 'auth_token_expiry', fallback=3600)
        self.encryption_enabled = self.config.getboolean('SECURITY', 'encryption_enabled', fallback=True)
        
        self.init_security()
    
    def init_security(self):
        """Initialize security systems"""
        try:
            # Generate encryption key
            key_data = f"{platform.node()}-{uuid.getnode()}-security"
            self.encryption_key = hashlib.sha256(key_data.encode()).digest()
            
            # Generate master API key
            self.master_api_key = self._generate_api_key("master")
            
            # Initialize security audit log
            self._log_security_event("system", "security_initialized", {
                'encryption_enabled': self.encryption_enabled,
                'max_login_attempts': self.max_login_attempts,
                'token_expiry': self.token_expiry
            })
            
            print("🔒 Security systems initialized")
            
        except Exception as e:
            print(f"⚠️ Security initialization warning: {e}")
    
    def generate_auth_token(self, agent_id: str, permissions: List[str] = None) -> str:
        """Generate authentication token"""
        try:
            token_id = secrets.token_urlsafe(32)
            expires_at = time.time() + self.token_expiry
            
            token_data = {
                'token_id': token_id,
                'agent_id': agent_id,
                'created_at': time.time(),
                'expires_at': expires_at,
                'permissions': permissions or ['read', 'write'],
                'used_count': 0,
                'last_used': None,
                'source_ip': None
            }
            
            # Create signed token
            signed_token = self._sign_token(token_data)
            self.auth_tokens[token_id] = token_data
            
            self._log_security_event("auth", "token_generated", {
                'agent_id': agent_id,
                'token_id': token_id,
                'permissions': permissions
            })
            
            return signed_token
            
        except Exception as e:
            self._log_security_event("auth", "token_generation_failed", {
                'agent_id': agent_id,
                'error': str(e)
            })
            raise
    
    def validate_auth_token(self, token: str, required_permission: str = None) -> Dict[str, Any]:
        """Validate authentication token"""
        try:
            # Verify token signature
            token_data = self._verify_token(token)
            if not token_data:
                return {'valid': False, 'error': 'Invalid token signature'}
            
            token_id = token_data.get('token_id')
            if token_id not in self.auth_tokens:
                return {'valid': False, 'error': 'Token not found'}
            
            stored_token = self.auth_tokens[token_id]
            
            # Check expiration
            if time.time() > stored_token['expires_at']:
                self._revoke_token(token_id)
                return {'valid': False, 'error': 'Token expired'}
            
            # Check permissions
            if required_permission:
                permissions = stored_token.get('permissions', [])
                if required_permission not in permissions and 'admin' not in permissions:
                    return {'valid': False, 'error': 'Insufficient permissions'}
            
            # Update usage stats
            stored_token['used_count'] += 1
            stored_token['last_used'] = time.time()
            
            return {
                'valid': True,
                'agent_id': stored_token['agent_id'],
                'permissions': stored_token['permissions'],
                'token_id': token_id
            }
            
        except Exception as e:
            self._log_security_event("auth", "token_validation_failed", {
                'error': str(e)
            })
            return {'valid': False, 'error': 'Token validation failed'}
    
    def _sign_token(self, token_data: Dict) -> str:
        """Sign token data"""
        token_json = json.dumps(token_data, sort_keys=True)
        signature = hmac.new(
            self.encryption_key,
            token_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Combine token and signature
        signed_token = base64.b64encode(
            json.dumps({
                'data': token_data,
                'signature': signature
            }).encode()
        ).decode()
        
        return signed_token
    
    def _verify_token(self, token: str) -> Optional[Dict]:
        """Verify token signature"""
        try:
            decoded = json.loads(base64.b64decode(token).decode())
            token_data = decoded['data']
            signature = decoded['signature']
            
            # Recalculate signature
            token_json = json.dumps(token_data, sort_keys=True)
            expected_signature = hmac.new(
                self.encryption_key,
                token_json.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if hmac.compare_digest(signature, expected_signature):
                return token_data
            else:
                return None
                
        except Exception:
            return None
    
    def _revoke_token(self, token_id: str) -> bool:
        """Revoke authentication token"""
        if token_id in self.auth_tokens:
            del self.auth_tokens[token_id]
            self._log_security_event("auth", "token_revoked", {
                'token_id': token_id
            })
            return True
        return False
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using AES encryption"""
        if not self.encryption_enabled:
            return data
        
        try:
            from cryptography.fernet import Fernet
            
            # Use first 32 bytes of key for Fernet (base64 encoded)
            fernet_key = base64.urlsafe_b64encode(self.encryption_key[:32])
            fernet = Fernet(fernet_key)
            
            return fernet.encrypt(data)
            
        except ImportError:
            # Fallback to simple XOR encryption
            return self._xor_encrypt(data)
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data"""
        if not self.encryption_enabled:
            return encrypted_data
        
        try:
            from cryptography.fernet import Fernet
            
            fernet_key = base64.urlsafe_b64encode(self.encryption_key[:32])
            fernet = Fernet(fernet_key)
            
            return fernet.decrypt(encrypted_data)
            
        except ImportError:
            # Fallback to simple XOR encryption
            return self._xor_encrypt(encrypted_data)
    
    def _xor_encrypt(self, data: bytes) -> bytes:
        """Simple XOR encryption as fallback"""
        key = self.encryption_key
        key_len = len(key)
        
        return bytes(data[i] ^ key[i % key_len] for i in range(len(data)))
    
    def hash_password(self, password: str, salt: str = None) -> Dict[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 for password hashing
        import hashlib
        
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000  # iterations
        )
        
        return {
            'hash': hashed.hex(),
            'salt': salt,
            'algorithm': 'pbkdf2_sha256',
            'iterations': 100000
        }
    
    def verify_password(self, password: str, hash_data: Dict[str, str]) -> bool:
        """Verify password against hash"""
        try:
            import hashlib
            
            hashed = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                hash_data['salt'].encode(),
                hash_data.get('iterations', 100000)
            )
            
            return hmac.compare_digest(hashed.hex(), hash_data['hash'])
            
        except Exception:
            return False
    
    def _generate_api_key(self, key_type: str) -> str:
        """Generate API key"""
        key_id = secrets.token_urlsafe(16)
        key_secret = secrets.token_urlsafe(32)
        
        api_key = f"{key_type}_{key_id}_{key_secret}"
        
        self.api_keys[key_id] = {
            'key_id': key_id,
            'key_type': key_type,
            'created_at': time.time(),
            'last_used': None,
            'usage_count': 0,
            'active': True
        }
        
        return api_key
    
    def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Validate API key"""
        try:
            parts = api_key.split('_')
            if len(parts) < 3:
                return {'valid': False, 'error': 'Invalid API key format'}
            
            key_type, key_id = parts[0], parts[1]
            
            if key_id not in self.api_keys:
                return {'valid': False, 'error': 'API key not found'}
            
            key_data = self.api_keys[key_id]
            
            if not key_data.get('active', False):
                return {'valid': False, 'error': 'API key deactivated'}
            
            # Update usage stats
            key_data['usage_count'] += 1
            key_data['last_used'] = time.time()
            
            return {
                'valid': True,
                'key_type': key_type,
                'key_id': key_id,
                'usage_count': key_data['usage_count']
            }
            
        except Exception as e:
            return {'valid': False, 'error': f'API key validation failed: {e}'}
    
    def check_rate_limit(self, identifier: str, limit: int = 100, window: int = 3600) -> Dict[str, Any]:
        """Check rate limiting for identifier"""
        current_time = time.time()
        window_start = current_time - window
        
        # Clean old entries
        if identifier not in self.failed_attempts:
            self.failed_attempts[identifier] = []
        
        attempts = self.failed_attempts[identifier]
        self.failed_attempts[identifier] = [
            attempt for attempt in attempts if attempt > window_start
        ]
        
        current_attempts = len(self.failed_attempts[identifier])
        
        if current_attempts >= limit:
            return {
                'allowed': False,
                'current_attempts': current_attempts,
                'limit': limit,
                'reset_time': window_start + window
            }
        
        return {
            'allowed': True,
            'current_attempts': current_attempts,
            'limit': limit,
            'remaining': limit - current_attempts
        }
    
    def record_failed_attempt(self, identifier: str):
        """Record failed authentication attempt"""
        if identifier not in self.failed_attempts:
            self.failed_attempts[identifier] = []
        
        self.failed_attempts[identifier].append(time.time())
        
        self._log_security_event("auth", "failed_attempt", {
            'identifier': identifier,
            'timestamp': time.time()
        })
    
    def _log_security_event(self, category: str, event_type: str, details: Dict[str, Any]):
        """Log security event"""
        event = {
            'timestamp': time.time(),
            'category': category,
            'event_type': event_type,
            'details': details,
            'event_id': secrets.token_hex(8)
        }
        
        self.security_events.append(event)
        
        # Keep only recent events
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security system status"""
        active_tokens = len([t for t in self.auth_tokens.values() 
                           if t['expires_at'] > time.time()])
        
        recent_events = len([e for e in self.security_events 
                           if e['timestamp'] > time.time() - 3600])
        
        return {
            'encryption_enabled': self.encryption_enabled,
            'active_tokens': active_tokens,
            'total_tokens_issued': len(self.auth_tokens),
            'api_keys_active': len([k for k in self.api_keys.values() if k['active']]),
            'failed_attempts_tracked': len(self.failed_attempts),
            'security_events_last_hour': recent_events,
            'total_security_events': len(self.security_events),
            'master_api_key_exists': hasattr(self, 'master_api_key')
        }
    
    def get_security_events(self, limit: int = 100, category: str = None) -> List[Dict]:
        """Get recent security events"""
        events = self.security_events
        
        if category:
            events = [e for e in events if e['category'] == category]
        
        # Return most recent events
        return sorted(events, key=lambda x: x['timestamp'], reverse=True)[:limit]
    
    def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens"""
        current_time = time.time()
        expired_tokens = []
        
        for token_id, token_data in self.auth_tokens.items():
            if token_data['expires_at'] <= current_time:
                expired_tokens.append(token_id)
        
        for token_id in expired_tokens:
            del self.auth_tokens[token_id]
        
        if expired_tokens:
            self._log_security_event("maintenance", "expired_tokens_cleaned", {
                'tokens_cleaned': len(expired_tokens)
            })
        
        return len(expired_tokens)
    
    def rotate_encryption_key(self) -> bool:
        """Rotate encryption key"""
        try:
            old_key = self.encryption_key
            
            # Generate new key
            key_data = f"{platform.node()}-{uuid.getnode()}-security-{time.time()}"
            self.encryption_key = hashlib.sha256(key_data.encode()).digest()
            
            self._log_security_event("security", "encryption_key_rotated", {
                'rotation_time': time.time()
            })
            
            print("🔐 Encryption key rotated successfully")
            return True
            
        except Exception as e:
            self._log_security_event("security", "key_rotation_failed", {
                'error': str(e)
            })
            return False
    
    def export_security_audit(self, filepath: str) -> bool:
        """Export security audit log"""
        try:
            audit_data = {
                'security_status': self.get_security_status(),
                'security_events': self.get_security_events(1000),
                'failed_attempts': {
                    identifier: len(attempts) 
                    for identifier, attempts in self.failed_attempts.items()
                },
                'api_keys': {
                    key_id: {**data, 'key_id': key_id} 
                    for key_id, data in self.api_keys.items()
                },
                'export_timestamp': time.time()
            }
            
            with open(filepath, 'w') as f:
                json.dump(audit_data, f, indent=2, default=str)
            
            self._log_security_event("audit", "security_audit_exported", {
                'filepath': filepath
            })
            
            print(f"🔍 Security audit exported to {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to export security audit: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get security manager status"""
        return {
            'security_initialized': True,
            'encryption_enabled': self.encryption_enabled,
            'active_tokens': len([t for t in self.auth_tokens.values() 
                                if t['expires_at'] > time.time()]),
            'api_keys_managed': len(self.api_keys),
            'security_events_count': len(self.security_events),
            'failed_attempts_monitored': len(self.failed_attempts),
            'token_expiry_seconds': self.token_expiry,
            'max_login_attempts': self.max_login_attempts
        }
    
    def close(self):
        """Close security manager and cleanup"""
        try:
            # Clear sensitive data
            self.auth_tokens.clear()
            self.api_keys.clear()
            self.encryption_key = None
            
            self._log_security_event("system", "security_manager_closed", {})
            print("🔒 Security manager closed")
            
        except Exception as e:
            print(f"⚠️ Security manager close warning: {e}")
