import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from ultimate_agent.core.agent import UltimateAgent


def test_ping_command():
    agent = UltimateAgent()
    result = agent.handle_command("ping")
    assert result["message"] == "pong"
