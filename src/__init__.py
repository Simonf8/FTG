"""
Distributed Edge AI Network - Main Package
"""

__version__ = "1.0.0"
__author__ = "Edge AI Network Team"
__description__ = "A comprehensive smart city infrastructure system"

from .coordinator import Coordinator
from .edge_node import EdgeNode
from .common import config, logger, models

__all__ = [
    "Coordinator",
    "EdgeNode",
    "config",
    "logger",
    "models",
]
