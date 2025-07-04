"""
Base Edge Node Implementation
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from ..common.models import (
    NodeType, SensorData, EdgeNodeStatus, ProcessingJob, 
    ProcessingStatus, Location, Alert
)
from ..common.config import get_config
from ..common.logger import get_logger
from ..common.utils import generate_id, get_current_timestamp, get_system_metrics

logger = get_logger(__name__)


class BaseEdgeNode:
    """
    Base Edge Node class that handles local processing and communication
    """
    
    def __init__(
        self,
        node_id: str,
        node_type: NodeType,
        location: Location,
        config: Optional[Dict[str, Any]] = None
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.location = location
        self.config = config or get_config()
        
        # Initialize components
        self.sensor_manager = None
        self.communication_manager = None
        self.storage = None
        self.ai_processors = {}
        
        # Runtime state
        self.status = "offline"
        self.last_heartbeat = get_current_timestamp()
        self.processing_queue = asyncio.Queue()
        self.metrics = {
            "messages_processed": 0,
            "alerts_generated": 0,
            "processing_time_avg": 0.0,
            "error_count": 0
        }
        
        # Tasks
        self.background_tasks = []
        self.shutdown_event = asyncio.Event()
        
        logger.info(f"Initialized {node_type.value} edge node: {node_id}")
    
    async def initialize(self) -> None:
        """Initialize the edge node and its components"""
        try:
            logger.info(f"Initializing edge node {self.node_id}")
            
            # Initialize storage
            await self._initialize_storage()
            
            # Initialize communication
            await self._initialize_communication()
            
            # Initialize sensors
            await self._initialize_sensors()
            
            # Initialize AI processors
            await self._initialize_ai_processors()
            
            # Start background tasks
            await self._start_background_tasks()
            
            self.status = "online"
            logger.info(f"Edge node {self.node_id} initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize edge node {self.node_id}: {e}")
            self.status = "error"
            raise
    
    async def _initialize_storage(self) -> None:
        """Initialize local storage"""
        from .storage import LocalStorage
        self.storage = LocalStorage(self.node_id)
        await self.storage.initialize()
    
    async def _initialize_communication(self) -> None:
        """Initialize communication manager"""
        from .communication import CommunicationManager
        self.communication_manager = CommunicationManager(self.node_id, self.config)
        await self.communication_manager.initialize()
        
        # Set up message handlers
        self.communication_manager.on_message(self._handle_incoming_message)
        self.communication_manager.on_command(self._handle_command)
    
    async def _initialize_sensors(self) -> None:
        """Initialize sensor manager"""
        from .sensors import SensorManager
        self.sensor_manager = SensorManager(self.node_id, self.config)
        await self.sensor_manager.initialize()
        
        # Set up sensor data handler
        self.sensor_manager.on_data(self._handle_sensor_data)
    
    async def _initialize_ai_processors(self) -> None:
        """Initialize AI processors based on node type"""
        from .ai_processors import TrafficProcessor, CrimeProcessor, EnvironmentProcessor
        
        if self.node_type == NodeType.TRAFFIC:
            self.ai_processors['traffic'] = TrafficProcessor(self.config)
        elif self.node_type == NodeType.CRIME:
            self.ai_processors['crime'] = CrimeProcessor(self.config)
        elif self.node_type == NodeType.ENVIRONMENT:
            self.ai_processors['environment'] = EnvironmentProcessor(self.config)
        elif self.node_type == NodeType.HYBRID:
            self.ai_processors['traffic'] = TrafficProcessor(self.config)
            self.ai_processors['crime'] = CrimeProcessor(self.config)
            self.ai_processors['environment'] = EnvironmentProcessor(self.config)
        
        # Initialize all processors
        for processor in self.ai_processors.values():
            await processor.initialize()
    
    async def _start_background_tasks(self) -> None:
        """Start background tasks"""
        tasks = [
            self._heartbeat_task(),
            self._processing_task(),
            self._metrics_task(),
            self._maintenance_task()
        ]
        
        for task in tasks:
            self.background_tasks.append(asyncio.create_task(task))
    
    async def _heartbeat_task(self) -> None:
        """Send periodic heartbeat to coordinator"""
        while not self.shutdown_event.is_set():
            try:
                await self._send_heartbeat()
                await asyncio.sleep(self.config.edge_node.heartbeat_interval)
            except Exception as e:
                logger.error(f"Heartbeat task error: {e}")
                await asyncio.sleep(5)
    
    async def _processing_task(self) -> None:
        """Process incoming sensor data"""
        while not self.shutdown_event.is_set():
            try:
                # Get processing job from queue
                job = await asyncio.wait_for(
                    self.processing_queue.get(), 
                    timeout=1.0
                )
                
                # Process the job
                await self._process_job(job)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Processing task error: {e}")
                self.metrics["error_count"] += 1
    
    async def _metrics_task(self) -> None:
        """Collect and report metrics"""
        while not self.shutdown_event.is_set():
            try:
                await self._collect_metrics()
                await asyncio.sleep(60)  # Collect metrics every minute
            except Exception as e:
                logger.error(f"Metrics task error: {e}")
                await asyncio.sleep(10)
    
    async def _maintenance_task(self) -> None:
        """Perform maintenance tasks"""
        while not self.shutdown_event.is_set():
            try:
                await self._perform_maintenance()
                await asyncio.sleep(3600)  # Maintenance every hour
            except Exception as e:
                logger.error(f"Maintenance task error: {e}")
                await asyncio.sleep(300)
    
    async def _send_heartbeat(self) -> None:
        """Send heartbeat to coordinator"""
        status = EdgeNodeStatus(
            node_id=self.node_id,
            node_type=self.node_type,
            location=self.location,
            status=self.status,
            last_heartbeat=get_current_timestamp(),
            **get_system_metrics(),
            active_sensors=await self.sensor_manager.get_active_sensors() if self.sensor_manager else [],
            processing_queue_size=self.processing_queue.qsize()
        )
        
        await self.communication_manager.send_heartbeat(status)
        self.last_heartbeat = get_current_timestamp()
    
    async def _handle_sensor_data(self, sensor_data: SensorData) -> None:
        """Handle incoming sensor data"""
        try:
            # Create processing job
            job = ProcessingJob(
                job_id=generate_id("job"),
                job_type=self.node_type.value,
                node_id=self.node_id,
                input_data=sensor_data,
                status=ProcessingStatus.PENDING,
                created_at=get_current_timestamp()
            )
            
            # Add to processing queue
            await self.processing_queue.put(job)
            
            # Store raw data
            await self.storage.store_sensor_data(sensor_data)
            
        except Exception as e:
            logger.error(f"Error handling sensor data: {e}")
    
    async def _process_job(self, job: ProcessingJob) -> None:
        """Process a job using appropriate AI processor"""
        start_time = time.time()
        
        try:
            job.status = ProcessingStatus.PROCESSING
            job.started_at = get_current_timestamp()
            
            # Select appropriate processor
            processor = self._get_processor_for_job(job)
            if not processor:
                raise ValueError(f"No processor available for job type: {job.job_type}")
            
            # Process the data
            result = await processor.process(job.input_data)
            
            # Update job with results
            job.result = result
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = get_current_timestamp()
            
            # Store processed result
            await self.storage.store_processing_result(job)
            
            # Check for alerts
            await self._check_for_alerts(job, result)
            
            # Update metrics
            processing_time = time.time() - start_time
            self.metrics["messages_processed"] += 1
            self.metrics["processing_time_avg"] = (
                (self.metrics["processing_time_avg"] * (self.metrics["messages_processed"] - 1) + processing_time) /
                self.metrics["messages_processed"]
            )
            
            logger.debug(f"Processed job {job.job_id} in {processing_time:.2f}s")
            
        except Exception as e:
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = get_current_timestamp()
            
            self.metrics["error_count"] += 1
            logger.error(f"Failed to process job {job.job_id}: {e}")
    
    def _get_processor_for_job(self, job: ProcessingJob):
        """Get appropriate processor for a job"""
        if job.job_type in self.ai_processors:
            return self.ai_processors[job.job_type]
        
        # Default to first available processor
        return next(iter(self.ai_processors.values())) if self.ai_processors else None
    
    async def _check_for_alerts(self, job: ProcessingJob, result: Dict[str, Any]) -> None:
        """Check processing results for alert conditions"""
        try:
            # Check for alert conditions based on node type and results
            alerts = []
            
            if self.node_type == NodeType.TRAFFIC:
                alerts.extend(await self._check_traffic_alerts(result))
            elif self.node_type == NodeType.CRIME:
                alerts.extend(await self._check_crime_alerts(result))
            elif self.node_type == NodeType.ENVIRONMENT:
                alerts.extend(await self._check_environment_alerts(result))
            
            # Send alerts to coordinator
            for alert in alerts:
                await self.communication_manager.send_alert(alert)
                self.metrics["alerts_generated"] += 1
                
        except Exception as e:
            logger.error(f"Error checking for alerts: {e}")
    
    async def _check_traffic_alerts(self, result: Dict[str, Any]) -> List[Alert]:
        """Check for traffic-related alerts"""
        alerts = []
        
        if "congestion_level" in result:
            congestion = result["congestion_level"]
            threshold = self.config.coordinator.alert_thresholds.get("traffic_congestion", 0.8)
            
            if congestion > threshold:
                alert = Alert(
                    alert_id=generate_id("alert"),
                    alert_type="traffic_congestion",
                    level="high" if congestion > 0.9 else "medium",
                    title="High Traffic Congestion Detected",
                    description=f"Congestion level: {congestion:.2f}",
                    location=self.location,
                    timestamp=get_current_timestamp(),
                    source_node=self.node_id,
                    source_data=result
                )
                alerts.append(alert)
        
        return alerts
    
    async def _check_crime_alerts(self, result: Dict[str, Any]) -> List[Alert]:
        """Check for crime-related alerts"""
        alerts = []
        
        if "suspicious_activity" in result and result["suspicious_activity"]:
            confidence = result.get("confidence_score", 0.0)
            threshold = self.config.coordinator.alert_thresholds.get("crime_probability", 0.6)
            
            if confidence > threshold:
                alert = Alert(
                    alert_id=generate_id("alert"),
                    alert_type="suspicious_activity",
                    level="critical" if confidence > 0.8 else "high",
                    title="Suspicious Activity Detected",
                    description=f"Activity type: {result.get('activity_type', 'unknown')}",
                    location=self.location,
                    timestamp=get_current_timestamp(),
                    source_node=self.node_id,
                    source_data=result
                )
                alerts.append(alert)
        
        return alerts
    
    async def _check_environment_alerts(self, result: Dict[str, Any]) -> List[Alert]:
        """Check for environment-related alerts"""
        alerts = []
        
        # Air quality alert
        if "air_quality_index" in result:
            aqi = result["air_quality_index"]
            threshold = self.config.coordinator.alert_thresholds.get("air_quality_index", 150)
            
            if aqi > threshold:
                alert = Alert(
                    alert_id=generate_id("alert"),
                    alert_type="air_quality",
                    level="critical" if aqi > 200 else "high",
                    title="Poor Air Quality Detected",
                    description=f"Air Quality Index: {aqi}",
                    location=self.location,
                    timestamp=get_current_timestamp(),
                    source_node=self.node_id,
                    source_data=result
                )
                alerts.append(alert)
        
        # Noise level alert
        if "noise_level" in result:
            noise = result["noise_level"]
            threshold = self.config.coordinator.alert_thresholds.get("noise_level", 70)
            
            if noise > threshold:
                alert = Alert(
                    alert_id=generate_id("alert"),
                    alert_type="noise_pollution",
                    level="high" if noise > 80 else "medium",
                    title="High Noise Level Detected",
                    description=f"Noise level: {noise} dB",
                    location=self.location,
                    timestamp=get_current_timestamp(),
                    source_node=self.node_id,
                    source_data=result
                )
                alerts.append(alert)
        
        return alerts
    
    async def _handle_incoming_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming messages from other nodes or coordinator"""
        try:
            message_type = message.get("type")
            
            if message_type == "data_request":
                await self._handle_data_request(message)
            elif message_type == "model_update":
                await self._handle_model_update(message)
            elif message_type == "config_update":
                await self._handle_config_update(message)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling incoming message: {e}")
    
    async def _handle_command(self, command: Dict[str, Any]) -> None:
        """Handle commands from coordinator"""
        try:
            command_type = command.get("type")
            
            if command_type == "restart":
                await self._restart()
            elif command_type == "shutdown":
                await self.shutdown()
            elif command_type == "update_config":
                await self._update_config(command.get("config", {}))
            else:
                logger.warning(f"Unknown command type: {command_type}")
                
        except Exception as e:
            logger.error(f"Error handling command: {e}")
    
    async def _collect_metrics(self) -> None:
        """Collect and store metrics"""
        try:
            system_metrics = get_system_metrics()
            
            # Combine with node-specific metrics
            all_metrics = {
                **system_metrics,
                **self.metrics,
                "node_id": self.node_id,
                "node_type": self.node_type.value,
                "queue_size": self.processing_queue.qsize()
            }
            
            # Store metrics
            await self.storage.store_metrics(all_metrics)
            
            # Send metrics to coordinator
            await self.communication_manager.send_metrics(all_metrics)
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    async def _perform_maintenance(self) -> None:
        """Perform maintenance tasks"""
        try:
            # Clean up old data
            await self.storage.cleanup_old_data()
            
            # Update AI models if needed
            for processor in self.ai_processors.values():
                await processor.check_for_updates()
            
            # Check system health
            await self._check_system_health()
            
        except Exception as e:
            logger.error(f"Error during maintenance: {e}")
    
    async def _check_system_health(self) -> None:
        """Check system health and report issues"""
        try:
            metrics = get_system_metrics()
            
            # Check resource usage
            if metrics["cpu_usage"] > 90:
                logger.warning(f"High CPU usage: {metrics['cpu_usage']:.1f}%")
            
            if metrics["memory_usage"] > 90:
                logger.warning(f"High memory usage: {metrics['memory_usage']:.1f}%")
            
            if metrics["disk_usage"] > 90:
                logger.warning(f"High disk usage: {metrics['disk_usage']:.1f}%")
            
            # Check queue size
            if self.processing_queue.qsize() > 100:
                logger.warning(f"Large processing queue: {self.processing_queue.qsize()}")
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
    
    async def _restart(self) -> None:
        """Restart the edge node"""
        logger.info(f"Restarting edge node {self.node_id}")
        await self.shutdown()
        await self.initialize()
    
    async def shutdown(self) -> None:
        """Shutdown the edge node gracefully"""
        logger.info(f"Shutting down edge node {self.node_id}")
        
        # Set shutdown event
        self.shutdown_event.set()
        
        # Wait for background tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Shutdown components
        if self.communication_manager:
            await self.communication_manager.shutdown()
        
        if self.sensor_manager:
            await self.sensor_manager.shutdown()
        
        if self.storage:
            await self.storage.shutdown()
        
        # Shutdown AI processors
        for processor in self.ai_processors.values():
            await processor.shutdown()
        
        self.status = "offline"
        logger.info(f"Edge node {self.node_id} shutdown complete")
    
    async def get_status(self) -> EdgeNodeStatus:
        """Get current node status"""
        return EdgeNodeStatus(
            node_id=self.node_id,
            node_type=self.node_type,
            location=self.location,
            status=self.status,
            last_heartbeat=self.last_heartbeat,
            **get_system_metrics(),
            active_sensors=await self.sensor_manager.get_active_sensors() if self.sensor_manager else [],
            processing_queue_size=self.processing_queue.qsize()
        )
