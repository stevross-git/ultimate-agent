#!/usr/bin/env python3
"""
Ultimate Agent Launcher
Simple launcher script that handles import path issues
"""

import sys
from pathlib import Path
import argparse

# Allow running directly via `python main.py`
if __package__ in (None, ""):
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    sys.path.insert(0, str(parent_dir))
    sys.path.insert(0, str(current_dir))


def main():
    """Launch the Ultimate Agent with proper path setup"""
    
    # Get the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    
    # Add the ultimate_agent directory to Python path
    ultimate_agent_dir = script_dir 
    if ultimate_agent_dir.exists():
        sys.path.insert(0, str(ultimate_agent_dir))
        print(f"✅ Added {ultimate_agent_dir} to Python path")
    else:
        print(f"❌ Error: {ultimate_agent_dir} not found")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description="Launch the Ultimate Agent")
    parser.add_argument("--node-url", help="Node URL for registration", default=None)
    parser.add_argument("--dashboard-port", type=int, help="Dashboard port", default=None)
    args = parser.parse_args()

    try:

        from ultimate_agent import create_agent

        print("🤖 Initializing Ultimate Agent...")

        agent = create_agent(node_url=args.node_url, dashboard_port=args.dashboard_port)

        print("🚀 Starting Ultimate Agent...")
        agent.start()

        # ✅ ADD THIS BLOCK
        if hasattr(agent, "dashboard_manager") and agent.dashboard_manager:
            print("🌐 Launching Dashboard Web Server on port", agent.dashboard_port)
            agent.dashboard_manager.start_server()
        else:
            print("⚠️ Dashboard not initialized or missing")


        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\n🔧 Troubleshooting suggestions:")
        print("1. Make sure you're in the ultimate_agent_full_bundle directory")
        print("2. Run: pip install -r ultimate_agent/requirements.txt")
        print("3. Try: python -m ultimate_agent.main")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Ultimate Agent...")
    except Exception as e:
        print(f"❌ Error starting agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()