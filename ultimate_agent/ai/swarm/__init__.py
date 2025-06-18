"""Basic swarm intelligence coordination utilities."""

from typing import Any, Callable, Dict, List, Tuple, Optional


class SwarmNode:
    """Simple representation of a node participating in the swarm."""

    def __init__(self, node_id: str, weight: float = 1.0, task_fn: Optional[Callable[[Any], Any]] = None):
        self.node_id = node_id
        self.weight = float(weight)
        self.task_fn = task_fn

    def execute(self, data: Any) -> Any:
        if self.task_fn:
            return self.task_fn(data)
        return data


class SwarmCoordinator:
    """Coordinates tasks among swarm nodes and aggregates their results."""

    def __init__(self):
        self.nodes: Dict[str, SwarmNode] = {}

    def register_node(self, node_id: str, weight: float = 1.0, task_fn: Optional[Callable[[Any], Any]] = None) -> None:
        """Register a new node in the swarm."""
        self.nodes[node_id] = SwarmNode(node_id, weight, task_fn)

    def unregister_node(self, node_id: str) -> None:
        """Remove node from the swarm if present."""
        self.nodes.pop(node_id, None)

    def coordinate_task(self, data: Any) -> Dict[str, Any]:
        """Send data to all nodes and aggregate their results."""
        if not self.nodes:
            return {"success": False, "error": "no_nodes"}

        results: List[Tuple[float, Any]] = []
        for node in self.nodes.values():
            try:
                result = node.execute(data)
                results.append((node.weight, result))
            except Exception:
                results.append((0.0, None))

        aggregated = self._aggregate_results(results)
        return {"success": True, "participants": len(self.nodes), "result": aggregated}

    def _aggregate_results(self, results: List[Tuple[float, Any]]) -> Any:
        """Aggregate results using weighted majority or average."""
        valid = [(w, r) for w, r in results if r is not None]
        if not valid:
            return None

        if all(isinstance(r, (int, float)) for _, r in valid):
            unique_vals = set(r for _, r in valid)
            if unique_vals <= {0, 1} and len(unique_vals) <= 2:
                # Treat as classification, return weighted majority
                weight_zero = sum(w for w, r in valid if r == 0)
                weight_one = sum(w for w, r in valid if r == 1)
                return 1 if weight_one >= weight_zero else 0

            total_w = sum(w for w, _ in valid)
            return sum(w * r for w, r in valid) / (total_w or 1.0)

        votes: Dict[str, float] = {}
        for weight, res in valid:
            key = str(res)
            votes[key] = votes.get(key, 0.0) + weight

        best = max(votes.items(), key=lambda x: x[1])
        # Try to return original object if possible
        for _, res in valid:
            if str(res) == best[0]:
                return res
        return best[0]

__all__ = ["SwarmNode", "SwarmCoordinator"]
