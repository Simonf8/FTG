"""
Data processing and analytics for the central coordinator.
Handles data aggregation, analysis, and machine learning pipelines.
"""
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import threading
import time
from dataclasses import dataclass

from ..common.logger import setup_logger
from ..common.models import Alert, NodeStatus, EdgeNode, MetricsData

logger = setup_logger(__name__)

@dataclass
class ProcessingPipeline:
    """Data processing pipeline configuration."""
    name: str
    input_types: List[str]
    processors: List[str]
    output_handlers: List[str]
    enabled: bool = True

class DataProcessor:
    """Central data processing and analytics engine."""
    
    def __init__(self, coordinator_core):
        self.coordinator = coordinator_core
        self.processing_queue = asyncio.Queue()
        self.processed_data = defaultdict(deque)
        self.analytics_cache = {}
        self.pipelines = {}
        self.metrics = {
            'processed_messages': 0,
            'processing_errors': 0,
            'avg_processing_time': 0.0,
            'data_types': defaultdict(int)
        }
        self.setup_pipelines()
        self.start_processing_threads()
    
    def setup_pipelines(self):
        """Setup data processing pipelines."""
        self.pipelines = {
            'traffic_analysis': ProcessingPipeline(
                name='traffic_analysis',
                input_types=['traffic_data'],
                processors=['traffic_aggregator', 'congestion_detector', 'flow_analyzer'],
                output_handlers=['traffic_alert_generator', 'traffic_metrics_updater']
            ),
            'environmental_monitoring': ProcessingPipeline(
                name='environmental_monitoring',
                input_types=['environmental_data'],
                processors=['air_quality_analyzer', 'noise_level_processor', 'weather_aggregator'],
                output_handlers=['environmental_alert_generator', 'trend_analyzer']
            ),
            'crime_detection': ProcessingPipeline(
                name='crime_detection',
                input_types=['crime_data', 'audio_data', 'video_data'],
                processors=['incident_classifier', 'threat_analyzer', 'pattern_detector'],
                output_handlers=['security_alert_generator', 'patrol_dispatcher']
            ),
            'system_monitoring': ProcessingPipeline(
                name='system_monitoring',
                input_types=['system_metrics', 'node_status'],
                processors=['health_checker', 'performance_analyzer', 'resource_monitor'],
                output_handlers=['system_alert_generator', 'optimization_recommender']
            )
        }
    
    def start_processing_threads(self):
        """Start background processing threads."""
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        self.analytics_thread = threading.Thread(target=self._analytics_loop, daemon=True)
        self.analytics_thread.start()
    
    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming data through appropriate pipelines."""
        try:
            start_time = time.time()
            
            # Determine data type
            data_type = self._determine_data_type(data)
            self.metrics['data_types'][data_type] += 1
            
            # Find appropriate pipeline
            pipeline = self._get_pipeline_for_data_type(data_type)
            if not pipeline:
                logger.warning(f"No pipeline found for data type: {data_type}")
                return {'error': f'No pipeline for data type: {data_type}'}
            
            # Process through pipeline
            result = await self._process_through_pipeline(data, pipeline)
            
            # Update metrics
            processing_time = time.time() - start_time
            self.metrics['processed_messages'] += 1
            self.metrics['avg_processing_time'] = (
                (self.metrics['avg_processing_time'] * (self.metrics['processed_messages'] - 1) + processing_time) /
                self.metrics['processed_messages']
            )
            
            # Store processed data
            self._store_processed_data(data_type, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            self.metrics['processing_errors'] += 1
            return {'error': str(e)}
    
    def _determine_data_type(self, data: Dict[str, Any]) -> str:
        """Determine the type of incoming data."""
        if 'vehicle_count' in data or 'traffic_flow' in data:
            return 'traffic_data'
        elif 'air_quality' in data or 'temperature' in data or 'noise_level' in data:
            return 'environmental_data'
        elif 'incident_type' in data or 'threat_level' in data:
            return 'crime_data'
        elif 'cpu_usage' in data or 'memory_usage' in data:
            return 'system_metrics'
        elif 'node_id' in data and 'status' in data:
            return 'node_status'
        else:
            return 'unknown'
    
    def _get_pipeline_for_data_type(self, data_type: str) -> Optional[ProcessingPipeline]:
        """Get the appropriate pipeline for a data type."""
        for pipeline in self.pipelines.values():
            if data_type in pipeline.input_types and pipeline.enabled:
                return pipeline
        return None
    
    async def _process_through_pipeline(self, data: Dict[str, Any], pipeline: ProcessingPipeline) -> Dict[str, Any]:
        """Process data through a specific pipeline."""
        result = data.copy()
        
        for processor in pipeline.processors:
            result = await self._apply_processor(result, processor)
        
        # Apply output handlers
        for handler in pipeline.output_handlers:
            await self._apply_output_handler(result, handler)
        
        return result
    
    async def _apply_processor(self, data: Dict[str, Any], processor: str) -> Dict[str, Any]:
        """Apply a specific processor to the data."""
        if processor == 'traffic_aggregator':
            return self._process_traffic_aggregation(data)
        elif processor == 'congestion_detector':
            return self._process_congestion_detection(data)
        elif processor == 'flow_analyzer':
            return self._process_flow_analysis(data)
        elif processor == 'air_quality_analyzer':
            return self._process_air_quality_analysis(data)
        elif processor == 'noise_level_processor':
            return self._process_noise_level_analysis(data)
        elif processor == 'weather_aggregator':
            return self._process_weather_aggregation(data)
        elif processor == 'incident_classifier':
            return self._process_incident_classification(data)
        elif processor == 'threat_analyzer':
            return self._process_threat_analysis(data)
        elif processor == 'pattern_detector':
            return self._process_pattern_detection(data)
        elif processor == 'health_checker':
            return self._process_health_check(data)
        elif processor == 'performance_analyzer':
            return self._process_performance_analysis(data)
        elif processor == 'resource_monitor':
            return self._process_resource_monitoring(data)
        else:
            logger.warning(f"Unknown processor: {processor}")
            return data
    
    async def _apply_output_handler(self, data: Dict[str, Any], handler: str):
        """Apply output handler to processed data."""
        if handler == 'traffic_alert_generator':
            await self._generate_traffic_alerts(data)
        elif handler == 'traffic_metrics_updater':
            await self._update_traffic_metrics(data)
        elif handler == 'environmental_alert_generator':
            await self._generate_environmental_alerts(data)
        elif handler == 'trend_analyzer':
            await self._analyze_trends(data)
        elif handler == 'security_alert_generator':
            await self._generate_security_alerts(data)
        elif handler == 'patrol_dispatcher':
            await self._dispatch_patrol(data)
        elif handler == 'system_alert_generator':
            await self._generate_system_alerts(data)
        elif handler == 'optimization_recommender':
            await self._recommend_optimizations(data)
    
    def _process_traffic_aggregation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process traffic data aggregation."""
        result = data.copy()
        
        # Aggregate vehicle counts
        if 'vehicle_count' in data:
            result['processed_vehicle_count'] = data['vehicle_count']
            result['traffic_density'] = self._calculate_traffic_density(data)
        
        # Calculate average speed
        if 'vehicle_speeds' in data:
            result['average_speed'] = statistics.mean(data['vehicle_speeds'])
            result['speed_variance'] = statistics.variance(data['vehicle_speeds'])
        
        # Detect congestion
        result['congestion_level'] = self._detect_congestion_level(data)
        
        return result
    
    def _process_congestion_detection(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process congestion detection."""
        result = data.copy()
        
        # Calculate congestion score
        congestion_score = 0
        if 'vehicle_count' in data and 'road_capacity' in data:
            congestion_score = min(data['vehicle_count'] / data['road_capacity'], 1.0)
        
        result['congestion_score'] = congestion_score
        result['congestion_category'] = self._categorize_congestion(congestion_score)
        
        return result
    
    def _process_flow_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process traffic flow analysis."""
        result = data.copy()
        
        # Analyze flow patterns
        if 'vehicle_directions' in data:
            result['flow_balance'] = self._analyze_flow_balance(data['vehicle_directions'])
        
        # Predict flow changes
        result['flow_prediction'] = self._predict_flow_changes(data)
        
        return result
    
    def _process_air_quality_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process air quality analysis."""
        result = data.copy()
        
        # Calculate air quality index
        if 'pollutants' in data:
            result['air_quality_index'] = self._calculate_air_quality_index(data['pollutants'])
            result['health_category'] = self._categorize_health_risk(result['air_quality_index'])
        
        return result
    
    def _process_noise_level_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process noise level analysis."""
        result = data.copy()
        
        # Analyze noise levels
        if 'noise_level' in data:
            result['noise_category'] = self._categorize_noise_level(data['noise_level'])
            result['noise_trend'] = self._analyze_noise_trend(data)
        
        return result
    
    def _process_weather_aggregation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process weather data aggregation."""
        result = data.copy()
        
        # Aggregate weather data
        if 'temperature' in data and 'humidity' in data:
            result['heat_index'] = self._calculate_heat_index(data['temperature'], data['humidity'])
            result['comfort_level'] = self._calculate_comfort_level(result['heat_index'])
        
        return result
    
    def _process_incident_classification(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incident classification."""
        result = data.copy()
        
        # Classify incident type
        if 'incident_data' in data:
            result['incident_classification'] = self._classify_incident(data['incident_data'])
            result['severity_level'] = self._assess_incident_severity(result['incident_classification'])
        
        return result
    
    def _process_threat_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process threat analysis."""
        result = data.copy()
        
        # Analyze threat level
        if 'threat_indicators' in data:
            result['threat_score'] = self._calculate_threat_score(data['threat_indicators'])
            result['threat_category'] = self._categorize_threat(result['threat_score'])
        
        return result
    
    def _process_pattern_detection(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process pattern detection."""
        result = data.copy()
        
        # Detect patterns
        result['patterns'] = self._detect_patterns(data)
        result['anomalies'] = self._detect_anomalies(data)
        
        return result
    
    def _process_health_check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process system health check."""
        result = data.copy()
        
        # Check system health
        if 'cpu_usage' in data and 'memory_usage' in data:
            result['health_score'] = self._calculate_health_score(data)
            result['health_status'] = self._determine_health_status(result['health_score'])
        
        return result
    
    def _process_performance_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process performance analysis."""
        result = data.copy()
        
        # Analyze performance metrics
        result['performance_score'] = self._calculate_performance_score(data)
        result['bottlenecks'] = self._identify_bottlenecks(data)
        
        return result
    
    def _process_resource_monitoring(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process resource monitoring."""
        result = data.copy()
        
        # Monitor resource usage
        result['resource_utilization'] = self._calculate_resource_utilization(data)
        result['resource_alerts'] = self._check_resource_thresholds(data)
        
        return result
    
    # Alert generation methods
    async def _generate_traffic_alerts(self, data: Dict[str, Any]):
        """Generate traffic-related alerts."""
        if data.get('congestion_level') == 'high':
            alert = Alert(
                alert_id=f"traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                alert_type='traffic_congestion',
                severity='medium',
                message=f"High traffic congestion detected at {data.get('location', 'unknown location')}",
                source_node=data.get('node_id'),
                data=data
            )
            await self.coordinator.add_alert(alert)
    
    async def _generate_environmental_alerts(self, data: Dict[str, Any]):
        """Generate environmental alerts."""
        if data.get('air_quality_index', 0) > 150:  # Unhealthy air quality
            alert = Alert(
                alert_id=f"env_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                alert_type='air_quality',
                severity='high',
                message=f"Poor air quality detected: AQI {data.get('air_quality_index')}",
                source_node=data.get('node_id'),
                data=data
            )
            await self.coordinator.add_alert(alert)
    
    async def _generate_security_alerts(self, data: Dict[str, Any]):
        """Generate security alerts."""
        if data.get('threat_score', 0) > 0.8:  # High threat score
            alert = Alert(
                alert_id=f"security_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                alert_type='security_threat',
                severity='critical',
                message=f"Security threat detected: {data.get('threat_category', 'unknown')}",
                source_node=data.get('node_id'),
                data=data
            )
            await self.coordinator.add_alert(alert)
    
    async def _generate_system_alerts(self, data: Dict[str, Any]):
        """Generate system alerts."""
        if data.get('health_score', 1.0) < 0.5:  # Poor system health
            alert = Alert(
                alert_id=f"system_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                alert_type='system_health',
                severity='high',
                message=f"System health degraded: {data.get('health_status', 'unknown')}",
                source_node=data.get('node_id'),
                data=data
            )
            await self.coordinator.add_alert(alert)
    
    # Utility methods (simplified implementations)
    def _calculate_traffic_density(self, data: Dict[str, Any]) -> float:
        """Calculate traffic density."""
        return data.get('vehicle_count', 0) / data.get('road_length', 1)
    
    def _detect_congestion_level(self, data: Dict[str, Any]) -> str:
        """Detect congestion level."""
        density = self._calculate_traffic_density(data)
        if density > 50:
            return 'high'
        elif density > 25:
            return 'medium'
        else:
            return 'low'
    
    def _categorize_congestion(self, score: float) -> str:
        """Categorize congestion level."""
        if score > 0.8:
            return 'severe'
        elif score > 0.6:
            return 'heavy'
        elif score > 0.4:
            return 'moderate'
        else:
            return 'light'
    
    def _calculate_air_quality_index(self, pollutants: Dict[str, float]) -> float:
        """Calculate air quality index."""
        # Simplified AQI calculation
        pm25 = pollutants.get('pm2.5', 0)
        pm10 = pollutants.get('pm10', 0)
        o3 = pollutants.get('o3', 0)
        
        return max(pm25 * 2, pm10 * 1.5, o3 * 3)
    
    def _categorize_health_risk(self, aqi: float) -> str:
        """Categorize health risk based on AQI."""
        if aqi > 300:
            return 'hazardous'
        elif aqi > 200:
            return 'very_unhealthy'
        elif aqi > 150:
            return 'unhealthy'
        elif aqi > 100:
            return 'unhealthy_for_sensitive'
        elif aqi > 50:
            return 'moderate'
        else:
            return 'good'
    
    def _calculate_health_score(self, data: Dict[str, Any]) -> float:
        """Calculate system health score."""
        cpu_score = 1.0 - (data.get('cpu_usage', 0) / 100)
        memory_score = 1.0 - (data.get('memory_usage', 0) / 100)
        return (cpu_score + memory_score) / 2
    
    def _determine_health_status(self, score: float) -> str:
        """Determine health status from score."""
        if score > 0.8:
            return 'excellent'
        elif score > 0.6:
            return 'good'
        elif score > 0.4:
            return 'fair'
        else:
            return 'poor'
    
    def _store_processed_data(self, data_type: str, data: Dict[str, Any]):
        """Store processed data for analytics."""
        self.processed_data[data_type].append({
            'timestamp': datetime.now(),
            'data': data
        })
        
        # Keep only last 1000 records per type
        if len(self.processed_data[data_type]) > 1000:
            self.processed_data[data_type].popleft()
    
    def _processing_loop(self):
        """Main processing loop."""
        while True:
            try:
                # Process any queued data
                # This would be implemented with actual queue processing
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(5)
    
    def _analytics_loop(self):
        """Analytics processing loop."""
        while True:
            try:
                # Run analytics on processed data
                self._run_analytics()
                time.sleep(60)  # Run analytics every minute
            except Exception as e:
                logger.error(f"Error in analytics loop: {e}")
                time.sleep(60)
    
    def _run_analytics(self):
        """Run analytics on processed data."""
        # Implement analytics logic
        pass
    
    def get_processing_metrics(self) -> Dict[str, Any]:
        """Get processing metrics."""
        return self.metrics.copy()
    
    def get_processed_data(self, data_type: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get processed data for a specific type and time range."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        if data_type not in self.processed_data:
            return []
        
        return [
            item for item in self.processed_data[data_type]
            if item['timestamp'] >= cutoff_time
        ]
