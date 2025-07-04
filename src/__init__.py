"""
Distributed Edge AI Network

A comprehensive edge computing platform for smart city applications,
supporting traffic optimization, crime detection, and environmental monitoring.
"""

__version__ = "1.0.0"
__author__ = "Edge AI Network Team"
__email__ = "team@edgeai.example.com"
__license__ = "MIT"
__description__ = "A comprehensive smart city infrastructure system"

# Import main components
from .common.config import get_config
from .common.logger import get_logger
from .common.models import (
    SensorData, TrafficData, CrimeData, EnvironmentData,
    Alert, AlertSeverity, AlertStatus, NodeStatus, EdgeNode
)

# Import edge node components
from .edge_node.base import EdgeNodeBase
from .edge_node.ai_processors import TrafficProcessor, CrimeProcessor, EnvironmentProcessor

# Import coordinator components
from .coordinator.core import CentralCoordinator

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__description__",
    "get_config",
    "get_logger",
    "SensorData",
    "TrafficData", 
    "CrimeData",
    "EnvironmentData",
    "Alert",
    "AlertSeverity",
    "AlertStatus",
    "NodeStatus",
    "EdgeNode",
    "EdgeNodeBase",
    "TrafficProcessor",
    "CrimeProcessor",
    "EnvironmentProcessor",
    "CentralCoordinator",
]
from .common import config, logger, models

__all__ = [
    "Coordinator",
    "EdgeNode",
    "config",
    "logger",
    "models",
]
