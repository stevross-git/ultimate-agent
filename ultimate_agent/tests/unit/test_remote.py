import sys
from pathlib import Path

# add repository root so tests run without installation
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from ultimate_agent.remote.handler import RemoteCommandHandler
from ultimate_agent.core.events import event_bus


def test_ping_command():
    event_bus._listeners.clear()
    results = []
    handler = RemoteCommandHandler()
    event_bus.subscribe("remote.command.result", lambda data: results.append(data))
    event_bus.publish("remote.command", {"command": "ping"})
    assert results == [{"command": "ping", "result": {"status": "pong"}}]


def test_echo_command():
    event_bus._listeners.clear()
    results = []
    handler = RemoteCommandHandler()
    event_bus.subscribe("remote.command.result", lambda data: results.append(data))
    event_bus.publish("remote.command", {"command": "echo", "params": {"msg": "hi"}})
    assert results == [{"command": "echo", "result": {"echo": {"msg": "hi"}}}]

