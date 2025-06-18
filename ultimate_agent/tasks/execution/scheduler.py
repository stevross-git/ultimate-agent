
#!/usr/bin/env python3
"""
ultimate_agent/tasks/execution/scheduler.py
Task scheduling and execution management
"""

import asyncio
import signal
import time
import threading
import random
import uuid
from datetime import datetime
from typing import Dict, Any, List, Callable

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    class _DummyNumpy:
        class ndarray:
            pass
    np = _DummyNumpy()

try:
    import aioredis  # type: ignore
except ModuleNotFoundError:
    aioredis = None

from .executor import TaskExecutor
from ...config.settings import settings
from ..simulation import TaskSimulator
from ..control import TaskControlClient


class TaskScheduler:
    """Manages task scheduling, execution, and Redis streaming."""

    def __init__(self, config):
        self.config = config or {}

        self.ai_manager = config.get('ai_manager')
        self.blockchain_manager = config.get('blockchain_manager')

        self.task_simulator = TaskSimulator(self.ai_manager, self.blockchain_manager)
        self.task_control_client = TaskControlClient(self)

        self.current_tasks = {}
        self.completed_tasks = []
        self.task_queue = []
        self.max_concurrent_tasks = config.get('max_concurrent_tasks', 3)

        self.executor_threads = {}
        self.running = True

        self.executor = TaskExecutor()
        self.redis = None
        self.shutdown_event = asyncio.Event()
        self.stream_key = "agent:tasks"
        self.group_name = "agent-workers"
        self.consumer_name = f"agent-{id(self)}"

        print("🎯 Task Scheduler initialized")

    async def connect_redis(self):
        if aioredis is None:
            raise RuntimeError("aioredis is required for scheduler")
        self.redis = await aioredis.from_url(settings.get("REDIS_URL", "redis://localhost:6379"))
        print("🔗 Connected to Redis")
        try:
            await self.redis.xgroup_create(self.stream_key, self.group_name, id='0', mkstream=True)
            print(f"🆕 Created Redis stream group: {self.group_name}")
        except aioredis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                print("ℹ️ Redis group already exists.")
            else:
                raise

    async def read_stream_tasks(self):
        while not self.shutdown_event.is_set():
            try:
                results = await self.redis.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream_key: '>'},
                    count=5,
                    block=3000
                )
                if results:
                    for stream_key, messages in results:
                        for message_id, fields in messages:
                            task = {k.decode(): v.decode() for k, v in fields.items()}
                            print(f"🔧 Received task: {task}")
                            self.executor.execute(task)
                            await self.redis.xack(self.stream_key, self.group_name, message_id)
            except Exception as e:
                print(f"❌ Error reading stream: {e}")
                await asyncio.sleep(1)

    async def redis_listener(self):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe("agent:control")
        print("📡 Subscribed to Redis channel: agent:control")
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = message["data"].decode() if isinstance(message["data"], bytes) else message["data"]
                    print(f"📨 Redis Control Message: {data}")
                    import json
                    command = json.loads(data)
                    from ...core.events import event_bus
                    event_bus.publish("remote.command", command)
                except Exception as e:
                    print(f"❌ Failed to process control message: {e}")

    async def run_loop(self):
        await self.connect_redis()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.shutdown_event.set)

        print("🌀 TaskScheduler with Redis stream group started")

        stream_task = asyncio.create_task(self.read_stream_tasks())
        redis_task = asyncio.create_task(self.redis_listener())

        await self.shutdown_event.wait()
        print("🛑 Shutdown initiated")

        stream_task.cancel()
        redis_task.cancel()

        await self.redis.close()

    async def process_pending(self):
        """Placeholder for async task processing logic"""
        print("🔄 Checking for pending tasks... (stub)")
