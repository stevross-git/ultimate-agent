from typing import Callable, Dict, List

class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, handler: Callable):
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(handler)

    def publish(self, event_name: str, *args, **kwargs):
        handlers = self._listeners.get(event_name, [])
        for handler in handlers:
            handler(*args, **kwargs)

# Global event bus instance
event_bus = EventBus()

# Example:
# def on_startup():
#     print("🟢 Agent is starting")
# event_bus.subscribe("startup", on_startup)
# event_bus.publish("startup")
