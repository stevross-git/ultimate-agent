#!/usr/bin/env python3
import re

# Fix main.py
with open('main.py', 'r') as f:
    main_content = f.read()

# Replace the dashboard_port access
main_content = re.sub(
    r'agent\.dashboard_port', 
    'dashboard_port', 
    main_content
)

# Add keep-alive loop
if 'while True:' not in main_content:
    main_content = main_content.replace(
        'agent.start()',
        '''agent.start()

        # Keep the main thread alive
        try:
            import time
            print("✅ Ultimate Agent is running...")
            print("Press Ctrl+C to stop")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\\n🛑 Shutting down Ultimate Agent...")
            if hasattr(agent, 'stop'):
                agent.stop()'''
    )

with open('main.py', 'w') as f:
    f.write(main_content)

print("✅ Fixed main.py")
