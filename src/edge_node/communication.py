"""
Communication Manager for Edge Nodes
"""

import asyncio
import json
import ssl
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import aiohttp
import websockets
import paho.mqtt.client as mqtt
from urllib.parse import urlparse

from ..common.models import EdgeNodeStatus, Alert, SensorData
from ..common.logger import get_logger
from ..common.utils import serialize_data, deserialize_data, retry_async

logger = get_logger(__name__)


class MQTTHandler:
    """MQTT communication handler"""
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.client = None
        self.is_connected = False
        self.message_callbacks = []
        self.command_callbacks = []
    
    async def initialize(self) -> None:
        """Initialize MQTT client"""
        try:
            self.client = mqtt.Client(client_id=f"edge_node_{self.node_id}")
            
            # Set up callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Set up authentication if configured
            if self.config.mqtt.username and self.config.mqtt.password:
                self.client.username_pw_set(
                    self.config.mqtt.username,
                    self.config.mqtt.password
                )
            
            # Connect to MQTT broker
            await self._connect()
            
        except Exception as e:
            logger.error(f"Failed to initialize MQTT handler: {e}")
            raise
    
    async def _connect(self) -> None:
        """Connect to MQTT broker"""
        try:
            self.client.connect(
                self.config.mqtt.host,
                self.config.mqtt.port,
                keepalive=60
            )
            
            # Start the loop in a separate thread
            self.client.loop_start()
            
            # Wait for connection
            await asyncio.sleep(1)
            
            if self.is_connected:
                logger.info(f"Connected to MQTT broker at {self.config.mqtt.host}:{self.config.mqtt.port}")
            else:
                raise ConnectionError("Failed to connect to MQTT broker")
                
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.is_connected = True
            logger.info("MQTT connection successful")
            
            # Subscribe to relevant topics
            topics = [
                f"commands/{self.node_id}",
                f"messages/{self.node_id}",
                "broadcast/all"
            ]
            
            for topic in topics:
                client.subscribe(topic)
                logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.is_connected = False
        logger.warning("MQTT disconnected")
    
    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            message = json.loads(payload)
            
            # Route message based on topic
            if topic.startswith("commands/"):
                asyncio.create_task(self._handle_command(message))
            elif topic.startswith("messages/"):
                asyncio.create_task(self._handle_message(message))
            elif topic.startswith("broadcast/"):
                asyncio.create_task(self._handle_broadcast(message))
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    async def _handle_command(self, command: Dict[str, Any]) -> None:
        """Handle incoming commands"""
        for callback in self.command_callbacks:
            try:
                await callback(command)
            except Exception as e:
                logger.error(f"Error in command callback: {e}")
    
    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming messages"""
        for callback in self.message_callbacks:
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"Error in message callback: {e}")
    
    async def _handle_broadcast(self, message: Dict[str, Any]) -> None:
        """Handle broadcast messages"""
        await self._handle_message(message)
    
    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish message to MQTT topic"""
        if not self.is_connected:
            logger.warning("MQTT not connected, cannot publish message")
            return
        
        try:
            payload = json.dumps(message)
            result = self.client.publish(topic, payload)
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Failed to publish to topic {topic}")
                
        except Exception as e:
            logger.error(f"Error publishing MQTT message: {e}")
    
    def on_message(self, callback: Callable) -> None:
        """Register message callback"""
        self.message_callbacks.append(callback)
    
    def on_command(self, callback: Callable) -> None:
        """Register command callback"""
        self.command_callbacks.append(callback)
    
    async def shutdown(self) -> None:
        """Shutdown MQTT handler"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        self.is_connected = False
        logger.info("MQTT handler shutdown")


class WebSocketHandler:
    """WebSocket communication handler"""
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.websocket = None
        self.is_connected = False
        self.message_callbacks = []
        self.reconnect_interval = 5
    
    async def initialize(self) -> None:
        """Initialize WebSocket connection"""
        await self._connect()
    
    async def _connect(self) -> None:
        """Connect to WebSocket server"""
        try:
            coordinator_url = f"ws://{self.config.coordinator.host}:{self.config.coordinator.port}/ws/{self.node_id}"
            
            self.websocket = await websockets.connect(coordinator_url)
            self.is_connected = True
            
            logger.info(f"Connected to coordinator WebSocket at {coordinator_url}")
            
            # Start message handling loop
            asyncio.create_task(self._message_loop())
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            # Schedule reconnection
            asyncio.create_task(self._reconnect())
    
    async def _message_loop(self) -> None:
        """Handle incoming WebSocket messages"""
        try:
            while self.is_connected and self.websocket:
                message_str = await self.websocket.recv()
                message = json.loads(message_str)
                
                # Handle the message
                for callback in self.message_callbacks:
                    try:
                        await callback(message)
                    except Exception as e:
                        logger.error(f"Error in WebSocket message callback: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
            asyncio.create_task(self._reconnect())
        except Exception as e:
            logger.error(f"WebSocket message loop error: {e}")
            self.is_connected = False
    
    async def _reconnect(self) -> None:
        """Reconnect to WebSocket server"""
        await asyncio.sleep(self.reconnect_interval)
        if not self.is_connected:
            logger.info("Attempting to reconnect to WebSocket server")
            await self._connect()
    
    async def send(self, message: Dict[str, Any]) -> None:
        """Send message via WebSocket"""
        if not self.is_connected or not self.websocket:
            logger.warning("WebSocket not connected, cannot send message")
            return
        
        try:
            message_str = json.dumps(message)
            await self.websocket.send(message_str)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
    
    def on_message(self, callback: Callable) -> None:
        """Register message callback"""
        self.message_callbacks.append(callback)
    
    async def shutdown(self) -> None:
        """Shutdown WebSocket handler"""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
        logger.info("WebSocket handler shutdown")


class HTTPHandler:
    """HTTP communication handler"""
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.session = None
        self.base_url = f"http://{config.coordinator.host}:{config.coordinator.port}"
    
    async def initialize(self) -> None:
        """Initialize HTTP session"""
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            ssl=False
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        logger.info("HTTP handler initialized")
    
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send POST request"""
        if not self.session:
            logger.warning("HTTP session not initialized")
            return None
        
        try:
            url = f"{self.base_url}/{endpoint}"
            
            async with self.session.post(
                url,
                json=data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"HTTP POST failed with status {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"HTTP POST error: {e}")
            return None
    
    async def get(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Send GET request"""
        if not self.session:
            logger.warning("HTTP session not initialized")
            return None
        
        try:
            url = f"{self.base_url}/{endpoint}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"HTTP GET failed with status {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"HTTP GET error: {e}")
            return None
    
    async def shutdown(self) -> None:
        """Shutdown HTTP handler"""
        if self.session:
            await self.session.close()
        logger.info("HTTP handler shutdown")


class CommunicationManager:
    """Manages all communication for an edge node"""
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        
        # Communication handlers
        self.mqtt_handler = MQTTHandler(node_id, config)
        self.websocket_handler = WebSocketHandler(node_id, config)
        self.http_handler = HTTPHandler(node_id, config)
        
        # Callbacks
        self.message_callbacks = []
        self.command_callbacks = []
        
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize all communication handlers"""
        logger.info(f"Initializing communication manager for node {self.node_id}")
        
        try:
            # Initialize handlers
            await self.mqtt_handler.initialize()
            await self.websocket_handler.initialize()
            await self.http_handler.initialize()
            
            # Set up callbacks
            self.mqtt_handler.on_message(self._on_message)
            self.mqtt_handler.on_command(self._on_command)
            self.websocket_handler.on_message(self._on_message)
            
            self.is_initialized = True
            logger.info("Communication manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize communication manager: {e}")
            raise
    
    async def _on_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming messages"""
        for callback in self.message_callbacks:
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"Error in message callback: {e}")
    
    async def _on_command(self, command: Dict[str, Any]) -> None:
        """Handle incoming commands"""
        for callback in self.command_callbacks:
            try:
                await callback(command)
            except Exception as e:
                logger.error(f"Error in command callback: {e}")
    
    def on_message(self, callback: Callable) -> None:
        """Register message callback"""
        self.message_callbacks.append(callback)
    
    def on_command(self, callback: Callable) -> None:
        """Register command callback"""
        self.command_callbacks.append(callback)
    
    async def send_heartbeat(self, status: EdgeNodeStatus) -> None:
        """Send heartbeat to coordinator"""
        try:
            # Send via HTTP
            response = await self.http_handler.post(
                f"api/nodes/{self.node_id}/heartbeat",
                status.to_dict()
            )
            
            # Also send via MQTT for real-time monitoring
            await self.mqtt_handler.publish(
                f"status/{self.node_id}",
                status.to_dict()
            )
            
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
    
    async def send_alert(self, alert: Alert) -> None:
        """Send alert to coordinator"""
        try:
            # Send via HTTP for reliability
            response = await self.http_handler.post(
                "api/alerts",
                alert.to_dict()
            )
            
            # Also send via MQTT for real-time notification
            await self.mqtt_handler.publish(
                f"alerts/{alert.alert_type}",
                alert.to_dict()
            )
            
            # Send via WebSocket for real-time dashboard updates
            await self.websocket_handler.send({
                "type": "alert",
                "data": alert.to_dict()
            })
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def send_sensor_data(self, sensor_data: SensorData) -> None:
        """Send sensor data to coordinator"""
        try:
            # Send via MQTT (primary channel for sensor data)
            await self.mqtt_handler.publish(
                f"sensors/{sensor_data.sensor_id}/data",
                sensor_data.to_dict()
            )
            
        except Exception as e:
            logger.error(f"Error sending sensor data: {e}")
    
    async def send_metrics(self, metrics: Dict[str, Any]) -> None:
        """Send metrics to coordinator"""
        try:
            # Send via HTTP
            response = await self.http_handler.post(
                f"api/nodes/{self.node_id}/metrics",
                metrics
            )
            
            # Also send via MQTT
            await self.mqtt_handler.publish(
                f"metrics/{self.node_id}",
                metrics
            )
            
        except Exception as e:
            logger.error(f"Error sending metrics: {e}")
    
    async def request_data(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Request data from coordinator"""
        try:
            response = await self.http_handler.post(
                "api/data/request",
                request
            )
            return response
            
        except Exception as e:
            logger.error(f"Error requesting data: {e}")
            return None
    
    async def send_message(self, target_node: str, message: Dict[str, Any]) -> None:
        """Send message to another node"""
        try:
            await self.mqtt_handler.publish(
                f"messages/{target_node}",
                {
                    "from": self.node_id,
                    "to": target_node,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending message to {target_node}: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown communication manager"""
        logger.info("Shutting down communication manager")
        
        await self.mqtt_handler.shutdown()
        await self.websocket_handler.shutdown()
        await self.http_handler.shutdown()
        
        self.message_callbacks.clear()
        self.command_callbacks.clear()
        self.is_initialized = False
        
        logger.info("Communication manager shutdown complete")
