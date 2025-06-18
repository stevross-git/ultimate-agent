#!/usr/bin/env python3
"""
Dashboard Verification Script
Tests if the dashboard is working correctly
"""

import sys
import time
import requests
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

def test_agent_creation():
    """Test agent creation"""
    print("🧪 Testing agent creation...")
    
    try:
        # Try importing agent1 first
        try:
            from ultimate_agent.core.agent1 import UltimatePainNetworkAgent
            agent = UltimatePainNetworkAgent()
            print("✅ UltimatePainNetworkAgent created successfully")
        except ImportError:
            from ultimate_agent.core.agent import UltimateAgent
            agent = UltimateAgent()
            print("✅ UltimateAgent created successfully")
        
        return agent
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return None

def test_dashboard_initialization(agent):
    """Test dashboard initialization"""
    print("🧪 Testing dashboard initialization...")
    
    try:
        if hasattr(agent, 'dashboard_manager') and agent.dashboard_manager:
            print("✅ Dashboard manager found")
            return True
        elif 'dashboard' in getattr(agent, 'modules', {}):
            print("✅ Dashboard module found in modules")
            return True
        else:
            print("❌ Dashboard not properly initialized")
            return False
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        return False

def test_dashboard_server():
    """Test if dashboard server is responding"""
    print("🧪 Testing dashboard server response...")
    
    try:
        response = requests.get("http://localhost:8080", timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard server responding")
            return True
        else:
            print(f"⚠️ Dashboard server returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Dashboard server not responding (connection refused)")
        return False
    except Exception as e:
        print(f"❌ Dashboard server test failed: {e}")
        return False

def main():
    print("🔍 Dashboard Verification Test")
    print("=" * 40)
    
    # Test agent creation
    agent = test_agent_creation()
    if not agent:
        sys.exit(1)
    
    # Test dashboard initialization
    dashboard_ok = test_dashboard_initialization(agent)
    
    # If dashboard is initialized, test if server is running
    if dashboard_ok:
        print("⏳ Waiting for server to start...")
        time.sleep(3)  # Give server time to start
        test_dashboard_server()
    
    print("\n📋 Verification complete!")
    print("If all tests passed, your dashboard should be working.")

if __name__ == "__main__":
    main()
