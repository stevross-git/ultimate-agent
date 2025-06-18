import time
import threading
from typing import List, Dict, Optional

try:
    import requests
except Exception:  # pragma: no cover - optional dependency
    requests = None


class DiscoveryClient:
    """Service discovery for agents and nodes."""


    def __init__(
        self,
        node_service: str = "https://srvnodes.peoplesainetwork.com",
        manager_service: str = "http://mannodes.peoplesainetwork.com",
    ):

        self.node_service = node_service.rstrip('/')
        self.manager_service = manager_service.rstrip('/')
        self.nodes_cache: List[Dict[str, str]] = []
        self.manager_url: Optional[str] = None
        self.last_refresh: float = 0
        self.lock = threading.Lock()

    def refresh_nodes(self) -> List[Dict[str, str]]:
        """Fetch node list from the discovery service."""
        if requests is None:
            print("⚠️ 'requests' not available - using cached nodes")
            return self.nodes_cache

        try:
            resp = requests.get(f"{self.node_service}/api/nodes", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            nodes = data.get("nodes", [])
            with self.lock:
                self.nodes_cache = nodes
                self.last_refresh = time.time()
            return nodes
        except Exception as exc:
            print(f"⚠️ Node discovery failed: {exc}")
            return self.nodes_cache

    def refresh_manager(self) -> Optional[str]:
        """Fetch manager URL from the manager registry."""
        if requests is None:
            print("⚠️ 'requests' not available - manager discovery disabled")
            return self.manager_url

        try:
            resp = requests.get(f"{self.manager_service}/api/manager", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            manager_url = data.get("manager_url")
            if manager_url:
                with self.lock:
                    self.manager_url = manager_url.rstrip('/')
                    self.last_refresh = time.time()
            return self.manager_url
        except Exception as exc:
            print(f"⚠️ Manager discovery failed: {exc}")
            return self.manager_url

    def get_best_node(self, test_fn=None) -> Optional[Dict[str, str]]:
        """Return the best available node using optional latency test."""
        if not self.nodes_cache:
            self.refresh_nodes()
        best = None
        best_latency = float("inf")
        for node in self.nodes_cache:
            url = node.get("url")
            if not url:
                continue
            latency = 0.0
            if test_fn:
                result = test_fn(url)
                if not result.get("success"):
                    continue
                latency = result.get("response_time_ms", 0.0)
            if best is None or latency < best_latency:
                best = node
                best_latency = latency
        return best

    def start_background_refresh(self, interval: int = 300) -> None:
        """Start background thread to refresh discovery data."""
        def _refresh_loop():
            while True:
                try:
                    self.refresh_nodes()
                    self.refresh_manager()
                    time.sleep(interval)
                except Exception:
                    time.sleep(interval)

        thread = threading.Thread(target=_refresh_loop, daemon=True)
        thread.start()
