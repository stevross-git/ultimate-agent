"""Bridge for integrating quantum P2P manager with the agent."""

from typing import Any, Dict

from .p2p.quantum_enhanced_p2p import QuantumEnhancedP2PManager


class QuantumP2PBridge:
    def __init__(self, agent: Any):
        self.agent = agent
        self.manager: QuantumEnhancedP2PManager | None = None

    async def start(self) -> bool:
        self.manager = QuantumEnhancedP2PManager("quantum-" + getattr(self.agent, "agent_id", "agent"))
        await self.manager.start_network()
        return True

    async def stop(self):
        if self.manager:
            await self.manager.stop_network()
            self.manager = None

    async def send_quantum_message(self, target_node: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.manager:
            return {"success": False, "error": "not running"}
        success = await self.manager.send_quantum_encrypted_message(target_node, message_data)
        return {"success": success}
