# ultimate_agent/config/__init__.py

"""Package initialization for configuration module."""

# Import the settings dictionary from settings.py
from .settings import settings

# Export `config` as an alias for backward compatibility
config = settings

# Simple sanity check to ensure settings were loaded
print(settings["port"])
