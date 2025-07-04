"""
Data models for the distributed edge AI network
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
import json


class NodeType(str, Enum):
    """Types of edge nodes"""
    TRAFFIC = "traffic"
    CRIME = "crime"
    ENVIRONMENT = "environment"
    HYBRID = "hybrid"


class SensorType(str, Enum):
    """Types of sensors"""
    CAMERA = "camera"
    MICROPHONE = "microphone"
    AIR_QUALITY = "air_quality"
    MOTION = "motion"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    NOISE = "noise"
    TRAFFIC_COUNTER = "traffic_counter"
    LIDAR = "lidar"
    RADAR = "radar"


class AlertLevel(str, Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProcessingStatus(str, Enum):
    """Processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Location:
    """Geographic location"""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    address: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "address": self.address
        }


@dataclass
class SensorData:
    """Base sensor data model"""
    sensor_id: str
    sensor_type: SensorType
    timestamp: datetime
    location: Location
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "sensor_type": self.sensor_type.value,
            "timestamp": self.timestamp.isoformat(),
            "location": self.location.to_dict(),
            "data": self.data,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SensorData':
        return cls(
            sensor_id=data["sensor_id"],
            sensor_type=SensorType(data["sensor_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            location=Location(**data["location"]),
            data=data["data"],
            metadata=data.get("metadata", {})
        )


@dataclass
class AIInference:
    """AI inference result"""
    model_id: str
    model_version: str
    inference_time: float
    confidence: float
    predictions: List[Dict[str, Any]]
    input_data_id: str
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_version": self.model_version,
            "inference_time": self.inference_time,
            "confidence": self.confidence,
            "predictions": self.predictions,
            "input_data_id": self.input_data_id,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class EdgeNodeStatus:
    """Edge node status information"""
    node_id: str
    node_type: NodeType
    location: Location
    status: str  # online, offline, maintenance
    last_heartbeat: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_latency: float
    active_sensors: List[str]
    processing_queue_size: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "location": self.location.to_dict(),
            "status": self.status,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_usage": self.disk_usage,
            "network_latency": self.network_latency,
            "active_sensors": self.active_sensors,
            "processing_queue_size": self.processing_queue_size
        }


@dataclass
class Alert:
    """Alert/incident data model"""
    alert_id: str
    alert_type: str
    level: AlertLevel
    title: str
    description: str
    location: Location
    timestamp: datetime
    source_node: str
    source_data: Dict[str, Any]
    actions_taken: List[str] = field(default_factory=list)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "level": self.level.value,
            "title": self.title,
            "description": self.description,
            "location": self.location.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "source_node": self.source_node,
            "source_data": self.source_data,
            "actions_taken": self.actions_taken,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class TrafficData:
    """Traffic-specific data model"""
    vehicle_count: int
    vehicle_types: Dict[str, int]
    average_speed: float
    congestion_level: float
    flow_rate: float
    occupancy_rate: float
    incidents: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_count": self.vehicle_count,
            "vehicle_types": self.vehicle_types,
            "average_speed": self.average_speed,
            "congestion_level": self.congestion_level,
            "flow_rate": self.flow_rate,
            "occupancy_rate": self.occupancy_rate,
            "incidents": self.incidents
        }


@dataclass
class CrimeData:
    """Crime detection data model"""
    suspicious_activity: bool
    activity_type: str
    confidence_score: float
    detected_objects: List[Dict[str, Any]]
    behavior_analysis: Dict[str, Any]
    risk_assessment: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "suspicious_activity": self.suspicious_activity,
            "activity_type": self.activity_type,
            "confidence_score": self.confidence_score,
            "detected_objects": self.detected_objects,
            "behavior_analysis": self.behavior_analysis,
            "risk_assessment": self.risk_assessment
        }


@dataclass
class EnvironmentData:
    """Environmental monitoring data model"""
    temperature: float
    humidity: float
    air_quality_index: int
    pm25: float
    pm10: float
    co2: float
    noise_level: float
    uv_index: float
    wind_speed: float
    wind_direction: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "air_quality_index": self.air_quality_index,
            "pm25": self.pm25,
            "pm10": self.pm10,
            "co2": self.co2,
            "noise_level": self.noise_level,
            "uv_index": self.uv_index,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction
        }


@dataclass
class ProcessingJob:
    """Data processing job"""
    job_id: str
    job_type: str
    node_id: str
    input_data: SensorData
    status: ProcessingStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "node_id": self.node_id,
            "input_data": self.input_data.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error_message": self.error_message
        }


@dataclass
class SystemMetrics:
    """System-wide metrics"""
    timestamp: datetime
    total_nodes: int
    active_nodes: int
    total_sensors: int
    active_sensors: int
    messages_per_second: float
    processing_latency: float
    storage_usage: float
    network_usage: float
    alert_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_nodes": self.total_nodes,
            "active_nodes": self.active_nodes,
            "total_sensors": self.total_sensors,
            "active_sensors": self.active_sensors,
            "messages_per_second": self.messages_per_second,
            "processing_latency": self.processing_latency,
            "storage_usage": self.storage_usage,
            "network_usage": self.network_usage,
            "alert_count": self.alert_count
        }
