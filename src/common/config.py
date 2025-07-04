"""
Configuration management for the distributed edge AI network
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    username: str = "edge_ai"
    password: str = "password"
    database: str = "edge_network"


@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


@dataclass
class MQTTConfig:
    """MQTT broker configuration"""
    host: str = "localhost"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    topics: Dict[str, str] = field(default_factory=lambda: {
        "sensors": "sensors/+/data",
        "alerts": "alerts/+",
        "commands": "commands/+",
        "status": "status/+"
    })


@dataclass
class AIModelConfig:
    """AI model configuration"""
    model_path: str = "models/"
    traffic_model: str = "traffic_yolo_v5.pt"
    crime_model: str = "crime_detection_v2.pt"
    environment_model: str = "env_lstm_v1.pt"
    update_interval: int = 3600  # seconds
    confidence_threshold: float = 0.7


@dataclass
class EdgeNodeConfig:
    """Edge node configuration"""
    node_id: str = "edge_node_01"
    node_type: str = "traffic"  # traffic, crime, environment
    location: Dict[str, float] = field(default_factory=lambda: {"lat": 0.0, "lon": 0.0})
    sensors: List[str] = field(default_factory=list)
    processing_interval: int = 1  # seconds
    max_local_storage: int = 1000  # MB
    heartbeat_interval: int = 30  # seconds


@dataclass
class CoordinatorConfig:
    """Central coordinator configuration"""
    host: str = "0.0.0.0"
    port: int = 8080
    max_connections: int = 1000
    data_retention_days: int = 30
    alert_thresholds: Dict[str, Any] = field(default_factory=lambda: {
        "traffic_congestion": 0.8,
        "crime_probability": 0.6,
        "air_quality_index": 150,
        "noise_level": 70
    })


@dataclass
class Config:
    """Main configuration class"""
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    ai_models: AIModelConfig = field(default_factory=AIModelConfig)
    edge_node: EdgeNodeConfig = field(default_factory=EdgeNodeConfig)
    coordinator: CoordinatorConfig = field(default_factory=CoordinatorConfig)
    
    # Security settings
    secret_key: str = "your-secret-key-here"
    jwt_expire_hours: int = 24
    encrypt_data: bool = True
    
    # Performance settings
    max_workers: int = 4
    queue_size: int = 1000
    timeout_seconds: int = 30


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Config object
    """
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", "config/config.yaml")
    
    config_file = Path(config_path)
    
    if not config_file.exists():
        # Create default config if it doesn't exist
        default_config = Config()
        save_config(default_config, config_path)
        return default_config
    
    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Convert nested dictionaries to dataclass objects
        config = Config()
        
        if 'database' in config_data:
            config.database = DatabaseConfig(**config_data['database'])
        
        if 'redis' in config_data:
            config.redis = RedisConfig(**config_data['redis'])
        
        if 'mqtt' in config_data:
            config.mqtt = MQTTConfig(**config_data['mqtt'])
        
        if 'ai_models' in config_data:
            config.ai_models = AIModelConfig(**config_data['ai_models'])
        
        if 'edge_node' in config_data:
            config.edge_node = EdgeNodeConfig(**config_data['edge_node'])
        
        if 'coordinator' in config_data:
            config.coordinator = CoordinatorConfig(**config_data['coordinator'])
        
        # Update top-level fields
        for key, value in config_data.items():
            if hasattr(config, key) and key not in ['database', 'redis', 'mqtt', 'ai_models', 'edge_node', 'coordinator']:
                setattr(config, key, value)
        
        return config
        
    except Exception as e:
        print(f"Error loading config: {e}")
        return Config()


def save_config(config: Config, config_path: str) -> None:
    """
    Save configuration to YAML file
    
    Args:
        config: Config object to save
        config_path: Path to save configuration file
    """
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert dataclass to dictionary
    config_dict = {
        'environment': config.environment,
        'debug': config.debug,
        'log_level': config.log_level,
        'secret_key': config.secret_key,
        'jwt_expire_hours': config.jwt_expire_hours,
        'encrypt_data': config.encrypt_data,
        'max_workers': config.max_workers,
        'queue_size': config.queue_size,
        'timeout_seconds': config.timeout_seconds,
        'database': {
            'host': config.database.host,
            'port': config.database.port,
            'username': config.database.username,
            'password': config.database.password,
            'database': config.database.database
        },
        'redis': {
            'host': config.redis.host,
            'port': config.redis.port,
            'db': config.redis.db,
            'password': config.redis.password
        },
        'mqtt': {
            'host': config.mqtt.host,
            'port': config.mqtt.port,
            'username': config.mqtt.username,
            'password': config.mqtt.password,
            'topics': config.mqtt.topics
        },
        'ai_models': {
            'model_path': config.ai_models.model_path,
            'traffic_model': config.ai_models.traffic_model,
            'crime_model': config.ai_models.crime_model,
            'environment_model': config.ai_models.environment_model,
            'update_interval': config.ai_models.update_interval,
            'confidence_threshold': config.ai_models.confidence_threshold
        },
        'edge_node': {
            'node_id': config.edge_node.node_id,
            'node_type': config.edge_node.node_type,
            'location': config.edge_node.location,
            'sensors': config.edge_node.sensors,
            'processing_interval': config.edge_node.processing_interval,
            'max_local_storage': config.edge_node.max_local_storage,
            'heartbeat_interval': config.edge_node.heartbeat_interval
        },
        'coordinator': {
            'host': config.coordinator.host,
            'port': config.coordinator.port,
            'max_connections': config.coordinator.max_connections,
            'data_retention_days': config.coordinator.data_retention_days,
            'alert_thresholds': config.coordinator.alert_thresholds
        }
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, indent=2)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance"""
    global _config
    _config = config
