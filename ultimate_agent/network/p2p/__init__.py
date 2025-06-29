"""
P2P networking module for distributed AI inference
Fixed version with proper implementations
"""

# Import order fixed to avoid circular imports
from .quantum_crypto import QuantumEncryptionProtocol
from .adaptive_routing import CSPAdaptiveRouting, RouteInfo
from .fault_tolerance import CSPFaultTolerance, CircuitState
from .quantum_enhanced_p2p import QuantumEnhancedP2PManager, P2PMessage, MessageType

__all__ = [
    'QuantumEncryptionProtocol',
    'CSPAdaptiveRouting',
    'CSPFaultTolerance', 
    'QuantumEnhancedP2PManager',
    'P2PMessage',
    'MessageType',
    'RouteInfo',
    'CircuitState'
]

__version__ = "1.0.0"
__author__ = "Ultimate Agent Team"
