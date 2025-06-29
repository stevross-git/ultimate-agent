import asyncio
import logging
import time
from ultimate_agent.network.p2p import QuantumEnhancedP2PManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_quantum_p2p():
    """Working quantum P2P demonstration"""
    print("\U0001F680 Starting Quantum P2P Demo")
    print("=" * 50)
    
    # Create two P2P nodes
    alice = QuantumEnhancedP2PManager("alice", bind_port=0)
    bob = QuantumEnhancedP2PManager("bob", bind_port=0)
    
    try:
        # Start both networks
        print("\U0001F4E1 Starting P2P networks...")
        alice_started = await alice.start_network()
        bob_started = await bob.start_network()
        
        if not (alice_started and bob_started):
            print("\u274C Failed to start P2P networks")
            return
        
        print(f"\u2705 Alice started on port {alice.bind_port}")
        print(f"\u2705 Bob started on port {bob.bind_port}")
        
        # Wait for networks to stabilize
        await asyncio.sleep(1)
        
        # Test quantum encryption
        print("\n\U0001F512 Testing quantum encryption...")
        test_message = {"content": "Hello from Alice!", "timestamp": time.time()}
        
        result = await alice.send_quantum_encrypted_message("bob", test_message)
        
        if result["success"]:
            print("\u2705 Message sent successfully")
            print(f"   Attempts: {result.get('attempts', 1)}")
        else:
            print(f"\u274C Message failed: {result.get('error')}")
        
        # Test multiple messages
        print("\n\U0001F4E6 Testing multiple messages...")
        tasks = []
        for i in range(3):
            msg = {"batch_id": i, "data": f"Batch message {i}"}
            task = alice.send_quantum_encrypted_message("bob", msg)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        print(f"\u2705 {successful}/3 batch messages successful")
        
        # Show metrics
        print("\n\U0001F4CA Network Metrics:")
        alice_metrics = alice.get_metrics()
        bob_metrics = bob.get_metrics()
        
        print(f"Alice: {alice_metrics['messages_sent']} sent, "
              f"{alice_metrics['encryption_success_rate']:.1%} encryption success")
        print(f"Bob: {bob_metrics['messages_received']} received")
        
        # Test fault tolerance
        print("\n\U0001F6E1\uFE0F Testing fault tolerance...")
        
        # Simulate network issues
        with patch.object(alice, '_send_to_peer') as mock_send:
            mock_send.side_effect = [
                ConnectionError("Network down"),
                ConnectionError("Still down"),
                True  # Success on third try
            ]
            
            result = await alice.send_quantum_encrypted_message(
                "bob", 
                {"test": "fault_tolerance"},
                timeout=5.0
            )
            
            if result["success"]:
                print(f"\u2705 Fault tolerance worked (attempts: {result['attempts']})")
            else:
                print(f"\u274C Fault tolerance failed: {result['error']}")
        
        print("\n\U0001F389 Demo completed successfully!")
        
    except Exception as e:
        print(f"\u274C Demo failed: {e}")
        logger.exception("Demo error")
        
    finally:
        # Cleanup
        print("\n\U0001F9F9 Cleaning up...")
        await alice.stop_network()
        await bob.stop_network()
        print("\u2705 Cleanup complete")

def main():
    """Main entry point"""
    try:
        asyncio.run(demo_quantum_p2p())
    except KeyboardInterrupt:
        print("\n\u23F9\uFE0F Demo interrupted by user")
    except Exception as e:
        print(f"\u274C Demo failed: {e}")

if __name__ == "__main__":
    main()
