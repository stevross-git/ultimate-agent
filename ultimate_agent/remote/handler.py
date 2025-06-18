from typing import Any, Callable, Dict

from ..core.events import event_bus


class RemoteCommandHandler:
    """Simple remote command processor."""

    def __init__(self):
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "ping": self.ping,
            "shutdown": self.shutdown,
            "echo": self.echo,
        }
        event_bus.subscribe("remote.command", self.handle_command)
        self._shutdown_callback: Callable[[], None] | None = None

    def execute(self, command: str, **params: Any) -> Dict[str, Any]:
        """Execute command directly and return result."""
        handler = self._handlers.get(command)
        if not handler:
            return {"error": f"unknown command {command}"}
        return handler(params)

    def set_shutdown_callback(self, cb: Callable[[], None]):
        self._shutdown_callback = cb

    def handle_command(self, command: Dict[str, Any]):
        command_type = command.get("command")
        handler = self._handlers.get(command_type)
        if not handler:
            result = {"error": f"unknown command {command_type}"}
        else:
            params = command.get("params", {})
            result = handler(params)
        event_bus.publish("remote.command.result", {"command": command_type, "result": result})

    def ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "pong"}

    def echo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"echo": params}

    def shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self._shutdown_callback:
            self._shutdown_callback()
        return {"status": "shutting down"}
