import asyncio
import time
import random
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    timeout_seconds: float = 60.0
    half_open_max_calls: int = 3
    success_threshold: int = 2

class CSPFaultTolerance:
    """Production fault tolerance with circuit breaker and exponential backoff"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.last_failure_times: Dict[str, float] = {}
        self.circuit_states: Dict[str, CircuitState] = defaultdict(lambda: CircuitState.CLOSED)
        self.half_open_calls: Dict[str, int] = defaultdict(int)
        self.success_counts: Dict[str, int] = defaultdict(int)
        self.config = CircuitBreakerConfig()
        
    async def execute_with_fault_tolerance(
        self,
        operation_coro: Callable[..., Awaitable[Any]],
        operation_type: str,
        peer_id: str,
        *args,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute operation with comprehensive fault tolerance"""
        
        circuit_key = f"{peer_id}:{operation_type}"
        
        # Check circuit breaker
        if not self._can_execute(circuit_key):
            return {
                "success": False,
                "error": "circuit_breaker_open",
                "retry_after": self._get_retry_delay(circuit_key)
            }
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    operation_coro(*args, **kwargs),
                    timeout=timeout_seconds
                )
                
                # Success - update circuit breaker
                self._record_success(circuit_key)
                
                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt + 1,
                    "peer_id": peer_id
                }
                
            except asyncio.TimeoutError:
                last_exception = "timeout"
                logger.warning(f"Timeout on {operation_type} to {peer_id} (attempt {attempt + 1})")
                
            except asyncio.CancelledError:
                # Don't retry cancellation
                self._record_failure(circuit_key)
                return {
                    "success": False,
                    "error": "cancelled",
                    "attempts": attempt + 1
                }
                
            except Exception as e:
                last_exception = str(e)
                logger.warning(f"Error on {operation_type} to {peer_id}: {e} (attempt {attempt + 1})")
            
            # Record failure and calculate backoff
            self._record_failure(circuit_key)
            
            # Don't sleep after last attempt
            if attempt < max_retries:
                backoff_delay = self._calculate_backoff_delay(attempt, peer_id)
                await asyncio.sleep(backoff_delay)
        
        return {
            "success": False,
            "error": last_exception or "max_retries_exceeded",
            "attempts": max_retries + 1,
            "peer_id": peer_id,
            "retry_after": self._get_retry_delay(circuit_key)
        }
    
    def _can_execute(self, circuit_key: str) -> bool:
        """Check if operation can execute based on circuit breaker state"""
        state = self.circuit_states[circuit_key]
        
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            # Check if timeout has passed
            last_failure = self.last_failure_times.get(circuit_key, 0)
            if time.time() - last_failure > self.config.timeout_seconds:
                self.circuit_states[circuit_key] = CircuitState.HALF_OPEN
                self.half_open_calls[circuit_key] = 0
                self.success_counts[circuit_key] = 0
                return True
            return False
        elif state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            return self.half_open_calls[circuit_key] < self.config.half_open_max_calls
        
        return False
    
    def _record_success(self, circuit_key: str):
        """Record successful operation"""
        state = self.circuit_states[circuit_key]
        
        if state == CircuitState.HALF_OPEN:
            self.success_counts[circuit_key] += 1
            if self.success_counts[circuit_key] >= self.config.success_threshold:
                # Circuit back to closed
                self.circuit_states[circuit_key] = CircuitState.CLOSED
                self.failure_counts[circuit_key] = 0
                logger.info(f"Circuit breaker closed for {circuit_key}")
        elif state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_counts[circuit_key] = 0
    
    def _record_failure(self, circuit_key: str):
        """Record failed operation"""
        self.failure_counts[circuit_key] += 1
        self.last_failure_times[circuit_key] = time.time()
        
        state = self.circuit_states[circuit_key]
        
        if state == CircuitState.CLOSED:
            if self.failure_counts[circuit_key] >= self.config.failure_threshold:
                self.circuit_states[circuit_key] = CircuitState.OPEN
                logger.warning(f"Circuit breaker opened for {circuit_key}")
        elif state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self.circuit_states[circuit_key] = CircuitState.OPEN
            logger.warning(f"Circuit breaker back to open for {circuit_key}")
    
    def _calculate_backoff_delay(self, attempt: int, peer_id: str) -> float:
        """Calculate exponential backoff with jitter"""
        base_delay = min(2 ** attempt, 30)  # Max 30 seconds
        jitter = random.uniform(0.5, 1.5)  # ±50% jitter
        
        # Add peer-specific factor to avoid thundering herd
        peer_factor = 1 + (hash(peer_id) % 100) / 1000  # 0-10% variation
        
        return base_delay * jitter * peer_factor
    
    def _get_retry_delay(self, circuit_key: str) -> float:
        """Get recommended retry delay"""
        state = self.circuit_states[circuit_key]
        
        if state == CircuitState.OPEN:
            last_failure = self.last_failure_times.get(circuit_key, 0)
            return max(0, self.config.timeout_seconds - (time.time() - last_failure))
        
        return 0.0
