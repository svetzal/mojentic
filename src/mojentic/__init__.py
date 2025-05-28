"""
Mojentic is an agentic framework that aims to provide a simple and flexible way to assemble teams of agents to solve
complex problems. Design goals are to be asynchronous with a pubsub messaging architecture.
"""
import importlib.metadata as _importlib_metadata
import logging

import structlog

# Core components
from .dispatcher import Dispatcher
from .event import Event
from .router import Router

# Initialize logging
logging.basicConfig(level=logging.INFO)
structlog.configure(logger_factory=structlog.stdlib.LoggerFactory(), processors=[
    structlog.stdlib.filter_by_level,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.JSONRenderer()
])
logger = structlog.get_logger()
logger.info("Starting logger")


__version__: str
try:
    __version__ = _importlib_metadata.version(__name__)
except _importlib_metadata.PackageNotFoundError:
    __version__ = "unknown"
