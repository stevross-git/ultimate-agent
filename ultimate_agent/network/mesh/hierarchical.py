"""Simplified hierarchical mesh network with bandwidth optimization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class MeshNode:
    node_id: str
    cluster_id: str
    bandwidth_mbps: float
    is_leader: bool = False


@dataclass
class MeshCluster:
    cluster_id: str
    nodes: Dict[str, MeshNode] = field(default_factory=dict)
    leader: MeshNode | None = None

    def add_node(self, node: MeshNode) -> None:
        self.nodes[node.node_id] = node
        if node.is_leader or self.leader is None:
            self.leader = node


class HierarchicalMeshNetwork:
    """Coordinate nodes in a hierarchical mesh."""

    def __init__(self) -> None:
        self.nodes: Dict[str, MeshNode] = {}
        self.clusters: Dict[str, MeshCluster] = {}

    def add_node(self, node_id: str, cluster_id: str,
                 bandwidth_mbps: float = 100.0, *, is_leader: bool = False) -> None:
        cluster = self.clusters.setdefault(cluster_id, MeshCluster(cluster_id))
        node = MeshNode(node_id, cluster_id, bandwidth_mbps, is_leader=is_leader)
        cluster.add_node(node)
        if is_leader:
            cluster.leader = node
        self.nodes[node_id] = node

    def rebalance_leaders(self) -> None:
        """Choose the highest-bandwidth node as leader in each cluster."""
        for cluster in self.clusters.values():
            best = max(cluster.nodes.values(), key=lambda n: n.bandwidth_mbps)
            cluster.leader = best
            best.is_leader = True

    def route_path(self, src_id: str, dst_id: str) -> List[str]:
        src = self.nodes[src_id]
        dst = self.nodes[dst_id]
        if src.cluster_id == dst.cluster_id:
            return [src_id, dst_id]
        src_leader = self.clusters[src.cluster_id].leader.node_id
        dst_leader = self.clusters[dst.cluster_id].leader.node_id
        path = [src_id]
        if src_id != src_leader:
            path.append(src_leader)
        if src_leader != dst_leader:
            path.append(dst_leader)
        if dst_id != dst_leader:
            path.append(dst_id)
        return path

    def estimate_transfer_time(self, src_id: str, dst_id: str,
                               size_mb: float, optimize: bool = False) -> float:
        path = self.route_path(src_id, dst_id)
        if optimize and size_mb >= 100:
            size_mb *= 0.5  # pretend compression for large transfers
        total = 0.0
        for a, b in zip(path, path[1:]):
            bw = min(self.nodes[a].bandwidth_mbps,
                     self.nodes[b].bandwidth_mbps)
            total += size_mb / (bw or 1.0)
        return total

    def broadcast(self, src_id: str, size_mb: float, optimize: bool = False) -> float:
        """Broadcast a payload to all other nodes, returning total estimated time."""
        total = 0.0
        for dst_id in self.nodes:
            if dst_id == src_id:
                continue
            total += self.estimate_transfer_time(src_id, dst_id, size_mb, optimize=optimize)
        return total
