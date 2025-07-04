"""
Python wrapper for the high-performance C++ edge processor.
Provides Python bindings for time-critical operations.
"""

import ctypes
import os
import sys
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

class EdgeProcessorWrapper:
    """Python wrapper for the C++ edge processor."""
    
    def __init__(self, lib_path: Optional[str] = None):
        """Initialize the wrapper."""
        self.lib_path = lib_path or self._find_library()
        self.lib = None
        self.load_library()
    
    def _find_library(self) -> str:
        """Find the compiled C++ library."""
        # Look for the library in common locations
        possible_paths = [
            os.path.join(os.path.dirname(__file__), 'edge_processor_lib.so'),
            os.path.join(os.path.dirname(__file__), '..', 'cpp', 'edge_processor_lib.so'),
            os.path.join(os.path.dirname(__file__), '..', 'build', 'edge_processor_lib.so'),
            '/usr/local/lib/edge_processor_lib.so',
            './edge_processor_lib.so'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError("Could not find edge_processor_lib.so")
    
    def load_library(self):
        """Load the C++ library."""
        try:
            self.lib = ctypes.CDLL(self.lib_path)
            self._setup_function_signatures()
            logger.info(f"Loaded C++ library from {self.lib_path}")
        except Exception as e:
            logger.error(f"Failed to load C++ library: {e}")
            raise
    
    def _setup_function_signatures(self):
        """Setup function signatures for C++ functions."""
        # Process traffic data
        self.lib.process_traffic_data.argtypes = [
            ctypes.POINTER(ctypes.c_float),  # image data
            ctypes.c_int,                    # width
            ctypes.c_int,                    # height
            ctypes.c_int,                    # channels
            ctypes.POINTER(ctypes.c_char_p)  # result JSON
        ]
        self.lib.process_traffic_data.restype = ctypes.c_int
        
        # Process audio data
        self.lib.process_audio_data.argtypes = [
            ctypes.POINTER(ctypes.c_float),  # audio data
            ctypes.c_int,                    # sample count
            ctypes.c_int,                    # sample rate
            ctypes.POINTER(ctypes.c_char_p)  # result JSON
        ]
        self.lib.process_audio_data.restype = ctypes.c_int
        
        # Process environmental data
        self.lib.process_environmental_data.argtypes = [
            ctypes.POINTER(ctypes.c_float),  # sensor data
            ctypes.c_int,                    # sensor count
            ctypes.POINTER(ctypes.c_char_p)  # result JSON
        ]
        self.lib.process_environmental_data.restype = ctypes.c_int
        
        # Initialize processor
        self.lib.initialize_processor.argtypes = [ctypes.c_char_p]  # config JSON
        self.lib.initialize_processor.restype = ctypes.c_int
        
        # Cleanup
        self.lib.cleanup_processor.argtypes = []
        self.lib.cleanup_processor.restype = None
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the C++ processor."""
        try:
            import json
            config_json = json.dumps(config).encode('utf-8')
            result = self.lib.initialize_processor(config_json)
            return result == 0
        except Exception as e:
            logger.error(f"Failed to initialize processor: {e}")
            return False
    
    def process_traffic_data(self, image_data: np.ndarray) -> Dict[str, Any]:
        """Process traffic data using C++ implementation."""
        try:
            # Ensure image data is float32
            if image_data.dtype != np.float32:
                image_data = image_data.astype(np.float32)
            
            # Get image dimensions
            height, width, channels = image_data.shape
            
            # Flatten image data
            image_flat = image_data.flatten()
            
            # Create pointer to image data
            image_ptr = (ctypes.c_float * len(image_flat))(*image_flat)
            
            # Create result buffer
            result_ptr = ctypes.c_char_p()
            
            # Call C++ function
            success = self.lib.process_traffic_data(
                image_ptr, width, height, channels, ctypes.byref(result_ptr)
            )
            
            if success == 0 and result_ptr.value:
                import json
                result_json = result_ptr.value.decode('utf-8')
                return json.loads(result_json)
            else:
                return {'error': 'Processing failed'}
                
        except Exception as e:
            logger.error(f"Error processing traffic data: {e}")
            return {'error': str(e)}
    
    def process_audio_data(self, audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """Process audio data using C++ implementation."""
        try:
            # Ensure audio data is float32
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Flatten audio data if needed
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            # Create pointer to audio data
            audio_ptr = (ctypes.c_float * len(audio_data))(*audio_data)
            
            # Create result buffer
            result_ptr = ctypes.c_char_p()
            
            # Call C++ function
            success = self.lib.process_audio_data(
                audio_ptr, len(audio_data), sample_rate, ctypes.byref(result_ptr)
            )
            
            if success == 0 and result_ptr.value:
                import json
                result_json = result_ptr.value.decode('utf-8')
                return json.loads(result_json)
            else:
                return {'error': 'Processing failed'}
                
        except Exception as e:
            logger.error(f"Error processing audio data: {e}")
            return {'error': str(e)}
    
    def process_environmental_data(self, sensor_data: List[float]) -> Dict[str, Any]:
        """Process environmental data using C++ implementation."""
        try:
            # Convert to float32 array
            sensor_array = np.array(sensor_data, dtype=np.float32)
            
            # Create pointer to sensor data
            sensor_ptr = (ctypes.c_float * len(sensor_array))(*sensor_array)
            
            # Create result buffer
            result_ptr = ctypes.c_char_p()
            
            # Call C++ function
            success = self.lib.process_environmental_data(
                sensor_ptr, len(sensor_array), ctypes.byref(result_ptr)
            )
            
            if success == 0 and result_ptr.value:
                import json
                result_json = result_ptr.value.decode('utf-8')
                return json.loads(result_json)
            else:
                return {'error': 'Processing failed'}
                
        except Exception as e:
            logger.error(f"Error processing environmental data: {e}")
            return {'error': str(e)}
    
    def cleanup(self):
        """Clean up resources."""
        if self.lib:
            self.lib.cleanup_processor()
    
    def __del__(self):
        """Destructor."""
        self.cleanup()


# Global instance for easy access
_edge_processor = None

def get_edge_processor(lib_path: Optional[str] = None) -> EdgeProcessorWrapper:
    """Get the global edge processor instance."""
    global _edge_processor
    if _edge_processor is None:
        _edge_processor = EdgeProcessorWrapper(lib_path)
    return _edge_processor

def initialize_edge_processor(config: Dict[str, Any], lib_path: Optional[str] = None) -> bool:
    """Initialize the edge processor."""
    processor = get_edge_processor(lib_path)
    return processor.initialize(config)

def process_traffic_data_cpp(image_data: np.ndarray) -> Dict[str, Any]:
    """Process traffic data using C++ (convenience function)."""
    processor = get_edge_processor()
    return processor.process_traffic_data(image_data)

def process_audio_data_cpp(audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
    """Process audio data using C++ (convenience function)."""
    processor = get_edge_processor()
    return processor.process_audio_data(audio_data, sample_rate)

def process_environmental_data_cpp(sensor_data: List[float]) -> Dict[str, Any]:
    """Process environmental data using C++ (convenience function)."""
    processor = get_edge_processor()
    return processor.process_environmental_data(sensor_data)

def cleanup_edge_processor():
    """Clean up the edge processor."""
    global _edge_processor
    if _edge_processor:
        _edge_processor.cleanup()
        _edge_processor = None


# Mock implementation for when C++ library is not available
class MockEdgeProcessor:
    """Mock edge processor for development/testing."""
    
    def __init__(self, lib_path: Optional[str] = None):
        logger.warning("Using mock edge processor - C++ library not available")
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        logger.info("Mock processor initialized")
        return True
    
    def process_traffic_data(self, image_data: np.ndarray) -> Dict[str, Any]:
        """Mock traffic processing."""
        import random
        return {
            'vehicle_count': random.randint(0, 20),
            'average_speed': random.uniform(20, 60),
            'congestion_level': random.choice(['low', 'medium', 'high']),
            'processing_time_ms': random.uniform(10, 50)
        }
    
    def process_audio_data(self, audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """Mock audio processing."""
        import random
        return {
            'sound_level': random.uniform(30, 90),
            'dominant_frequency': random.uniform(100, 8000),
            'anomaly_detected': random.choice([True, False]),
            'processing_time_ms': random.uniform(5, 20)
        }
    
    def process_environmental_data(self, sensor_data: List[float]) -> Dict[str, Any]:
        """Mock environmental processing."""
        import random
        return {
            'processed_values': [v * random.uniform(0.9, 1.1) for v in sensor_data],
            'anomalies': [],
            'quality_score': random.uniform(0.7, 1.0),
            'processing_time_ms': random.uniform(1, 5)
        }
    
    def cleanup(self):
        """Mock cleanup."""
        pass


# Try to use real processor, fall back to mock
try:
    EdgeProcessorWrapper()
except (FileNotFoundError, OSError):
    # Use mock implementation
    EdgeProcessorWrapper = MockEdgeProcessor
    logger.info("Using mock edge processor implementation")
