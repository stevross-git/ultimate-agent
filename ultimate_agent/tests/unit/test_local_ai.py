#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Add Ultimate Agent to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_local_ai():
    print("🧪 Testing Local AI Integration...")
    
    try:
        # Import your agent
        from ultimate_agent.core.agent1 import UltimatePainNetworkAgent
        
        # Create agent instance
        agent = UltimatePainNetworkAgent()
        
        # Test Local AI availability
        if agent.local_ai_manager:
            print("✅ Local AI Manager initialized")
            
            # Get hardware info
            hw_info = agent.local_ai_manager.get_hardware_info()
            print(f"🖥️ Hardware: {hw_info['hardware_type']}")
            print(f"💾 Memory: {hw_info['system_info']['memory_gb']:.1f}GB")
            
            # List recommended models
            models = agent.local_ai_manager.list_available_models()
            print(f"📦 Recommended models: {len(models['recommended_models'])}")
            
            # Test inference if models available
            available_models = [m for m in models['recommended_models'] if m['available']]
            if available_models:
                print("🧠 Testing inference...")
                result = await agent.local_ai_manager.generate_response(
                    "Hello! Please respond with 'Local AI is working' if you can understand this."
                )
                
                if result['success']:
                    print(f"✅ Inference successful!")
                    print(f"   Model: {result['model_used']}")
                    print(f"   Time: {result['processing_time']:.2f}s")
                    print(f"   Response: {result['response'][:100]}...")
                else:
                    print(f"❌ Inference failed: {result['error']}")
            else:
                print("📥 No models available - try downloading one with: ollama pull llama2:7b-q4_0")
        else:
            print("❌ Local AI Manager not available")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_local_ai())