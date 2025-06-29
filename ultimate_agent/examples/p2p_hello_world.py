#!/usr/bin/env python3.11
"""Simple example showing two peers exchanging a message."""

import asyncio
import time

from ultimate_agent.network.p2p import QuantumEnhancedP2PManager, MessageType


async def main() -> None:
    # Create two local P2P managers
    alice = QuantumEnhancedP2PManager("alice", bind_port=0)
    bob = QuantumEnhancedP2PManager("bob", bind_port=0)

    await alice.start_network()
    await bob.start_network()

    # Prepare a message handler on Bob's side
    async def handle_message(message: dict, sender: str) -> None:
        print(f"Bob received from {sender}: {message['data']['text']}")

    bob.message_handlers[MessageType.INFERENCE_REQUEST] = handle_message

    # Manually connect peers over TCP
    reader_ab, writer_ab = await asyncio.open_connection("127.0.0.1", bob.bind_port)
    alice.connected_peers["bob"] = {
        "writer": writer_ab,
        "connected_at": time.time(),
        "last_seen": time.time(),
    }

    reader_ba, writer_ba = await asyncio.open_connection("127.0.0.1", alice.bind_port)
    bob.connected_peers["alice"] = {
        "writer": writer_ba,
        "connected_at": time.time(),
        "last_seen": time.time(),
    }

    await alice.send_quantum_encrypted_message("bob", {"text": "Hello world"})

    # Give Bob a moment to process
    await asyncio.sleep(0.2)

    await alice.stop_network()
    await bob.stop_network()


if __name__ == "__main__":
    asyncio.run(main())
