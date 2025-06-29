import asyncio
import time
import math
from collections import defaultdict, deque
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class RouteMetrics:
    """Route performance metrics"""
    latency_ms: float
    bandwidth_mbps: float
    success_rate: float
    last_updated: float
    
@dataclass 
class RouteInfo:
    """Route information with confidence scoring"""
    route: List[str]
    confidence: float
    estimated_latency: float
    optimization_reason: str
    
class CSPAdaptiveRouting:
    """Production adaptive routing with dynamic optimization"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.peer_metrics: Dict[str, RouteMetrics] = {}
        self.route_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.peer_topology: Dict[str, List[str]] = {}
        
    def find_optimal_route(self, target: str, msg_type: str, peers: List[str]) -> RouteInfo:
        """Find optimal route using adaptive scoring"""
        if not peers:
            return RouteInfo(
                route=[],
                confidence=0.0,
                estimated_latency=float('inf'),
                optimization_reason="no_peers_available"
            )
            
        if target in peers:
            # Direct route available
            metrics = self.peer_metrics.get(target)
            if metrics:
                confidence = self._calculate_confidence(metrics)
                return RouteInfo(
                    route=[self.node_id, target],
                    confidence=confidence,
                    estimated_latency=metrics.latency_ms,
                    optimization_reason="direct_route_optimal"
                )
        
        # Find best multi-hop route
        best_route = self._find_best_multihop_route(target, peers)
        
        return best_route
    
    def _find_best_multihop_route(self, target: str, peers: List[str]) -> RouteInfo:
        """Find best multi-hop route using Dijkstra-like algorithm"""
        # Simplified routing - in production, use full graph traversal
        scored_peers = []
        
        for peer in peers:
            score = self._calculate_peer_score(peer)
            estimated_latency = self._estimate_latency(peer, target)
            
            scored_peers.append((score, peer, estimated_latency))
        
        if not scored_peers:
            return RouteInfo(
                route=[],
                confidence=0.0,
                estimated_latency=float('inf'),
                optimization_reason="no_viable_routes"
            )
        
        # Sort by score (higher is better)
        scored_peers.sort(key=lambda x: x[0], reverse=True)
        best_score, best_peer, latency = scored_peers[0]
        
        confidence = min(best_score / 100.0, 1.0)  # Normalize to 0-1
        
        return RouteInfo(
            route=[self.node_id, best_peer, target],
            confidence=confidence,
            estimated_latency=latency,
            optimization_reason=f"best_peer_score_{best_score:.2f}"
        )
    
    def _calculate_peer_score(self, peer_id: str) -> float:
        """Calculate peer score based on historical performance"""
        metrics = self.peer_metrics.get(peer_id)
        if not metrics:
            return 50.0  # Default score for unknown peers
        
        # Age factor (prefer recent data)
        age_seconds = time.time() - metrics.last_updated
        age_factor = math.exp(-age_seconds / 300)  # 5-minute half-life
        
        # Performance score (0-100)
        latency_score = max(0, 100 - metrics.latency_ms / 10)  # Penalty for high latency
        bandwidth_score = min(100, metrics.bandwidth_mbps * 2)  # Bonus for high bandwidth
        reliability_score = metrics.success_rate * 100
        
        # Weighted combination
        performance_score = (
            latency_score * 0.4 +
            bandwidth_score * 0.3 +
            reliability_score * 0.3
        )
        
        return performance_score * age_factor
    
    def _estimate_latency(self, peer: str, target: str) -> float:
        """Estimate latency for route through peer"""
        peer_metrics = self.peer_metrics.get(peer)
        peer_latency = peer_metrics.latency_ms if peer_metrics else 100.0
        
        # Estimate hop latency (simplified)
        target_latency = 50.0  # Default estimate
        
        return peer_latency + target_latency
    
    def _calculate_confidence(self, metrics: RouteMetrics) -> float:
        """Calculate confidence based on metrics quality"""
        age_seconds = time.time() - metrics.last_updated
        age_factor = math.exp(-age_seconds / 600)  # 10-minute half-life
        
        performance_factor = (
            (100 - min(metrics.latency_ms, 100)) / 100 * 0.4 +
            min(metrics.bandwidth_mbps / 100, 1.0) * 0.3 +
            metrics.success_rate * 0.3
        )
        
        return min(age_factor * performance_factor, 1.0)
    
    def record_route_performance(self, peer_id: str, latency_ms: float, 
                                bandwidth_mbps: float, success: bool):
        """Record performance metrics for route optimization"""
        # Update running averages
        current_metrics = self.peer_metrics.get(peer_id)
        
        if current_metrics:
            # Exponential moving average
            alpha = 0.3  # Learning rate
            new_latency = alpha * latency_ms + (1 - alpha) * current_metrics.latency_ms
            new_bandwidth = alpha * bandwidth_mbps + (1 - alpha) * current_metrics.bandwidth_mbps
            
            # Update success rate
            history = self.route_history[peer_id]
            history.append(1 if success else 0)
            new_success_rate = sum(history) / len(history)
            
            self.peer_metrics[peer_id] = RouteMetrics(
                latency_ms=new_latency,
                bandwidth_mbps=new_bandwidth,
                success_rate=new_success_rate,
                last_updated=time.time()
            )
        else:
            # First measurement
            self.route_history[peer_id].append(1 if success else 0)
            self.peer_metrics[peer_id] = RouteMetrics(
                latency_ms=latency_ms,
                bandwidth_mbps=bandwidth_mbps,
                success_rate=1.0 if success else 0.0,
                last_updated=time.time()
            )
        
        logger.debug(f"Updated metrics for {peer_id}: {self.peer_metrics[peer_id]}")
