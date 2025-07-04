"""
Utility functions for the distributed edge AI network
"""

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import asyncio
import socket
import psutil


def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Unique ID string
    """
    unique_id = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id


def get_current_timestamp() -> datetime:
    """Get current timestamp with timezone"""
    return datetime.now(timezone.utc)


def serialize_data(data: Any) -> str:
    """
    Serialize data to JSON string
    
    Args:
        data: Data to serialize
        
    Returns:
        JSON string
    """
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    return json.dumps(data, default=json_serializer, separators=(',', ':'))


def deserialize_data(data_str: str) -> Any:
    """
    Deserialize JSON string to data
    
    Args:
        data_str: JSON string
        
    Returns:
        Deserialized data
    """
    return json.loads(data_str)


def hash_data(data: Union[str, bytes]) -> str:
    """
    Generate SHA-256 hash of data
    
    Args:
        data: Data to hash
        
    Returns:
        Hash string
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two geographic points using Haversine formula
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        
    Returns:
        Distance in kilometers
    """
    import math
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


def get_system_metrics() -> Dict[str, Any]:
    """
    Get current system metrics
    
    Returns:
        Dictionary of system metrics
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    network = psutil.net_io_counters()
    
    return {
        "cpu_usage": cpu_percent,
        "memory_usage": memory.percent,
        "memory_available": memory.available,
        "disk_usage": disk.percent,
        "disk_free": disk.free,
        "network_bytes_sent": network.bytes_sent,
        "network_bytes_recv": network.bytes_recv,
        "timestamp": get_current_timestamp().isoformat()
    }


def get_local_ip() -> str:
    """
    Get local IP address
    
    Returns:
        Local IP address
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate geographic coordinates
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        True if coordinates are valid
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180


def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """
    Calculate exponential backoff delay
    
    Args:
        attempt: Attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Delay in seconds
    """
    delay = base_delay * (2 ** attempt)
    return min(delay, max_delay)


async def retry_async(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    Retry an async function with exponential backoff
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retries
        base_delay: Base delay between retries
        exceptions: Exceptions to catch and retry on
        
    Returns:
        Function result
    """
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except exceptions as e:
            if attempt == max_retries:
                raise e
            
            delay = exponential_backoff(attempt, base_delay)
            await asyncio.sleep(delay)


def sliding_window_average(values: List[float], window_size: int) -> List[float]:
    """
    Calculate sliding window average
    
    Args:
        values: List of values
        window_size: Size of the sliding window
        
    Returns:
        List of averaged values
    """
    if len(values) < window_size:
        return values
    
    averages = []
    for i in range(len(values) - window_size + 1):
        window = values[i:i + window_size]
        averages.append(sum(window) / len(window))
    
    return averages


def detect_anomaly(values: List[float], threshold: float = 2.0) -> List[bool]:
    """
    Detect anomalies using z-score
    
    Args:
        values: List of values
        threshold: Z-score threshold
        
    Returns:
        List of boolean values indicating anomalies
    """
    if len(values) < 2:
        return [False] * len(values)
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std_dev = variance ** 0.5
    
    if std_dev == 0:
        return [False] * len(values)
    
    anomalies = []
    for value in values:
        z_score = abs(value - mean) / std_dev
        anomalies.append(z_score > threshold)
    
    return anomalies


def normalize_data(data: List[float], min_val: float = 0.0, max_val: float = 1.0) -> List[float]:
    """
    Normalize data to a specific range
    
    Args:
        data: List of values to normalize
        min_val: Minimum value of the range
        max_val: Maximum value of the range
        
    Returns:
        Normalized data
    """
    if not data:
        return []
    
    data_min = min(data)
    data_max = max(data)
    
    if data_max == data_min:
        return [min_val] * len(data)
    
    normalized = []
    for value in data:
        normalized_value = (value - data_min) / (data_max - data_min)
        normalized_value = normalized_value * (max_val - min_val) + min_val
        normalized.append(normalized_value)
    
    return normalized


class RateLimiter:
    """Simple rate limiter implementation"""
    
    def __init__(self, max_requests: int, time_window: float):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def is_allowed(self) -> bool:
        """Check if request is allowed"""
        current_time = time.time()
        
        # Remove old requests
        self.requests = [req_time for req_time in self.requests 
                        if current_time - req_time < self.time_window]
        
        # Check if we can make a new request
        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            return True
        
        return False


class CircularBuffer:
    """Circular buffer for storing recent values"""
    
    def __init__(self, size: int):
        self.size = size
        self.buffer = [None] * size
        self.index = 0
        self.count = 0
    
    def append(self, value: Any) -> None:
        """Add value to buffer"""
        self.buffer[self.index] = value
        self.index = (self.index + 1) % self.size
        self.count = min(self.count + 1, self.size)
    
    def get_values(self) -> List[Any]:
        """Get all values in insertion order"""
        if self.count == 0:
            return []
        
        if self.count < self.size:
            return self.buffer[:self.count]
        
        return self.buffer[self.index:] + self.buffer[:self.index]
    
    def get_latest(self, n: int = 1) -> List[Any]:
        """Get the n most recent values"""
        values = self.get_values()
        return values[-n:] if values else []
