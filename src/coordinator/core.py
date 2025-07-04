"""
Central Coordinator Core Implementation
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict

from ..common.models import (
    EdgeNodeStatus, Alert, SensorData, SystemMetrics, NodeType,
    ProcessingJob, Location
)
from ..common.config import get_config
from ..common.logger import get_logger
from ..common.utils import get_current_timestamp, generate_id

logger = get_logger(__name__)


class CentralCoordinator:
    """Central coordinator for the distributed edge AI network"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()
        
        # Node management
        self.registered_nodes: Dict[str, EdgeNodeStatus] = {}
        self.node_heartbeats: Dict[str, datetime] = {}
        self.offline_nodes: Set[str] = set()
        
        # Data and alerts
        self.recent_alerts: List[Alert] = []
        self.system_metrics: Dict[str, Any] = {}
        self.sensor_data_buffer: Dict[str, List[SensorData]] = defaultdict(list)
        
        # Components
        self.api_server = None
        self.dashboard_server = None
        self.data_processor = None
        self.alert_manager = None
        self.resource_manager = None
        self.websocket_connections: Dict[str, Any] = {}
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()
        
        # Statistics
        self.stats = {
            "total_messages_processed": 0,
            "total_alerts_generated": 0,
            "uptime_start": get_current_timestamp(),
            "last_maintenance": get_current_timestamp()
        }
        
        logger.info("Central coordinator initialized")
    
    async def initialize(self) -> None:
        """Initialize the central coordinator"""
        logger.info("Starting central coordinator initialization")
        
        try:
            # Initialize components
            await self._initialize_components()
            
            # Start background tasks
            await self._start_background_tasks()
            
            # Start servers
            await self._start_servers()
            
            logger.info("Central coordinator initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize central coordinator: {e}")
            raise
    
    async def _initialize_components(self) -> None:
        """Initialize coordinator components"""
        from .data_processor import DataProcessor
        from .alert_manager import AlertManager
        from .resource_manager import ResourceManager
        
        # Initialize data processor
        self.data_processor = DataProcessor(self.config)
        await self.data_processor.initialize()
        
        # Initialize alert manager
        self.alert_manager = AlertManager(self.config)
        await self.alert_manager.initialize()
        
        # Initialize resource manager
        self.resource_manager = ResourceManager(self.config)
        await self.resource_manager.initialize()
        
        # Set up component callbacks
        self.data_processor.on_insight(self._on_cross_domain_insight)
        self.alert_manager.on_alert(self._on_alert_generated)
    
    async def _start_background_tasks(self) -> None:
        """Start background tasks"""
        tasks = [
            self._node_health_monitor(),
            self._metrics_collector(),
            self._data_aggregator(),
            self._system_maintenance(),
            self._alert_processor()
        ]
        
        for task in tasks:
            self.background_tasks.append(asyncio.create_task(task))
    
    async def _start_servers(self) -> None:
        """Start API and dashboard servers"""
        from .api import CoordinatorAPI
        from .dashboard import DashboardServer
        
        # Start API server
        self.api_server = CoordinatorAPI(self)
        await self.api_server.start()
        
        # Start dashboard server
        self.dashboard_server = DashboardServer(self)
        await self.dashboard_server.start()
    
    async def _node_health_monitor(self) -> None:
        """Monitor node health and detect offline nodes"""
        while not self.shutdown_event.is_set():
            try:
                current_time = get_current_timestamp()
                heartbeat_timeout = timedelta(seconds=self.config.edge_node.heartbeat_interval * 3)
                
                # Check for offline nodes
                offline_nodes = set()
                for node_id, last_heartbeat in self.node_heartbeats.items():
                    if current_time - last_heartbeat > heartbeat_timeout:
                        offline_nodes.add(node_id)
                
                # Process newly offline nodes
                newly_offline = offline_nodes - self.offline_nodes
                for node_id in newly_offline:
                    await self._handle_node_offline(node_id)
                
                # Process nodes that came back online
                back_online = self.offline_nodes - offline_nodes
                for node_id in back_online:
                    await self._handle_node_online(node_id)
                
                self.offline_nodes = offline_nodes
                
                # Update system metrics
                await self._update_system_metrics()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in node health monitor: {e}")
                await asyncio.sleep(10)
    
    async def _metrics_collector(self) -> None:
        """Collect and aggregate system metrics"""
        while not self.shutdown_event.is_set():
            try:
                # Collect metrics from all components
                coordinator_metrics = await self._collect_coordinator_metrics()
                
                # Store metrics
                self.system_metrics = {
                    **coordinator_metrics,
                    "timestamp": get_current_timestamp().isoformat(),
                    "coordinator_id": "central_coordinator"
                }
                
                # Process metrics for insights
                await self.data_processor.process_metrics(self.system_metrics)
                
                await asyncio.sleep(60)  # Collect every minute
                
            except Exception as e:
                logger.error(f"Error in metrics collector: {e}")
                await asyncio.sleep(30)
    
    async def _data_aggregator(self) -> None:
        """Aggregate data from edge nodes"""
        while not self.shutdown_event.is_set():
            try:
                # Process buffered sensor data
                await self._process_sensor_data_buffer()
                
                # Perform cross-domain analysis
                await self._perform_cross_domain_analysis()
                
                await asyncio.sleep(10)  # Process every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in data aggregator: {e}")
                await asyncio.sleep(5)
    
    async def _system_maintenance(self) -> None:
        """Perform system maintenance tasks"""
        while not self.shutdown_event.is_set():
            try:
                # Clean up old data
                await self._cleanup_old_data()
                
                # Optimize resource allocation
                await self.resource_manager.optimize_allocation()
                
                # Update statistics
                await self._update_statistics()
                
                self.stats["last_maintenance"] = get_current_timestamp()
                
                await asyncio.sleep(3600)  # Maintenance every hour
                
            except Exception as e:
                logger.error(f"Error in system maintenance: {e}")
                await asyncio.sleep(300)
    
    async def _alert_processor(self) -> None:
        """Process and correlate alerts"""
        while not self.shutdown_event.is_set():
            try:
                # Process alert correlations
                await self.alert_manager.process_correlations()
                
                # Check for alert patterns
                await self._analyze_alert_patterns()
                
                await asyncio.sleep(30)  # Process every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in alert processor: {e}")
                await asyncio.sleep(10)
    
    async def register_node(self, node_status: EdgeNodeStatus) -> None:
        """Register a new edge node"""
        logger.info(f"Registering node {node_status.node_id} of type {node_status.node_type}")
        
        self.registered_nodes[node_status.node_id] = node_status
        self.node_heartbeats[node_status.node_id] = get_current_timestamp()
        
        # Remove from offline nodes if it was there
        self.offline_nodes.discard(node_status.node_id)
        
        # Notify resource manager
        await self.resource_manager.add_node(node_status)
        
        # Broadcast node registration
        await self._broadcast_node_update(node_status, "registered")
    
    async def update_node_heartbeat(self, node_id: str, node_status: EdgeNodeStatus) -> None:
        """Update node heartbeat"""
        self.node_heartbeats[node_id] = get_current_timestamp()
        self.registered_nodes[node_id] = node_status
        
        # Remove from offline nodes
        self.offline_nodes.discard(node_id)
        
        # Update resource manager
        await self.resource_manager.update_node_status(node_status)
    
    async def receive_sensor_data(self, sensor_data: SensorData) -> None:
        """Receive sensor data from edge nodes"""
        # Buffer sensor data for processing
        self.sensor_data_buffer[sensor_data.sensor_id].append(sensor_data)
        
        # Keep buffer size manageable
        if len(self.sensor_data_buffer[sensor_data.sensor_id]) > 100:
            self.sensor_data_buffer[sensor_data.sensor_id].pop(0)
        
        # Process data immediately if critical
        if await self._is_critical_data(sensor_data):
            await self.data_processor.process_sensor_data(sensor_data)
        
        self.stats["total_messages_processed"] += 1
    
    async def receive_alert(self, alert: Alert) -> None:
        """Receive alert from edge nodes"""
        logger.info(f"Received alert: {alert.alert_type} from {alert.source_node}")
        
        # Store alert
        self.recent_alerts.append(alert)
        
        # Keep alert buffer manageable
        if len(self.recent_alerts) > 1000:
            self.recent_alerts.pop(0)
        
        # Process alert
        await self.alert_manager.process_alert(alert)
        
        # Broadcast alert to dashboard
        await self._broadcast_alert(alert)
        
        self.stats["total_alerts_generated"] += 1
    
    async def receive_node_metrics(self, node_id: str, metrics: Dict[str, Any]) -> None:
        """Receive metrics from edge nodes"""
        # Store metrics
        if "node_metrics" not in self.system_metrics:
            self.system_metrics["node_metrics"] = {}
        
        self.system_metrics["node_metrics"][node_id] = metrics
        
        # Process metrics
        await self.data_processor.process_node_metrics(node_id, metrics)
    
    async def _handle_node_offline(self, node_id: str) -> None:
        """Handle node going offline"""
        logger.warning(f"Node {node_id} went offline")
        
        # Generate alert
        alert = Alert(
            alert_id=generate_id("alert"),
            alert_type="node_offline",
            level="medium",
            title=f"Node {node_id} Offline",
            description=f"Edge node {node_id} has gone offline",
            location=self.registered_nodes[node_id].location if node_id in self.registered_nodes else Location(0, 0),
            timestamp=get_current_timestamp(),
            source_node="coordinator",
            source_data={"node_id": node_id}
        )
        
        await self.receive_alert(alert)
        
        # Notify resource manager
        await self.resource_manager.handle_node_offline(node_id)
        
        # Broadcast node update
        if node_id in self.registered_nodes:
            await self._broadcast_node_update(self.registered_nodes[node_id], "offline")
    
    async def _handle_node_online(self, node_id: str) -> None:
        """Handle node coming back online"""
        logger.info(f"Node {node_id} came back online")
        
        # Generate alert
        alert = Alert(
            alert_id=generate_id("alert"),
            alert_type="node_online",
            level="low",
            title=f"Node {node_id} Online",
            description=f"Edge node {node_id} has come back online",
            location=self.registered_nodes[node_id].location if node_id in self.registered_nodes else Location(0, 0),
            timestamp=get_current_timestamp(),
            source_node="coordinator",
            source_data={"node_id": node_id}
        )
        
        await self.receive_alert(alert)
        
        # Notify resource manager
        await self.resource_manager.handle_node_online(node_id)
        
        # Broadcast node update
        if node_id in self.registered_nodes:
            await self._broadcast_node_update(self.registered_nodes[node_id], "online")
    
    async def _is_critical_data(self, sensor_data: SensorData) -> bool:
        """Check if sensor data is critical and needs immediate processing"""
        # Example criteria for critical data
        if sensor_data.sensor_type.value == "camera":
            # Check if it's from a crime detection node
            return any(
                node.node_type == NodeType.CRIME and sensor_data.sensor_id in node.active_sensors
                for node in self.registered_nodes.values()
            )
        
        return False
    
    async def _process_sensor_data_buffer(self) -> None:
        """Process buffered sensor data"""
        for sensor_id, data_list in self.sensor_data_buffer.items():
            if data_list:
                # Process latest data
                latest_data = data_list[-1]
                await self.data_processor.process_sensor_data(latest_data)
                
                # Clear processed data
                self.sensor_data_buffer[sensor_id] = []
    
    async def _perform_cross_domain_analysis(self) -> None:
        """Perform cross-domain analysis"""
        # Analyze correlations between different types of data
        traffic_nodes = [n for n in self.registered_nodes.values() if n.node_type == NodeType.TRAFFIC]
        crime_nodes = [n for n in self.registered_nodes.values() if n.node_type == NodeType.CRIME]
        env_nodes = [n for n in self.registered_nodes.values() if n.node_type == NodeType.ENVIRONMENT]
        
        # Example: Correlate traffic congestion with crime incidents
        await self.data_processor.analyze_traffic_crime_correlation(traffic_nodes, crime_nodes)
        
        # Example: Correlate environmental conditions with traffic patterns
        await self.data_processor.analyze_environment_traffic_correlation(env_nodes, traffic_nodes)
    
    async def _update_system_metrics(self) -> None:
        """Update system-wide metrics"""
        total_nodes = len(self.registered_nodes)
        active_nodes = total_nodes - len(self.offline_nodes)
        
        # Count active sensors
        total_sensors = sum(len(node.active_sensors) for node in self.registered_nodes.values())
        
        # Calculate processing stats
        uptime = get_current_timestamp() - self.stats["uptime_start"]
        
        self.system_metrics.update({
            "total_nodes": total_nodes,
            "active_nodes": active_nodes,
            "offline_nodes": len(self.offline_nodes),
            "total_sensors": total_sensors,
            "total_alerts": len(self.recent_alerts),
            "uptime_seconds": uptime.total_seconds(),
            "messages_processed": self.stats["total_messages_processed"],
            "alerts_generated": self.stats["total_alerts_generated"]
        })
    
    async def _collect_coordinator_metrics(self) -> Dict[str, Any]:
        """Collect coordinator-specific metrics"""
        return {
            "registered_nodes": len(self.registered_nodes),
            "offline_nodes": len(self.offline_nodes),
            "recent_alerts": len(self.recent_alerts),
            "websocket_connections": len(self.websocket_connections),
            "background_tasks": len(self.background_tasks),
            "sensor_data_buffer_size": sum(len(data) for data in self.sensor_data_buffer.values())
        }
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old data"""
        # Remove old alerts
        cutoff_time = get_current_timestamp() - timedelta(days=7)
        self.recent_alerts = [
            alert for alert in self.recent_alerts
            if alert.timestamp > cutoff_time
        ]
        
        # Clear old sensor data buffers
        for sensor_id in list(self.sensor_data_buffer.keys()):
            self.sensor_data_buffer[sensor_id] = []
    
    async def _update_statistics(self) -> None:
        """Update system statistics"""
        # This would typically update a database with statistics
        pass
    
    async def _analyze_alert_patterns(self) -> None:
        """Analyze patterns in alerts"""
        # This would implement pattern analysis for alerts
        pass
    
    async def _on_cross_domain_insight(self, insight: Dict[str, Any]) -> None:
        """Handle cross-domain insights"""
        logger.info(f"Cross-domain insight: {insight}")
        
        # Broadcast insight to dashboard
        await self._broadcast_insight(insight)
    
    async def _on_alert_generated(self, alert: Alert) -> None:
        """Handle alerts generated by alert manager"""
        await self.receive_alert(alert)
    
    async def _broadcast_node_update(self, node_status: EdgeNodeStatus, event_type: str) -> None:
        """Broadcast node update to connected clients"""
        message = {
            "type": "node_update",
            "event": event_type,
            "node": node_status.to_dict()
        }
        
        await self._broadcast_to_websockets(message)
    
    async def _broadcast_alert(self, alert: Alert) -> None:
        """Broadcast alert to connected clients"""
        message = {
            "type": "alert",
            "data": alert.to_dict()
        }
        
        await self._broadcast_to_websockets(message)
    
    async def _broadcast_insight(self, insight: Dict[str, Any]) -> None:
        """Broadcast insight to connected clients"""
        message = {
            "type": "insight",
            "data": insight
        }
        
        await self._broadcast_to_websockets(message)
    
    async def _broadcast_to_websockets(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
        
        message_str = json.dumps(message)
        
        # Remove disconnected clients
        disconnected_clients = []
        
        for client_id, websocket in self.websocket_connections.items():
            try:
                await websocket.send(message_str)
            except Exception as e:
                logger.warning(f"Failed to send message to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Remove disconnected clients
        for client_id in disconnected_clients:
            self.websocket_connections.pop(client_id, None)
    
    def add_websocket_connection(self, client_id: str, websocket) -> None:
        """Add WebSocket connection"""
        self.websocket_connections[client_id] = websocket
        logger.info(f"WebSocket client {client_id} connected")
    
    def remove_websocket_connection(self, client_id: str) -> None:
        """Remove WebSocket connection"""
        self.websocket_connections.pop(client_id, None)
        logger.info(f"WebSocket client {client_id} disconnected")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "coordinator_status": "online",
            "total_nodes": len(self.registered_nodes),
            "active_nodes": len(self.registered_nodes) - len(self.offline_nodes),
            "offline_nodes": len(self.offline_nodes),
            "total_alerts": len(self.recent_alerts),
            "system_metrics": self.system_metrics,
            "uptime": (get_current_timestamp() - self.stats["uptime_start"]).total_seconds(),
            "last_maintenance": self.stats["last_maintenance"].isoformat()
        }
    
    async def get_node_status(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific node"""
        if node_id not in self.registered_nodes:
            return None
        
        node = self.registered_nodes[node_id]
        return {
            **node.to_dict(),
            "is_offline": node_id in self.offline_nodes,
            "last_heartbeat": self.node_heartbeats.get(node_id, get_current_timestamp()).isoformat()
        }
    
    async def get_recent_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        return [alert.to_dict() for alert in self.recent_alerts[-limit:]]
    
    async def shutdown(self) -> None:
        """Shutdown the central coordinator"""
        logger.info("Shutting down central coordinator")
        
        # Set shutdown event
        self.shutdown_event.set()
        
        # Wait for background tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Shutdown components
        if self.data_processor:
            await self.data_processor.shutdown()
        
        if self.alert_manager:
            await self.alert_manager.shutdown()
        
        if self.resource_manager:
            await self.resource_manager.shutdown()
        
        # Shutdown servers
        if self.api_server:
            await self.api_server.shutdown()
        
        if self.dashboard_server:
            await self.dashboard_server.shutdown()
        
        # Close WebSocket connections
        for websocket in self.websocket_connections.values():
            await websocket.close()
        
        logger.info("Central coordinator shutdown complete")
