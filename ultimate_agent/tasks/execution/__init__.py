import asyncio
import signal

try:
    import aioredis  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    aioredis = None

from .executor import TaskExecutor

class TaskScheduler:
    def __init__(self, config=None):
        self.config = config or {}
        self.executor = TaskExecutor()
        self.redis = None
        self.shutdown_event = asyncio.Event()

        # Redis stream settings
        self.stream_key = self.config.get("REDIS_STREAM_KEY", "agent:tasks")
        self.group_name = self.config.get("REDIS_GROUP_NAME", "agent-workers")
        self.consumer_name = self.config.get("REDIS_CONSUMER_PREFIX", "agent-") + str(id(self))

    async def connect_redis(self):
        if aioredis is None:
            raise RuntimeError("aioredis is required for scheduler")
        redis_url = self.config.get("REDIS_URL", "redis://localhost:6379")
        self.redis = await aioredis.from_url(redis_url)
        print("🔗 Connected to Redis")
        try:
            await self.redis.xgroup_create(self.stream_key, self.group_name, id='0', mkstream=True)
            print(f"🌟 Created Redis stream group: {self.group_name}")
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
        print("📱 Subscribed to Redis channel: agent:control")
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

        print("🔀 TaskScheduler with Redis stream group started")

        stream_task = asyncio.create_task(self.read_stream_tasks())
        redis_task = asyncio.create_task(self.redis_listener())

        await self.shutdown_event.wait()
        print("🚭 Shutdown initiated")

        stream_task.cancel()
        redis_task.cancel()

        await self.redis.close()