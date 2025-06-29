"""Simple adaptive routing placeholder."""

from collections import defaultdict, deque
from typing import List

from painet_common.protocol.messages import MessageType, RouteInfo


class CSPAdaptiveRouting:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.history = defaultdict(lambda: deque(maxlen=10))

    def find_optimal_route(self, target: str, msg_type: MessageType, peers: List[str]) -> RouteInfo:
        if not peers:
            return RouteInfo(route=[], confidence=0.0, optimization_reason="no peers")
        peer = peers[0]
        return RouteInfo(route=[self.node_id, peer, target], confidence=1.0, optimization_reason="default")

    def record_route_performance(self, peer_id: str, latency_ms: float, bandwidth_mbps: float, success: bool):
        self.history[peer_id].append(latency_ms)
