import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch

from ultimate_agent.network.p2p import (
    QuantumEncryptionProtocol,
    CSPAdaptiveRouting, 
    CSPFaultTolerance,
    QuantumEnhancedP2PManager
)

class TestQuantumCrypto:
    """Test quantum crypto implementation"""
    
    @pytest.mark.asyncio
    async def test_encryption_decryption_roundtrip(self):
        """Test encryption/decryption works correctly"""
        alice = QuantumEncryptionProtocol("alice")
        bob = QuantumEncryptionProtocol("bob")
        
        # Share keys (simplified)
        test_data = b"Hello quantum world!"
        
        # Encrypt with Alice
        encrypted = await alice.quantum_encrypt(test_data, "bob")
        assert encrypted["encrypted"] is True
        assert "nonce" in encrypted
        assert "ciphertext" in encrypted
        
        # Set up Bob's key store (in real impl, this would be via key exchange)
        alice_key = await alice._get_or_create_key("bob")
        bob.key_store[alice_key.key_id] = alice_key
        
        # Decrypt with Bob
        decrypted = await bob.quantum_decrypt(encrypted, "alice")
        assert decrypted == test_data
    
    @pytest.mark.asyncio
    async def test_replay_protection(self):
        """Test replay attack protection"""
        alice = QuantumEncryptionProtocol("alice")
        bob = QuantumEncryptionProtocol("bob")
        
        test_data = b"Test message"
        
        # First encryption
        encrypted1 = await alice.quantum_encrypt(test_data, "bob")
        
        # Share key
        alice_key = await alice._get_or_create_key("bob")
        bob.key_store[alice_key.key_id] = alice_key
        
        # First decryption should work
        decrypted1 = await bob.quantum_decrypt(encrypted1, "alice")
        assert decrypted1 == test_data
        
        # Replay same message should fail
        decrypted2 = await bob.quantum_decrypt(encrypted1, "alice")
        assert decrypted2 is None

class TestAdaptiveRouting:
    """Test adaptive routing implementation"""
    
    def test_route_scoring(self):
        """Test route scoring algorithm"""
        router = CSPAdaptiveRouting("node1")
        
        # Add some metrics
        router.record_route_performance("peer1", 50.0, 100.0, True)
        router.record_route_performance("peer2", 200.0, 50.0, True)
        
        # Test routing decision
        route = router.find_optimal_route("target", "test", ["peer1", "peer2"])
        
        assert route.route == ["node1", "peer1", "target"]  # Should prefer lower latency
        assert route.confidence > 0
    
    def test_no_peers_available(self):
        """Test routing with no peers"""
        router = CSPAdaptiveRouting("node1")
        
        route = router.find_optimal_route("target", "test", [])
        
        assert route.route == []
        assert route.confidence == 0.0
        assert "no_peers" in route.optimization_reason

class TestFaultTolerance:
    """Test fault tolerance implementation"""
    
    @pytest.mark.asyncio
    async def test_successful_operation(self):
        """Test successful operation execution"""
        ft = CSPFaultTolerance("node1")
        
        async def success_operation():
            return "success"
        
        result = await ft.execute_with_fault_tolerance(
            success_operation, "test_op", "peer1"
        )
        
        assert result["success"] is True
        assert result["result"] == "success"
        assert result["attempts"] == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry mechanism"""
        ft = CSPFaultTolerance("node1")
        
        call_count = 0
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Simulated failure")
            return "success_after_retries"
        
        result = await ft.execute_with_fault_tolerance(
            failing_operation, "test_op", "peer1", max_retries=3
        )
        
        assert result["success"] is True
        assert result["attempts"] == 3
        assert call_count == 3
    
    @pytest.mark.asyncio 
    async def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        ft = CSPFaultTolerance("node1")
        ft.config.failure_threshold = 2
        
        async def always_fail():
            raise ValueError("Always fails")
        
        # First few failures should be attempted
        for _ in range(3):
            result = await ft.execute_with_fault_tolerance(
                always_fail, "test_op", "peer1", max_retries=0
            )
            assert result["success"] is False
        
        # Circuit should now be open
        result = await ft.execute_with_fault_tolerance(
            always_fail, "test_op", "peer1", max_retries=0
        )
        assert result["error"] == "circuit_breaker_open"

class TestQuantumP2PManager:
    """Test quantum P2P manager"""
    
    @pytest.mark.asyncio
    async def test_network_startup_shutdown(self):
        """Test network lifecycle"""
        manager = QuantumEnhancedP2PManager("test_node")
        
        # Start network
        success = await manager.start_network()
        assert success is True
        assert manager.running is True
        assert manager.bind_port > 0
        
        # Stop network
        await manager.stop_network()
        assert manager.running is False
    
    @pytest.mark.asyncio
    async def test_message_encryption_flow(self):
        """Test end-to-end message flow"""
        manager = QuantumEnhancedP2PManager("test_node")
        
        # Mock the actual network send
        with patch.object(manager, '_send_to_peer', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            # Mock peer discovery
            with patch.object(manager, '_discover_and_connect_peer', new_callable=AsyncMock) as mock_discover:
                mock_discover.return_value = True
                
                # Send message
                result = await manager.send_quantum_encrypted_message(
                    "target_peer",
                    {"test": "data"}
                )
                
                assert result["success"] is True
                mock_send.assert_called_once()
    
    def test_metrics_collection(self):
        """Test metrics collection"""
        manager = QuantumEnhancedP2PManager("test_node")
        
        metrics = manager.get_metrics()
        
        assert "node_id" in metrics
        assert "running" in metrics
        assert "connected_peers" in metrics
        assert metrics["node_id"] == "test_node"
