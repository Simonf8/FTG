"""
Edge Node Implementation
"""

from .base import BaseEdgeNode
from .ai_processors import TrafficProcessor, CrimeProcessor, EnvironmentProcessor
from .sensors import SensorManager
from .communication import CommunicationManager
from .storage import LocalStorage

__all__ = [
    "BaseEdgeNode",
    "TrafficProcessor",
    "CrimeProcessor", 
    "EnvironmentProcessor",
    "SensorManager",
    "CommunicationManager",
    "LocalStorage"
]

# Main edge node class
EdgeNode = BaseEdgeNode
