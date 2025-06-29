import sys
from setuptools import setup, find_packages

# Check Python version
if sys.version_info < (3, 9):
    sys.exit("Python 3.9+ required")

# Platform-specific dependencies
install_requires = [
    "asyncio-mqtt>=0.16.0",
    "cryptography>=41.0.0",
    "aiofiles>=23.0.0",
    "aiohttp>=3.9.0",
    "websockets>=12.0",
    "redis>=5.0.0",
    "prometheus-client>=0.19.0",
    "psutil>=5.9.0",
    "msgpack>=1.0.0",
    "netifaces>=0.11.0",
    "aiodns>=3.1.0",
    "kademlia>=2.2.0",
    "asyncio-dgram>=2.1.0",
]

# Windows-specific
if sys.platform == "win32":
    install_requires.extend([
        "pywin32>=306",
        "winsdk>=1.0.0",
    ])
else:
    install_requires.extend([
        "uvloop>=0.19.0",
    ])

setup(
    name="quantum-p2p-integration",
    version="1.0.0",
    description="Production-ready Quantum P2P Integration for Ultimate Agent",
    author="Ultimate Agent Team",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={
        "quantum": ["qiskit>=0.45.0", "numpy>=1.25.0"],
        "dev": ["pytest>=7.4.0", "pytest-asyncio>=0.21.0", "black>=23.0.0"],
    },
    entry_points={
        "console_scripts": [
            "quantum-p2p-demo=ultimate_agent.network.p2p.demo:main",
        ],
    },
)
