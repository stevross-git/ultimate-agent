"""Minimal fault tolerance utilities."""

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict


class CSPFaultTolerance:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.failures = defaultdict(int)

    async def execute_with_fault_tolerance(
        self,
        operation_coro: Callable[..., Awaitable[Any]],
        operation_type: str,
        peer_id: str,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            result = await operation_coro(*args, **kwargs)
            self.failures[peer_id] = 0
            return {"success": True, "result": result}
        except Exception as e:
            self.failures[peer_id] += 1
            return {"success": False, "error": str(e)}
