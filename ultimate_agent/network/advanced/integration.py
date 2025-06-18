"""Integration helpers for AdvancedNetworkManager."""
from __future__ import annotations

from typing import Any, Dict

from .network_manager import AdvancedNetworkManager


def create_network_manager(config, node_id: str) -> AdvancedNetworkManager:
    """Factory used by agents to create the advanced manager."""
    listen_port = config.getint('NETWORK', 'listen_port', fallback=0)
    secret = (config.get('NETWORK', 'secret', fallback='').encode() or None)
    manager = AdvancedNetworkManager(node_id, listen_port=listen_port, secret=secret)
    return manager


__all__ = ["create_network_manager", "AdvancedNetworkManager"]
