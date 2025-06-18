import time

from ...core.events import event_bus
from ...config.settings import settings

class TaskExecutor:
    def __init__(self):
        self.batch_size = settings.get("TASK_FETCH_BATCH", 5)


    def execute(self, task: dict):
        task_id = task.get("task_id", "unknown")
        print(f"🛠️ Executing task: {task_id}")
        time.sleep(1)  # Simulate workload
        result = {"task_id": task_id, "status": "success"}
        print(f"✅ Completed task: {task_id}")
        event_bus.publish("task.completed", result)
        return result
