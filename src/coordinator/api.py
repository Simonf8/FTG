"""
RESTful API endpoints for the central coordinator.
Provides HTTP/WebSocket interfaces for node management and data access.
"""
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import threading
import time

from ..common.logger import setup_logger
from ..common.models import Alert, NodeStatus, EdgeNode, MetricsData

logger = setup_logger(__name__)

class CoordinatorAPI:
    """RESTful API and WebSocket server for the coordinator."""
    
    def __init__(self, coordinator_core):
        self.coordinator = coordinator_core
        self.app = Flask(__name__)
        CORS(self.app, origins="*")
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.setup_routes()
        self.setup_websocket()
        self.start_background_tasks()
        
    def setup_routes(self):
        """Setup REST API routes."""
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            })
        
        @self.app.route('/api/nodes', methods=['GET'])
        def get_nodes():
            """Get all registered nodes."""
            try:
                nodes = []
                for node_id, node in self.coordinator.nodes.items():
                    nodes.append({
                        'node_id': node_id,
                        'node_type': node.node_type,
                        'location': node.location,
                        'status': node.status,
                        'last_heartbeat': node.last_heartbeat.isoformat() if node.last_heartbeat else None,
                        'capabilities': node.capabilities
                    })
                return jsonify({'nodes': nodes})
            except Exception as e:
                logger.error(f"Error getting nodes: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/nodes/<node_id>', methods=['GET'])
        def get_node(node_id: str):
            """Get specific node details."""
            try:
                node = self.coordinator.nodes.get(node_id)
                if not node:
                    return jsonify({'error': 'Node not found'}), 404
                
                return jsonify({
                    'node_id': node_id,
                    'node_type': node.node_type,
                    'location': node.location,
                    'status': node.status,
                    'last_heartbeat': node.last_heartbeat.isoformat() if node.last_heartbeat else None,
                    'capabilities': node.capabilities,
                    'metrics': self.coordinator.get_node_metrics(node_id)
                })
            except Exception as e:
                logger.error(f"Error getting node {node_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/nodes/<node_id>/command', methods=['POST'])
        def send_command(node_id: str):
            """Send command to a specific node."""
            try:
                data = request.get_json()
                if not data or 'command' not in data:
                    return jsonify({'error': 'Command is required'}), 400
                
                result = self.coordinator.send_command(node_id, data['command'], data.get('params', {}))
                return jsonify({'result': result})
            except Exception as e:
                logger.error(f"Error sending command to {node_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/alerts', methods=['GET'])
        def get_alerts():
            """Get recent alerts."""
            try:
                hours = request.args.get('hours', 24, type=int)
                severity = request.args.get('severity', None)
                
                alerts = self.coordinator.get_alerts(
                    hours=hours, 
                    severity=severity
                )
                
                return jsonify({
                    'alerts': [alert.to_dict() for alert in alerts]
                })
            except Exception as e:
                logger.error(f"Error getting alerts: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/alerts/<alert_id>', methods=['PUT'])
        def update_alert(alert_id: str):
            """Update alert status."""
            try:
                data = request.get_json()
                if not data or 'status' not in data:
                    return jsonify({'error': 'Status is required'}), 400
                
                result = self.coordinator.update_alert_status(alert_id, data['status'])
                return jsonify({'result': result})
            except Exception as e:
                logger.error(f"Error updating alert {alert_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/metrics', methods=['GET'])
        def get_metrics():
            """Get system metrics."""
            try:
                node_id = request.args.get('node_id', None)
                hours = request.args.get('hours', 1, type=int)
                
                metrics = self.coordinator.get_system_metrics(
                    node_id=node_id,
                    hours=hours
                )
                
                return jsonify({'metrics': metrics})
            except Exception as e:
                logger.error(f"Error getting metrics: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/data/stream', methods=['GET'])
        def stream_data():
            """Stream real-time data."""
            def generate():
                while True:
                    try:
                        # Get latest data from all nodes
                        data = {
                            'timestamp': datetime.now().isoformat(),
                            'nodes': {},
                            'alerts': []
                        }
                        
                        # Get node data
                        for node_id, node in self.coordinator.nodes.items():
                            if node.status == 'active':
                                data['nodes'][node_id] = {
                                    'status': node.status,
                                    'last_data': node.last_data if hasattr(node, 'last_data') else None
                                }
                        
                        # Get recent alerts
                        recent_alerts = self.coordinator.get_alerts(hours=1)
                        data['alerts'] = [alert.to_dict() for alert in recent_alerts[-5:]]  # Last 5 alerts
                        
                        yield f"data: {json.dumps(data)}\n\n"
                        time.sleep(1)  # Update every second
                    except Exception as e:
                        logger.error(f"Error in data stream: {e}")
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return Response(generate(), mimetype='text/event-stream')
    
    def setup_websocket(self):
        """Setup WebSocket events."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.info(f"Client connected: {request.sid}")
            emit('connected', {'message': 'Connected to coordinator'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info(f"Client disconnected: {request.sid}")
        
        @self.socketio.on('subscribe_node')
        def handle_subscribe_node(data):
            """Subscribe to node updates."""
            node_id = data.get('node_id')
            if node_id:
                # Join room for this node
                from flask_socketio import join_room
                join_room(f"node_{node_id}")
                emit('subscribed', {'node_id': node_id})
        
        @self.socketio.on('get_dashboard_data')
        def handle_get_dashboard_data():
            """Get dashboard data."""
            try:
                dashboard_data = self.coordinator.get_dashboard_data()
                emit('dashboard_data', dashboard_data)
            except Exception as e:
                logger.error(f"Error getting dashboard data: {e}")
                emit('error', {'message': str(e)})
    
    def start_background_tasks(self):
        """Start background tasks for real-time updates."""
        
        def broadcast_updates():
            """Broadcast real-time updates to connected clients."""
            while True:
                try:
                    # Broadcast node updates
                    for node_id, node in self.coordinator.nodes.items():
                        if hasattr(node, 'updated') and node.updated:
                            node_data = {
                                'node_id': node_id,
                                'status': node.status,
                                'last_heartbeat': node.last_heartbeat.isoformat() if node.last_heartbeat else None,
                                'timestamp': datetime.now().isoformat()
                            }
                            self.socketio.emit('node_update', node_data, room=f"node_{node_id}")
                            node.updated = False
                    
                    # Broadcast new alerts
                    new_alerts = self.coordinator.get_new_alerts()
                    for alert in new_alerts:
                        self.socketio.emit('new_alert', alert.to_dict())
                    
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error in broadcast updates: {e}")
                    time.sleep(5)
        
        # Start background thread
        update_thread = threading.Thread(target=broadcast_updates, daemon=True)
        update_thread.start()
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the API server."""
        logger.info(f"Starting coordinator API server on {host}:{port}")
        self.socketio.run(self.app, host=host, port=port, debug=debug)
    
    def emit_node_update(self, node_id: str, data: Dict[str, Any]):
        """Emit node update to WebSocket clients."""
        self.socketio.emit('node_update', {
            'node_id': node_id,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }, room=f"node_{node_id}")
    
    def emit_alert(self, alert: Alert):
        """Emit new alert to WebSocket clients."""
        self.socketio.emit('new_alert', alert.to_dict())
    
    def emit_metrics_update(self, metrics: Dict[str, Any]):
        """Emit metrics update to WebSocket clients."""
        self.socketio.emit('metrics_update', {
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })
