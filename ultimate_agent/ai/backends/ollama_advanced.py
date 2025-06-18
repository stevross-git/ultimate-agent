#!/usr/bin/env python3
"""
ultimate_agent/ai/backends/ollama_advanced.py
Advanced Ollama Integration for Distributed AI Network

Features:
- Multi-instance connection pooling
- Intelligent load balancing  
- Model lifecycle management
- Health monitoring & auto-recovery
- Streaming & batch processing
- Distributed coordination
- Performance optimization
- Comprehensive error handling
"""

import asyncio
import aiohttp
import time
import json
import hashlib
import random
from typing import Dict, Any, List, Optional, Union, AsyncGenerator, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
from pathlib import Path
import weakref
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️ ollama-python not available. Install with: pip install ollama")


class InstanceStatus(Enum):
    """Ollama instance status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"


class LoadBalanceStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RESPONSE_TIME = "response_time"
    MODEL_AFFINITY = "model_affinity"
    RESOURCE_AWARE = "resource_aware"


@dataclass
class OllamaInstance:
    """Represents an Ollama instance"""
    host: str
    port: int = 11434
    protocol: str = "http"
    weight: float = 1.0
    max_connections: int = 10
    timeout: float = 30.0
    
    # Runtime state
    status: InstanceStatus = field(default=InstanceStatus.UNKNOWN, init=False)
    active_connections: int = field(default=0, init=False)
    total_requests: int = field(default=0, init=False)
    failed_requests: int = field(default=0, init=False)
    avg_response_time: float = field(default=0.0, init=False)
    last_health_check: Optional[datetime] = field(default=None, init=False)
    available_models: List[str] = field(default_factory=list, init=False)
    gpu_memory_used: float = field(default=0.0, init=False)
    cpu_usage: float = field(default=0.0, init=False)
    
    @property
    def base_url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def instance_id(self) -> str:
        return f"{self.host}:{self.port}"
    
    @property
    def health_score(self) -> float:
        """Calculate health score (0-1)"""
        if self.status == InstanceStatus.HEALTHY:
            base_score = 1.0
        elif self.status == InstanceStatus.DEGRADED:
            base_score = 0.7
        elif self.status == InstanceStatus.UNHEALTHY:
            base_score = 0.3
        else:
            base_score = 0.0
        
        # Adjust for load
        load_factor = max(0.1, 1.0 - (self.active_connections / self.max_connections))
        
        # Adjust for success rate
        success_rate = 1.0
        if self.total_requests > 0:
            success_rate = 1.0 - (self.failed_requests / self.total_requests)
        
        return base_score * load_factor * success_rate


@dataclass
class InferenceRequest:
    """Represents an inference request"""
    model: str
    prompt: str
    options: Dict[str, Any] = field(default_factory=dict)
    stream: bool = False
    keep_alive: Optional[str] = None
    format: Optional[str] = None
    system: Optional[str] = None
    template: Optional[str] = None
    context: Optional[List[int]] = None
    raw: bool = False
    
    # Metadata
    request_id: str = field(default_factory=lambda: f"req_{int(time.time() * 1000)}")
    priority: int = 5  # 1-10, higher = more priority
    max_retries: int = 3
    timeout: float = 30.0
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_ollama_dict(self) -> Dict[str, Any]:
        """Convert to Ollama API format"""
        data = {
            "model": self.model,
            "prompt": self.prompt,
            "stream": self.stream
        }
        
        if self.options:
            data["options"] = self.options
        if self.keep_alive is not None:
            data["keep_alive"] = self.keep_alive
        if self.format:
            data["format"] = self.format
        if self.system:
            data["system"] = self.system
        if self.template:
            data["template"] = self.template
        if self.context:
            data["context"] = self.context
        if self.raw:
            data["raw"] = self.raw
            
        return data


@dataclass
class InferenceResponse:
    """Represents an inference response"""
    success: bool
    response: Optional[str] = None
    model: str = ""
    context: Optional[List[int]] = None
    done: bool = True
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None
    
    # Metadata
    instance_id: str = ""
    request_id: str = ""
    processing_time: float = 0.0
    error: Optional[str] = None
    retry_count: int = 0
    
    @property
    def tokens_per_second(self) -> float:
        """Calculate tokens per second"""
        if self.eval_count and self.eval_duration:
            return self.eval_count / (self.eval_duration / 1_000_000_000)
        return 0.0


class ConnectionPool:
    """Manages HTTP connections to Ollama instances"""
    
    def __init__(self, instance: OllamaInstance):
        self.instance = instance
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(instance.max_connections)
        self._lock = asyncio.Lock()
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            async with self._lock:
                if self.session is None or self.session.closed:
                    if self.session and not self.session.closed:
                        await self.session.close()

                    timeout = aiohttp.ClientTimeout(total=self.instance.timeout)
                    connector = aiohttp.TCPConnector(
                        limit=self.instance.max_connections,
                        ttl_dns_cache=300,
                        use_dns_cache=True,
                        enable_cleanup_closed=True
                    )
                    self.session = aiohttp.ClientSession(
                        timeout=timeout,
                        connector=connector
                    )
        return self.session
    
    async def request(self, method: str, endpoint: str, **kwargs) -> aiohttp.ClientResponse:
        """Make HTTP request with connection pooling"""
        async with self.semaphore:
            self.instance.active_connections += 1
            try:
                session = await self.get_session()
                url = f"{self.instance.base_url}{endpoint}"
                
                async with session.request(method, url, **kwargs) as response:
                    return response
            finally:
                self.instance.active_connections -= 1
    
    async def close(self):
        """Close connection pool"""
        if self.session and not self.session.closed:
            await self.session.close()


class ModelManager:
    """Manages model lifecycle across Ollama instances"""
    
    def __init__(self, advanced_ollama):
        self.advanced_ollama = advanced_ollama
        self.model_cache: Dict[str, Dict[str, Any]] = {}
        self.download_progress: Dict[str, float] = {}
        self.model_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        
    async def ensure_model_available(self, model: str, instance: OllamaInstance) -> bool:
        """Ensure model is available on instance"""
        async with self.model_locks[f"{instance.instance_id}:{model}"]:
            # Check if model is already available
            if model in instance.available_models:
                return True
            
            # Check if model exists
            if not await self._model_exists(model, instance):
                # Try to pull the model
                success = await self._pull_model(model, instance)
                if success:
                    instance.available_models.append(model)
                    await self._update_model_cache(model, instance)
                return success
            else:
                instance.available_models.append(model)
                return True
    
    async def _model_exists(self, model: str, instance: OllamaInstance) -> bool:
        """Check if model exists on instance"""
        try:
            pool = self.advanced_ollama._get_connection_pool(instance)
            
            async with pool.request("GET", "/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return model in models
                    
        except Exception as e:
            logging.error(f"Error checking model {model} on {instance.instance_id}: {e}")
        
        return False
    
    async def _pull_model(self, model: str, instance: OllamaInstance) -> bool:
        """Pull model to instance"""
        try:
            pool = self.advanced_ollama._get_connection_pool(instance)
            
            # Start model pull
            data = {"name": model}
            
            async with pool.request("POST", "/api/pull", json=data) as response:
                if response.status == 200:
                    # Stream progress updates
                    async for line in response.content:
                        if line:
                            try:
                                progress_data = json.loads(line.decode())
                                if "status" in progress_data:
                                    # Update progress tracking
                                    progress_key = f"{instance.instance_id}:{model}"
                                    if "completed" in progress_data and "total" in progress_data:
                                        progress = progress_data["completed"] / progress_data["total"] * 100
                                        self.download_progress[progress_key] = progress
                                        
                                    # Check if completed
                                    if progress_data.get("status") == "success":
                                        if progress_key in self.download_progress:
                                            del self.download_progress[progress_key]
                                        return True
                                        
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            logging.error(f"Error pulling model {model} to {instance.instance_id}: {e}")
        
        return False
    
    async def _update_model_cache(self, model: str, instance: OllamaInstance):
        """Update model cache with metadata"""
        try:
            pool = self.advanced_ollama._get_connection_pool(instance)
            
            # Get model info
            async with pool.request("POST", "/api/show", json={"name": model}) as response:
                if response.status == 200:
                    model_info = await response.json()
                    
                    cache_key = f"{instance.instance_id}:{model}"
                    self.model_cache[cache_key] = {
                        "model": model,
                        "instance_id": instance.instance_id,
                        "info": model_info,
                        "cached_at": datetime.now(),
                        "size_bytes": model_info.get("size", 0)
                    }
                    
        except Exception as e:
            logging.error(f"Error caching model info for {model}: {e}")
    
    def get_instances_with_model(self, model: str) -> List[OllamaInstance]:
        """Get instances that have the specified model"""
        instances = []
        for instance in self.advanced_ollama.instances:
            if model in instance.available_models:
                instances.append(instance)
        return instances
    
    def get_download_progress(self, model: str, instance_id: str) -> Optional[float]:
        """Get download progress for model on instance"""
        return self.download_progress.get(f"{instance_id}:{model}")


class LoadBalancer:
    """Intelligent load balancer for Ollama instances"""
    
    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.RESPONSE_TIME):
        self.strategy = strategy
        self.round_robin_index = 0
        self.response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
    def select_instance(self, instances: List[OllamaInstance], 
                       request: InferenceRequest) -> Optional[OllamaInstance]:
        """Select best instance based on strategy"""
        if not instances:
            return None
        
        # Filter healthy instances
        healthy_instances = [i for i in instances if i.status == InstanceStatus.HEALTHY]
        if not healthy_instances:
            # Fall back to degraded instances
            healthy_instances = [i for i in instances if i.status == InstanceStatus.DEGRADED]
        
        if not healthy_instances:
            return None
        
        if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            selected = self._weighted_round_robin_select(healthy_instances)
            if selected is not None:
                return selected
            return self._round_robin_select(healthy_instances)
        elif self.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(healthy_instances)
        elif self.strategy == LoadBalanceStrategy.RESPONSE_TIME:
            return self._response_time_select(healthy_instances)
        elif self.strategy == LoadBalanceStrategy.MODEL_AFFINITY:
            return self._model_affinity_select(healthy_instances, request.model)
        elif self.strategy == LoadBalanceStrategy.RESOURCE_AWARE:
            return self._resource_aware_select(healthy_instances)
        else:
            return healthy_instances[0]
    
    def _round_robin_select(self, instances: List[OllamaInstance]) -> OllamaInstance:
        """Round robin selection"""
        instance = instances[self.round_robin_index % len(instances)]
        self.round_robin_index += 1
        return instance

    def _weighted_round_robin_select(self, instances: List[OllamaInstance]) -> Optional[OllamaInstance]:
        """Weighted round robin based on instance health and capacity"""
        if not instances:
            return None

        weights = []
        for instance in instances:
            capacity_factor = 1.0 - (instance.active_connections / instance.max_connections)
            weight = instance.health_score * capacity_factor * instance.weight
            weights.append(weight)

        total_weight = sum(weights)
        if total_weight == 0:
            return instances[0]

        import random
        r = random.uniform(0, total_weight)
        for i, weight in enumerate(weights):
            r -= weight
            if r <= 0:
                return instances[i]

        return instances[-1]
    
    def _least_connections_select(self, instances: List[OllamaInstance]) -> OllamaInstance:
        """Select instance with least active connections"""
        return min(instances, key=lambda i: i.active_connections / i.max_connections)
    
    def _response_time_select(self, instances: List[OllamaInstance]) -> OllamaInstance:
        """Select instance with best response time"""
        def score(instance):
            # Combine response time and health score
            response_time_factor = 1.0 / max(0.001, instance.avg_response_time)
            return instance.health_score * response_time_factor
        
        return max(instances, key=score)
    
    def _model_affinity_select(self, instances: List[OllamaInstance], model: str) -> OllamaInstance:
        """Select instance with model affinity"""
        # Prefer instances that already have the model loaded
        model_instances = [i for i in instances if model in i.available_models]
        if model_instances:
            return self._response_time_select(model_instances)
        return self._response_time_select(instances)
    
    def _resource_aware_select(self, instances: List[OllamaInstance]) -> OllamaInstance:
        """Select instance based on resource utilization"""
        def resource_score(instance):
            # Lower CPU and GPU usage = better score
            cpu_score = 1.0 - (instance.cpu_usage / 100.0)
            gpu_score = 1.0 - (instance.gpu_memory_used / 100.0)
            load_score = 1.0 - (instance.active_connections / instance.max_connections)
            
            return (cpu_score + gpu_score + load_score) / 3.0 * instance.health_score
        
        return max(instances, key=resource_score)
    
    def record_response_time(self, instance_id: str, response_time: float):
        """Record response time for instance"""
        self.response_times[instance_id].append(response_time)


class HealthMonitor:
    """Monitors health of Ollama instances"""
    
    def __init__(self, advanced_ollama):
        self.advanced_ollama = advanced_ollama
        self.check_interval = 30.0  # seconds
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start health monitoring"""
        if self.running:
            return
            
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logging.info("Health monitor started")
    
    async def stop(self):
        """Stop health monitoring"""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logging.info("Health monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self._check_all_instances()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)
    
    async def _check_all_instances(self):
        """Check health of all instances"""
        tasks = []
        for instance in self.advanced_ollama.instances:
            task = asyncio.create_task(self._check_instance_health(instance))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_instance_health(self, instance: OllamaInstance):
        """Check health of single instance"""
        start_time = time.time()
        
        try:
            pool = self.advanced_ollama._get_connection_pool(instance)
            
            # Simple health check - get version
            async with pool.request("GET", "/api/version", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    response_time = time.time() - start_time
                    
                    # Update response time
                    instance.avg_response_time = (instance.avg_response_time * 0.9 + response_time * 0.1)
                    
                    # Update status based on response time
                    if response_time < 1.0:
                        instance.status = InstanceStatus.HEALTHY
                    elif response_time < 3.0:
                        instance.status = InstanceStatus.DEGRADED
                    else:
                        instance.status = InstanceStatus.UNHEALTHY
                        
                    instance.last_health_check = datetime.now()
                    
                    # Update available models
                    await self._update_available_models(instance)
                    
                else:
                    instance.status = InstanceStatus.UNHEALTHY
                    
        except Exception as e:
            logging.warning(f"Health check failed for {instance.instance_id}: {e}")
            instance.status = InstanceStatus.UNHEALTHY
    
    async def _update_available_models(self, instance: OllamaInstance):
        """Update list of available models"""
        try:
            pool = self.advanced_ollama._get_connection_pool(instance)
            
            async with pool.request("GET", "/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    instance.available_models = models
                    
        except Exception as e:
            logging.warning(f"Failed to update models for {instance.instance_id}: {e}")


class AdvancedOllamaManager:
    """Advanced Ollama integration with distributed capabilities"""
    
    def __init__(self, config_manager=None):
        self.config = config_manager
        self.instances: List[OllamaInstance] = []
        self.connection_pools: Dict[str, ConnectionPool] = {}
        
        # Components
        self.model_manager = ModelManager(self)
        self.load_balancer = LoadBalancer(LoadBalanceStrategy.RESPONSE_TIME)
        self.health_monitor = HealthMonitor(self)
        
        # Configuration
        self.default_timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 1.0
        self.enable_streaming = True
        self.enable_batching = True
        self.batch_size = 10
        self.batch_timeout = 1.0
        
        # State
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self.batch_processor_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_response_time = 0.0
        
        # Thread pool for CPU-intensive tasks
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Initialize from config
        self._load_configuration()
        
        logging.info("Advanced Ollama Manager initialized")
    
    def _load_configuration(self):
        """Load configuration from config manager"""
        if not self.config:
            return
        
        # Load default instances
        instances_config = self.config.get('OLLAMA', 'instances', fallback='localhost:11434')
        for instance_str in instances_config.split(','):
            if ':' in instance_str:
                host, port = instance_str.strip().split(':')
                self.add_instance(OllamaInstance(host=host, port=int(port)))
            else:
                self.add_instance(OllamaInstance(host=instance_str.strip()))
        
        # Load other settings
        self.default_timeout = self.config.getfloat('OLLAMA', 'default_timeout', fallback=30.0)
        self.max_retries = self.config.getint('OLLAMA', 'max_retries', fallback=3)
        self.enable_batching = self.config.getboolean('OLLAMA', 'enable_batching', fallback=True)
        self.batch_size = self.config.getint('OLLAMA', 'batch_size', fallback=10)
    
    def add_instance(self, instance: OllamaInstance):
        """Add Ollama instance"""
        if instance.instance_id not in [i.instance_id for i in self.instances]:
            self.instances.append(instance)
            self.connection_pools[instance.instance_id] = ConnectionPool(instance)
            logging.info(f"Added Ollama instance: {instance.instance_id}")
    
    def remove_instance(self, instance_id: str):
        """Remove Ollama instance"""
        self.instances = [i for i in self.instances if i.instance_id != instance_id]
        if instance_id in self.connection_pools:
            asyncio.create_task(self.connection_pools[instance_id].close())
            del self.connection_pools[instance_id]
        logging.info(f"Removed Ollama instance: {instance_id}")
    
    def _get_connection_pool(self, instance: OllamaInstance) -> ConnectionPool:
        """Get connection pool for instance"""
        return self.connection_pools[instance.instance_id]
    
    async def start(self):
        """Start the Ollama manager"""
        if self.running:
            return
        
        self.running = True
        
        # Start health monitoring
        await self.health_monitor.start()
        
        # Start batch processor if enabled
        if self.enable_batching:
            self.batch_processor_task = asyncio.create_task(self._batch_processor())
        
        logging.info("Advanced Ollama Manager started")
    
    async def stop(self):
        """Stop the Ollama manager"""
        if not self.running:
            return
        
        self.running = False
        
        # Stop health monitoring
        await self.health_monitor.stop()
        
        # Stop batch processor
        if self.batch_processor_task:
            self.batch_processor_task.cancel()
            try:
                await self.batch_processor_task
            except asyncio.CancelledError:
                pass
        
        # Close all connection pools
        for pool in self.connection_pools.values():
            await pool.close()
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        logging.info("Advanced Ollama Manager stopped")
    
    async def generate(self, request: InferenceRequest) -> InferenceResponse:
        """Generate response for inference request"""
        if self.enable_batching and not request.stream:
            # Add to batch queue
            future = asyncio.Future()
            await self.request_queue.put((request, future))
            return await future
        else:
            # Process immediately
            return await self._process_request(request)
    
    async def generate_stream(self, request: InferenceRequest) -> AsyncGenerator[InferenceResponse, None]:
        """Generate streaming response"""
        request.stream = True
        
        # Select instance
        available_instances = self.model_manager.get_instances_with_model(request.model)
        if not available_instances:
            # Try to ensure model is available on at least one instance
            if self.instances:
                success = await self.model_manager.ensure_model_available(request.model, self.instances[0])
                if success:
                    available_instances = [self.instances[0]]
        
        if not available_instances:
            yield InferenceResponse(
                success=False,
                error=f"Model {request.model} not available on any instance",
                request_id=request.request_id
            )
            return
        
        instance = self.load_balancer.select_instance(available_instances, request)
        if not instance:
            yield InferenceResponse(
                success=False,
                error="No healthy instances available",
                request_id=request.request_id
            )
            return
        
        # Stream from instance
        async for response in self._stream_from_instance(request, instance):
            yield response
    
    async def _process_request(self, request: InferenceRequest) -> InferenceResponse:
        """Process single inference request"""
        start_time = time.time()
        self.total_requests += 1
        
        # Ensure model is available
        available_instances = self.model_manager.get_instances_with_model(request.model)
        if not available_instances:
            # Try to ensure model is available on at least one instance
            if self.instances:
                success = await self.model_manager.ensure_model_available(request.model, self.instances[0])
                if success:
                    available_instances = [self.instances[0]]
        
        if not available_instances:
            self.failed_requests += 1
            return InferenceResponse(
                success=False,
                error=f"Model {request.model} not available on any instance",
                request_id=request.request_id
            )
        
        # Try with retries
        last_error = None
        for attempt in range(request.max_retries):
            try:
                # Select instance
                instance = self.load_balancer.select_instance(available_instances, request)
                if not instance:
                    raise Exception("No healthy instances available")
                
                # Make request
                response = await self._make_inference_request(request, instance)
                
                # Record metrics
                processing_time = time.time() - start_time
                self.total_response_time += processing_time
                self.successful_requests += 1
                
                # Update load balancer
                self.load_balancer.record_response_time(instance.instance_id, processing_time)
                
                # Update instance metrics
                instance.total_requests += 1
                
                response.processing_time = processing_time
                response.instance_id = instance.instance_id
                response.retry_count = attempt
                
                return response
                
            except Exception as e:
                last_error = str(e)
                logging.warning(f"Request attempt {attempt + 1} failed: {e}")
                
                if attempt < request.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
        
        # All retries failed
        self.failed_requests += 1
        return InferenceResponse(
            success=False,
            error=last_error or "All retry attempts failed",
            request_id=request.request_id,
            retry_count=request.max_retries
        )
    
    async def _make_inference_request(self, request: InferenceRequest, instance: OllamaInstance) -> InferenceResponse:
        """Make inference request to specific instance"""
        pool = self._get_connection_pool(instance)
        
        # Prepare request data
        data = request.to_ollama_dict()
        
        # Make request
        async with pool.request("POST", "/api/generate", json=data) as response:
            if response.status == 200:
                if request.stream:
                    # Handle streaming response
                    return await self._handle_streaming_response(response, request)
                else:
                    # Handle non-streaming response
                    result = await response.json()
                    return InferenceResponse(
                        success=True,
                        response=result.get("response", ""),
                        model=result.get("model", request.model),
                        context=result.get("context"),
                        done=result.get("done", True),
                        total_duration=result.get("total_duration"),
                        load_duration=result.get("load_duration"),
                        prompt_eval_count=result.get("prompt_eval_count"),
                        prompt_eval_duration=result.get("prompt_eval_duration"),
                        eval_count=result.get("eval_count"),
                        eval_duration=result.get("eval_duration"),
                        request_id=request.request_id
                    )
            else:
                error_text = await response.text()
                raise Exception(f"HTTP {response.status}: {error_text}")
    
    async def _stream_from_instance(self, request: InferenceRequest, instance: OllamaInstance) -> AsyncGenerator[InferenceResponse, None]:
        """Stream response from specific instance"""
        pool = self._get_connection_pool(instance)
        data = request.to_ollama_dict()
        
        try:
            async with pool.request("POST", "/api/generate", json=data) as response:
                if response.status == 200:
                    async for line in response.content:
                        if line:
                            try:
                                chunk_data = json.loads(line.decode())
                                yield InferenceResponse(
                                    success=True,
                                    response=chunk_data.get("response", ""),
                                    model=chunk_data.get("model", request.model),
                                    context=chunk_data.get("context"),
                                    done=chunk_data.get("done", False),
                                    total_duration=chunk_data.get("total_duration"),
                                    load_duration=chunk_data.get("load_duration"),
                                    prompt_eval_count=chunk_data.get("prompt_eval_count"),
                                    prompt_eval_duration=chunk_data.get("prompt_eval_duration"),
                                    eval_count=chunk_data.get("eval_count"),
                                    eval_duration=chunk_data.get("eval_duration"),
                                    request_id=request.request_id,
                                    instance_id=instance.instance_id
                                )
                                
                                if chunk_data.get("done", False):
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                else:
                    error_text = await response.text()
                    yield InferenceResponse(
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        request_id=request.request_id,
                        instance_id=instance.instance_id
                    )
                    
        except Exception as e:
            yield InferenceResponse(
                success=False,
                error=str(e),
                request_id=request.request_id,
                instance_id=instance.instance_id
            )
    
    async def _batch_processor(self):
        """Process requests in batches"""
        batch = []
        batch_futures = []
        last_batch_time = time.time()
        
        while self.running:
            try:
                # Wait for request or timeout
                try:
                    timeout = self.batch_timeout - (time.time() - last_batch_time)
                    if timeout <= 0:
                        timeout = 0.01
                    
                    request, future = await asyncio.wait_for(
                        self.request_queue.get(), 
                        timeout=timeout
                    )
                    
                    batch.append(request)
                    batch_futures.append(future)
                    
                except asyncio.TimeoutError:
                    pass
                
                # Process batch if ready
                current_time = time.time()
                should_process = (
                    len(batch) >= self.batch_size or 
                    (batch and (current_time - last_batch_time) >= self.batch_timeout)
                )
                
                if should_process and batch:
                    # Process batch
                    await self._process_batch(batch, batch_futures)
                    batch = []
                    batch_futures = []
                    last_batch_time = current_time
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Batch processor error: {e}")
                
                # Fail pending requests
                for future in batch_futures:
                    if not future.done():
                        future.set_result(InferenceResponse(
                            success=False,
                            error=f"Batch processing error: {e}"
                        ))
                
                batch = []
                batch_futures = []
    
    async def _process_batch(self, requests: List[InferenceRequest], futures: List[asyncio.Future]):
        """Process batch of requests"""
        # Group by model for efficiency
        model_groups = defaultdict(list)
        for i, request in enumerate(requests):
            model_groups[request.model].append((request, futures[i]))
        
        # Process each model group
        tasks = []
        for model, group in model_groups.items():
            task = asyncio.create_task(self._process_model_group(group))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_model_group(self, group: List[tuple]):
        """Process requests for same model"""
        # Process requests concurrently
        tasks = []
        for request, future in group:
            task = asyncio.create_task(self._process_single_request_for_batch(request, future))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_request_for_batch(self, request: InferenceRequest, future: asyncio.Future):
        """Process single request within batch"""
        try:
            response = await self._process_request(request)
            future.set_result(response)
        except Exception as e:
            future.set_result(InferenceResponse(
                success=False,
                error=str(e),
                request_id=request.request_id
            ))
    
    async def get_available_models(self, instance_id: Optional[str] = None) -> List[str]:
        """Get available models"""
        if instance_id:
            # Get models from specific instance
            instance = next((i for i in self.instances if i.instance_id == instance_id), None)
            if instance:
                return instance.available_models.copy()
            return []
        else:
            # Get models from all instances
            all_models = set()
            for instance in self.instances:
                all_models.update(instance.available_models)
            return list(all_models)
    
    async def pull_model(self, model: str, instance_id: Optional[str] = None) -> Dict[str, bool]:
        """Pull model to instances"""
        results = {}
        
        if instance_id:
            # Pull to specific instance
            instance = next((i for i in self.instances if i.instance_id == instance_id), None)
            if instance:
                success = await self.model_manager.ensure_model_available(model, instance)
                results[instance_id] = success
        else:
            # Pull to all instances
            tasks = []
            for instance in self.instances:
                task = asyncio.create_task(self.model_manager.ensure_model_available(model, instance))
                tasks.append((instance.instance_id, task))
            
            for instance_id, task in tasks:
                try:
                    success = await task
                    results[instance_id] = success
                except Exception as e:
                    logging.error(f"Error pulling model {model} to {instance_id}: {e}")
                    results[instance_id] = False
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        healthy_instances = len([i for i in self.instances if i.status == InstanceStatus.HEALTHY])
        avg_response_time = 0.0
        if self.successful_requests > 0:
            avg_response_time = self.total_response_time / self.successful_requests
        
        return {
            "instances": {
                "total": len(self.instances),
                "healthy": healthy_instances,
                "degraded": len([i for i in self.instances if i.status == InstanceStatus.DEGRADED]),
                "unhealthy": len([i for i in self.instances if i.status == InstanceStatus.UNHEALTHY])
            },
            "requests": {
                "total": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "success_rate": self.successful_requests / max(1, self.total_requests)
            },
            "performance": {
                "avg_response_time": avg_response_time,
                "queue_size": self.request_queue.qsize() if hasattr(self.request_queue, 'qsize') else 0
            },
            "models": {
                "total_unique": len(self.get_available_models()),
                "download_progress": dict(self.model_manager.download_progress)
            }
        }
    
    def get_instance_stats(self) -> List[Dict[str, Any]]:
        """Get per-instance statistics"""
        stats = []
        for instance in self.instances:
            stats.append({
                "instance_id": instance.instance_id,
                "status": instance.status.value,
                "health_score": instance.health_score,
                "active_connections": instance.active_connections,
                "max_connections": instance.max_connections,
                "total_requests": instance.total_requests,
                "failed_requests": instance.failed_requests,
                "avg_response_time": instance.avg_response_time,
                "available_models": len(instance.available_models),
                "last_health_check": instance.last_health_check.isoformat() if instance.last_health_check else None,
                "cpu_usage": instance.cpu_usage,
                "gpu_memory_used": instance.gpu_memory_used
            })
        return stats


# Convenience functions for integration with existing codebase
def create_advanced_ollama_manager(config_manager=None) -> AdvancedOllamaManager:
    """Factory function to create advanced Ollama manager"""
    return AdvancedOllamaManager(config_manager)


async def quick_generate(prompt: str, model: str = "llama2", **options) -> str:
    """Quick generation function for simple use cases"""
    manager = AdvancedOllamaManager()
    
    # Add local instance if none configured
    if not manager.instances:
        manager.add_instance(OllamaInstance(host="localhost"))
    
    await manager.start()
    
    try:
        request = InferenceRequest(
            model=model,
            prompt=prompt,
            options=options
        )
        
        response = await manager.generate(request)
        
        if response.success:
            return response.response or ""
        else:
            raise Exception(response.error)
            
    finally:
        await manager.stop()


# Integration with existing AI manager
class EnhancedInferenceEngine:
    """Enhanced inference engine using advanced Ollama integration"""
    
    def __init__(self, config_manager=None):
        self.ollama_manager = AdvancedOllamaManager(config_manager)
        self.fallback_enabled = True
        
    async def run_inference(self, model_name: str, input_data: Any, **kwargs) -> Dict[str, Any]:
        """Run inference with advanced Ollama backend"""
        try:
            # Ensure manager is started
            if not self.ollama_manager.running:
                await self.ollama_manager.start()
            
            # Create request
            request = InferenceRequest(
                model=model_name,
                prompt=str(input_data),
                options=kwargs.get('options', {}),
                stream=kwargs.get('stream', False)
            )
            
            # Generate response
            if request.stream:
                # Handle streaming
                full_response = ""
                async for chunk in self.ollama_manager.generate_stream(request):
                    if chunk.success and chunk.response:
                        full_response += chunk.response
                
                return {
                    'success': True,
                    'prediction': full_response,
                    'model_used': model_name,
                    'processing_method': 'advanced_ollama_streaming'
                }
            else:
                # Handle regular response
                response = await self.ollama_manager.generate(request)
                
                return {
                    'success': response.success,
                    'prediction': response.response if response.success else None,
                    'error': response.error if not response.success else None,
                    'model_used': model_name,
                    'processing_time': response.processing_time,
                    'tokens_per_second': response.tokens_per_second,
                    'instance_id': response.instance_id,
                    'retry_count': response.retry_count,
                    'processing_method': 'advanced_ollama'
                }
                
        except Exception as e:
            if self.fallback_enabled:
                # Fallback to basic inference if configured
                return {
                    'success': False,
                    'error': f'Advanced Ollama failed: {e}',
                    'fallback_used': True
                }
            else:
                raise
    
    async def close(self):
        """Clean shutdown"""
        await self.ollama_manager.stop()


if __name__ == "__main__":
    # Example usage
    async def main():
        # Create manager
        manager = AdvancedOllamaManager()
        
        # Add instances
        manager.add_instance(OllamaInstance(host="localhost", port=11434))
        manager.add_instance(OllamaInstance(host="192.168.1.100", port=11434))
        
        # Start manager
        await manager.start()
        
        try:
            # Simple generation
            request = InferenceRequest(
                model="llama2",
                prompt="Explain quantum computing in simple terms."
            )
            
            response = await manager.generate(request)
            print(f"Response: {response.response}")
            print(f"Tokens/sec: {response.tokens_per_second}")
            
            # Streaming generation
            print("\nStreaming response:")
            async for chunk in manager.generate_stream(request):
                if chunk.success and chunk.response:
                    print(chunk.response, end="", flush=True)
            
            # Get stats
            stats = manager.get_stats()
            print(f"\nStats: {stats}")
            
        finally:
            await manager.stop()
    
    # Run example
    if OLLAMA_AVAILABLE:
        asyncio.run(main())
    else:
        print("Install ollama-python to run example: pip install ollama")
