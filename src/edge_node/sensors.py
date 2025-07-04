"""
Sensor Management for Edge Nodes
"""

import asyncio
import json
import random
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from abc import ABC, abstractmethod

from ..common.models import SensorData, SensorType, Location
from ..common.logger import get_logger
from ..common.utils import generate_id, get_current_timestamp

logger = get_logger(__name__)


class BaseSensor(ABC):
    """Base class for all sensors"""
    
    def __init__(self, sensor_id: str, sensor_type: SensorType, location: Location, config: Dict[str, Any]):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.location = location
        self.config = config
        self.is_active = False
        self.data_callback = None
        self.read_interval = config.get("read_interval", 1.0)
        self.metadata = config.get("metadata", {})
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the sensor"""
        pass
    
    @abstractmethod
    async def read_data(self) -> Dict[str, Any]:
        """Read data from the sensor"""
        pass
    
    async def start(self) -> None:
        """Start the sensor data collection"""
        self.is_active = True
        asyncio.create_task(self._data_collection_loop())
    
    async def stop(self) -> None:
        """Stop the sensor data collection"""
        self.is_active = False
    
    def set_data_callback(self, callback: Callable) -> None:
        """Set callback for sensor data"""
        self.data_callback = callback
    
    async def _data_collection_loop(self) -> None:
        """Main data collection loop"""
        while self.is_active:
            try:
                # Read sensor data
                raw_data = await self.read_data()
                
                # Create sensor data object
                sensor_data = SensorData(
                    sensor_id=self.sensor_id,
                    sensor_type=self.sensor_type,
                    timestamp=get_current_timestamp(),
                    location=self.location,
                    data=raw_data,
                    metadata=self.metadata
                )
                
                # Call data callback if set
                if self.data_callback:
                    await self.data_callback(sensor_data)
                
                # Wait for next reading
                await asyncio.sleep(self.read_interval)
                
            except Exception as e:
                logger.error(f"Error in sensor {self.sensor_id}: {e}")
                await asyncio.sleep(1)


class CameraSensor(BaseSensor):
    """Camera sensor for video/image data"""
    
    def __init__(self, sensor_id: str, location: Location, config: Dict[str, Any]):
        super().__init__(sensor_id, SensorType.CAMERA, location, config)
        self.camera_id = config.get("camera_id", 0)
        self.resolution = config.get("resolution", (640, 480))
        self.fps = config.get("fps", 30)
    
    async def initialize(self) -> None:
        """Initialize camera sensor"""
        logger.info(f"Initializing camera sensor {self.sensor_id}")
        # In a real implementation, this would initialize the camera
        await asyncio.sleep(0.1)  # Simulate initialization time
    
    async def read_data(self) -> Dict[str, Any]:
        """Read camera data"""
        # In a real implementation, this would capture frames from the camera
        # For now, we'll simulate camera data
        return {
            "image_data": f"mock_image_data_{random.randint(1000, 9999)}",
            "resolution": self.resolution,
            "fps": self.fps,
            "timestamp": get_current_timestamp().isoformat(),
            "camera_id": self.camera_id
        }


class MicrophoneSensor(BaseSensor):
    """Microphone sensor for audio data"""
    
    def __init__(self, sensor_id: str, location: Location, config: Dict[str, Any]):
        super().__init__(sensor_id, SensorType.MICROPHONE, location, config)
        self.sample_rate = config.get("sample_rate", 44100)
        self.channels = config.get("channels", 1)
    
    async def initialize(self) -> None:
        """Initialize microphone sensor"""
        logger.info(f"Initializing microphone sensor {self.sensor_id}")
        await asyncio.sleep(0.1)
    
    async def read_data(self) -> Dict[str, Any]:
        """Read audio data"""
        # Simulate audio data
        audio_level = random.uniform(30, 90)  # dB level
        frequency_data = [random.uniform(0, 1) for _ in range(10)]
        
        return {
            "audio_level": audio_level,
            "frequency_spectrum": frequency_data,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration": 1.0,
            "timestamp": get_current_timestamp().isoformat()
        }


class AirQualitySensor(BaseSensor):
    """Air quality sensor"""
    
    def __init__(self, sensor_id: str, location: Location, config: Dict[str, Any]):
        super().__init__(sensor_id, SensorType.AIR_QUALITY, location, config)
        self.sensor_model = config.get("sensor_model", "generic")
    
    async def initialize(self) -> None:
        """Initialize air quality sensor"""
        logger.info(f"Initializing air quality sensor {self.sensor_id}")
        await asyncio.sleep(0.1)
    
    async def read_data(self) -> Dict[str, Any]:
        """Read air quality data"""
        # Simulate air quality readings
        return {
            "pm25": random.uniform(5, 50),
            "pm10": random.uniform(10, 80),
            "co2": random.uniform(400, 1000),
            "no2": random.uniform(0, 50),
            "o3": random.uniform(0, 100),
            "temperature": random.uniform(15, 35),
            "humidity": random.uniform(30, 90),
            "pressure": random.uniform(950, 1050),
            "timestamp": get_current_timestamp().isoformat()
        }


class MotionSensor(BaseSensor):
    """Motion detection sensor"""
    
    def __init__(self, sensor_id: str, location: Location, config: Dict[str, Any]):
        super().__init__(sensor_id, SensorType.MOTION, location, config)
        self.sensitivity = config.get("sensitivity", 0.5)
    
    async def initialize(self) -> None:
        """Initialize motion sensor"""
        logger.info(f"Initializing motion sensor {self.sensor_id}")
        await asyncio.sleep(0.1)
    
    async def read_data(self) -> Dict[str, Any]:
        """Read motion data"""
        # Simulate motion detection
        motion_detected = random.choice([True, False])
        confidence = random.uniform(0.5, 0.99) if motion_detected else random.uniform(0.0, 0.3)
        
        return {
            "motion_detected": motion_detected,
            "confidence": confidence,
            "sensitivity": self.sensitivity,
            "detection_zones": [
                {
                    "zone_id": "zone_1",
                    "motion": motion_detected,
                    "bbox": [0, 0, 100, 100]
                }
            ],
            "timestamp": get_current_timestamp().isoformat()
        }


class TrafficCounterSensor(BaseSensor):
    """Traffic counter sensor"""
    
    def __init__(self, sensor_id: str, location: Location, config: Dict[str, Any]):
        super().__init__(sensor_id, SensorType.TRAFFIC_COUNTER, location, config)
        self.lanes = config.get("lanes", 2)
    
    async def initialize(self) -> None:
        """Initialize traffic counter sensor"""
        logger.info(f"Initializing traffic counter sensor {self.sensor_id}")
        await asyncio.sleep(0.1)
    
    async def read_data(self) -> Dict[str, Any]:
        """Read traffic counter data"""
        # Simulate traffic counting
        vehicle_count = random.randint(0, 15)
        vehicle_types = {
            "car": random.randint(0, vehicle_count),
            "truck": random.randint(0, max(1, vehicle_count - 10)),
            "motorcycle": random.randint(0, max(1, vehicle_count - 12))
        }
        
        return {
            "count": vehicle_count,
            "types": vehicle_types,
            "speed": random.uniform(20, 80),
            "flow_rate": random.uniform(0, 100),
            "occupancy": random.uniform(0, 1),
            "lanes": self.lanes,
            "timestamp": get_current_timestamp().isoformat()
        }


class NoiseSensor(BaseSensor):
    """Noise level sensor"""
    
    def __init__(self, sensor_id: str, location: Location, config: Dict[str, Any]):
        super().__init__(sensor_id, SensorType.NOISE, location, config)
        self.frequency_range = config.get("frequency_range", (20, 20000))
    
    async def initialize(self) -> None:
        """Initialize noise sensor"""
        logger.info(f"Initializing noise sensor {self.sensor_id}")
        await asyncio.sleep(0.1)
    
    async def read_data(self) -> Dict[str, Any]:
        """Read noise data"""
        # Simulate noise measurements
        return {
            "noise_level": random.uniform(35, 85),  # dB
            "frequency_analysis": {
                "low": random.uniform(0, 1),
                "mid": random.uniform(0, 1),
                "high": random.uniform(0, 1)
            },
            "peak_frequency": random.uniform(100, 5000),
            "frequency_range": self.frequency_range,
            "timestamp": get_current_timestamp().isoformat()
        }


class SensorManager:
    """Manages all sensors for an edge node"""
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.sensors = {}
        self.data_callbacks = []
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize sensor manager"""
        logger.info(f"Initializing sensor manager for node {self.node_id}")
        
        # Create sensors based on configuration
        sensor_configs = self.config.edge_node.sensors
        for sensor_config in sensor_configs:
            await self.add_sensor(sensor_config)
        
        self.is_initialized = True
        logger.info(f"Sensor manager initialized with {len(self.sensors)} sensors")
    
    async def add_sensor(self, sensor_config: Dict[str, Any]) -> None:
        """Add a sensor to the manager"""
        sensor_id = sensor_config.get("sensor_id", generate_id("sensor"))
        sensor_type = sensor_config.get("type", "generic")
        location = Location(
            latitude=sensor_config.get("latitude", 0.0),
            longitude=sensor_config.get("longitude", 0.0),
            address=sensor_config.get("address", "")
        )
        
        # Create sensor based on type
        sensor = self._create_sensor(sensor_id, sensor_type, location, sensor_config)
        
        if sensor:
            # Set data callback
            sensor.set_data_callback(self._on_sensor_data)
            
            # Initialize and start sensor
            await sensor.initialize()
            await sensor.start()
            
            self.sensors[sensor_id] = sensor
            logger.info(f"Added sensor {sensor_id} of type {sensor_type}")
    
    def _create_sensor(self, sensor_id: str, sensor_type: str, location: Location, config: Dict[str, Any]) -> Optional[BaseSensor]:
        """Create a sensor based on its type"""
        sensor_map = {
            "camera": CameraSensor,
            "microphone": MicrophoneSensor,
            "air_quality": AirQualitySensor,
            "motion": MotionSensor,
            "traffic_counter": TrafficCounterSensor,
            "noise": NoiseSensor
        }
        
        sensor_class = sensor_map.get(sensor_type)
        if sensor_class:
            return sensor_class(sensor_id, location, config)
        else:
            logger.warning(f"Unknown sensor type: {sensor_type}")
            return None
    
    async def _on_sensor_data(self, sensor_data: SensorData) -> None:
        """Handle sensor data from individual sensors"""
        # Call all registered callbacks
        for callback in self.data_callbacks:
            try:
                await callback(sensor_data)
            except Exception as e:
                logger.error(f"Error in sensor data callback: {e}")
    
    def on_data(self, callback: Callable) -> None:
        """Register a callback for sensor data"""
        self.data_callbacks.append(callback)
    
    async def get_active_sensors(self) -> List[str]:
        """Get list of active sensor IDs"""
        active_sensors = []
        for sensor_id, sensor in self.sensors.items():
            if sensor.is_active:
                active_sensors.append(sensor_id)
        return active_sensors
    
    async def get_sensor_status(self, sensor_id: str) -> Dict[str, Any]:
        """Get status of a specific sensor"""
        if sensor_id not in self.sensors:
            return {"error": "Sensor not found"}
        
        sensor = self.sensors[sensor_id]
        return {
            "sensor_id": sensor_id,
            "sensor_type": sensor.sensor_type.value,
            "is_active": sensor.is_active,
            "location": sensor.location.to_dict(),
            "read_interval": sensor.read_interval,
            "metadata": sensor.metadata
        }
    
    async def stop_sensor(self, sensor_id: str) -> None:
        """Stop a specific sensor"""
        if sensor_id in self.sensors:
            await self.sensors[sensor_id].stop()
            logger.info(f"Stopped sensor {sensor_id}")
    
    async def start_sensor(self, sensor_id: str) -> None:
        """Start a specific sensor"""
        if sensor_id in self.sensors:
            await self.sensors[sensor_id].start()
            logger.info(f"Started sensor {sensor_id}")
    
    async def shutdown(self) -> None:
        """Shutdown all sensors"""
        logger.info("Shutting down sensor manager")
        
        for sensor_id, sensor in self.sensors.items():
            await sensor.stop()
        
        self.sensors.clear()
        self.data_callbacks.clear()
        self.is_initialized = False
        
        logger.info("Sensor manager shutdown complete")
