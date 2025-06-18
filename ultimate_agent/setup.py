#!/usr/bin/env python3
"""
setup.py
Enhanced Ultimate Pain Network Agent - Modular Architecture
Package setup and installation configuration
"""

from setuptools import setup, find_packages
import os
import sys
from pathlib import Path

# Read version from package
def get_version():
    """Get version from package __init__.py"""
    try:
        from ultimate_agent import __version__
        return __version__
    except ImportError:
        return "3.0.0-modular"

# Read README for long description
def get_long_description():
    """Get long description from README"""
    readme_path = Path(__file__).parent / "README.md"
    if readme_path.exists():
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Enhanced Ultimate Pain Network Agent with Modular Architecture"

# Read requirements
def get_requirements():
    """Get requirements from requirements.txt"""
    requirements_path = Path(__file__).parent / "requirements.txt"
    if requirements_path.exists():
        with open(requirements_path, "r", encoding="utf-8") as f:
            requirements = []
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    # Handle conditional requirements
                    if ";" in line:
                        req = line.split(";")[0].strip()
                    else:
                        req = line
                    requirements.append(req)
            return requirements
    return [
        "requests>=2.28.0",
        "flask>=2.3.0",
        "flask-cors>=4.0.0",
        "flask-socketio>=5.3.0",
        "numpy>=1.21.0",
        "psutil>=5.9.0",
        "sqlalchemy>=1.4.0",
        "cryptography>=3.4.8"
    ]

# Optional dependencies
extras_require = {
    'ai': [
        'torch>=1.13.0',
        'torchvision>=0.14.0',
        'pandas>=1.5.0',
        'scipy>=1.9.0'
    ],
    'gpu': [
        'GPUtil>=1.4.0',
        'torch[cuda]>=1.13.0'
    ],
    'cloud': [
        'boto3>=1.26.0',
        'azure-storage-blob>=12.14.0',
        'google-cloud-storage>=2.7.0'
    ],
    'dev': [
        'pytest>=7.2.0',
        'pytest-asyncio>=0.21.0',
        'pytest-benchmark>=4.0.0',
        'black>=22.0.0',
        'flake8>=5.0.0',
        'mypy>=0.991'
    ]
}

# All optional dependencies
extras_require['all'] = list(set().union(*extras_require.values()))

setup(
    name="ultimate-agent-modular",
    version=get_version(),
    author="Ultimate Agent Team",
    author_email="team@ultimate-agent.ai",
    description="Enhanced Ultimate Pain Network Agent with Modular Architecture",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/ultimate-agent/modular",
    project_urls={
        "Bug Reports": "https://github.com/ultimate-agent/modular/issues",
        "Source": "https://github.com/ultimate-agent/modular",
        "Documentation": "https://ultimate-agent.github.io/modular"
    },
    
    # Package discovery
    packages=find_packages(exclude=["tests", "tests.*", "docs", "examples"]),
    include_package_data=True,
    
    # Package data
    package_data={
        "ultimate_agent": [
            "config/*.ini",
            "dashboard/static/*",
            "dashboard/templates/*",
            "plugins/examples/*"
        ]
    },
    
    # Requirements
    python_requires=">=3.7",
    install_requires=get_requirements(),
    extras_require=extras_require,
    
    # Entry points
    entry_points={
        "console_scripts": [
            "ultimate-agent=ultimate_agent.main:main",
            "ultimate-agent-check=ultimate_agent:print_module_status",
        ]
    },
    
    # Classification
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application"
    ],
    
    # Keywords
    keywords="ai, agent, blockchain, modular, architecture, machine-learning, automation, distributed-computing",
    
    # Dependencies
    zip_safe=False,
    
    # Additional metadata
    platforms=["any"],
    license="MIT",
    
    # Testing
    test_suite="tests",
    tests_require=extras_require['dev']
)

# Post-installation setup
def post_install():
    """Post-installation setup tasks"""
    print("🚀 Enhanced Ultimate Pain Network Agent installed successfully!")
    print("📦 Modular architecture with enterprise features")
    print("\n🎯 Quick Start:")
    print("  ultimate-agent --help")
    print("  ultimate-agent --show-modules") 
    print("  ultimate-agent")
    print("\n📚 Documentation: https://ultimate-agent.github.io/modular")

if __name__ == "__main__":
    # Run setup
    setup()
    
    # Run post-install if installing
    if "install" in sys.argv:
        post_install()
