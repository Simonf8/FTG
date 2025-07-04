"""
Dashboard data aggregation and visualization support.
Provides data processing and formatting for the web dashboard.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from ..common.logger import setup_logger
from ..common.models import Alert, NodeStatus, EdgeNode, MetricsData

logger = setup_logger(__name__)

class DashboardManager:
    """Manages dashboard data aggregation and visualization."""
    
    def __init__(self, coordinator_core):
        self.coordinator = coordinator_core
        self.cache = {}
        self.cache_ttl = 30  # seconds
        self.last_cache_update = {}
        
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        try:
            # Check cache first
            if self._is_cache_valid('dashboard'):
                return self.cache['dashboard']
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'system_overview': self._get_system_overview(),
                'node_status': self._get_node_status_summary(),
                'alert_summary': self._get_alert_summary(),
                'metrics': self._get_metrics_summary(),
                'traffic_data': self._get_traffic_data(),
                'environmental_data': self._get_environmental_data(),
                'crime_data': self._get_crime_data(),
                'performance_metrics': self._get_performance_metrics()
            }
            
            # Cache the result
            self.cache['dashboard'] = data
            self.last_cache_update['dashboard'] = datetime.now()
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {'error': str(e)}
    
    def _get_system_overview(self) -> Dict[str, Any]:
        """Get system overview statistics."""
        total_nodes = len(self.coordinator.nodes)
        active_nodes = sum(1 for node in self.coordinator.nodes.values() if node.status == 'active')
        inactive_nodes = total_nodes - active_nodes
        
        # Get recent alerts
        recent_alerts = self.coordinator.get_alerts(hours=24)
        critical_alerts = len([a for a in recent_alerts if a.severity == 'critical'])
        
        return {
            'total_nodes': total_nodes,
            'active_nodes': active_nodes,
            'inactive_nodes': inactive_nodes,
            'uptime_percentage': (active_nodes / total_nodes * 100) if total_nodes > 0 else 0,
            'total_alerts_24h': len(recent_alerts),
            'critical_alerts_24h': critical_alerts,
            'system_health': self._calculate_system_health()
        }
    
    def _get_node_status_summary(self) -> Dict[str, Any]:
        """Get node status summary with geographical distribution."""
        node_status = {
            'by_type': defaultdict(lambda: {'total': 0, 'active': 0, 'inactive': 0}),
            'by_location': defaultdict(lambda: {'total': 0, 'active': 0, 'inactive': 0}),
            'recent_changes': []
        }
        
        for node_id, node in self.coordinator.nodes.items():
            node_type = node.node_type
            location = node.location.get('zone', 'unknown') if node.location else 'unknown'
            
            # Count by type
            node_status['by_type'][node_type]['total'] += 1
            if node.status == 'active':
                node_status['by_type'][node_type]['active'] += 1
            else:
                node_status['by_type'][node_type]['inactive'] += 1
            
            # Count by location
            node_status['by_location'][location]['total'] += 1
            if node.status == 'active':
                node_status['by_location'][location]['active'] += 1
            else:
                node_status['by_location'][location]['inactive'] += 1
        
        # Convert defaultdict to regular dict
        node_status['by_type'] = dict(node_status['by_type'])
        node_status['by_location'] = dict(node_status['by_location'])
        
        return node_status
    
    def _get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary with trends."""
        alerts_24h = self.coordinator.get_alerts(hours=24)
        alerts_1h = self.coordinator.get_alerts(hours=1)
        
        # Group by severity
        severity_counts = defaultdict(int)
        for alert in alerts_24h:
            severity_counts[alert.severity] += 1
        
        # Group by type
        type_counts = defaultdict(int)
        for alert in alerts_24h:
            type_counts[alert.alert_type] += 1
        
        # Get trend (comparing last hour to previous hour)
        alerts_2h = self.coordinator.get_alerts(hours=2)
        alerts_prev_hour = [a for a in alerts_2h if a.timestamp < datetime.now() - timedelta(hours=1)]
        
        trend = 'stable'
        if len(alerts_1h) > len(alerts_prev_hour):
            trend = 'increasing'
        elif len(alerts_1h) < len(alerts_prev_hour):
            trend = 'decreasing'
        
        return {
            'total_24h': len(alerts_24h),
            'total_1h': len(alerts_1h),
            'by_severity': dict(severity_counts),
            'by_type': dict(type_counts),
            'trend': trend,
            'recent_alerts': [alert.to_dict() for alert in alerts_1h[-10:]]  # Last 10 alerts
        }
    
    def _get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary with averages and trends."""
        metrics = self.coordinator.get_system_metrics(hours=1)
        
        if not metrics:
            return {'error': 'No metrics available'}
        
        # Calculate averages
        cpu_values = [m.get('cpu_usage', 0) for m in metrics if 'cpu_usage' in m]
        memory_values = [m.get('memory_usage', 0) for m in metrics if 'memory_usage' in m]
        network_values = [m.get('network_usage', 0) for m in metrics if 'network_usage' in m]
        
        return {
            'avg_cpu_usage': statistics.mean(cpu_values) if cpu_values else 0,
            'avg_memory_usage': statistics.mean(memory_values) if memory_values else 0,
            'avg_network_usage': statistics.mean(network_values) if network_values else 0,
            'max_cpu_usage': max(cpu_values) if cpu_values else 0,
            'max_memory_usage': max(memory_values) if memory_values else 0,
            'data_points': len(metrics),
            'time_range': '1 hour'
        }
    
    def _get_traffic_data(self) -> Dict[str, Any]:
        """Get traffic-related data and analytics."""
        traffic_nodes = [node for node in self.coordinator.nodes.values() 
                        if 'traffic' in node.capabilities]
        
        # Simulate traffic data aggregation
        traffic_data = {
            'total_vehicles_detected': 0,
            'average_speed': 0,
            'congestion_level': 'low',
            'incidents': 0,
            'flow_by_location': {},
            'peak_hours': []
        }
        
        # In a real implementation, this would aggregate actual traffic data
        for node in traffic_nodes:
            if hasattr(node, 'last_data') and node.last_data:
                # Process traffic data from node
                pass
        
        return traffic_data
    
    def _get_environmental_data(self) -> Dict[str, Any]:
        """Get environmental monitoring data."""
        env_nodes = [node for node in self.coordinator.nodes.values() 
                    if 'environmental' in node.capabilities]
        
        # Simulate environmental data aggregation
        env_data = {
            'air_quality_index': 0,
            'average_temperature': 0,
            'humidity': 0,
            'noise_level': 0,
            'pollution_alerts': 0,
            'by_location': {},
            'trends': {
                'temperature': 'stable',
                'air_quality': 'good',
                'noise': 'normal'
            }
        }
        
        # In a real implementation, this would aggregate actual environmental data
        for node in env_nodes:
            if hasattr(node, 'last_data') and node.last_data:
                # Process environmental data from node
                pass
        
        return env_data
    
    def _get_crime_data(self) -> Dict[str, Any]:
        """Get crime detection and security data."""
        crime_nodes = [node for node in self.coordinator.nodes.values() 
                      if 'crime' in node.capabilities]
        
        # Simulate crime data aggregation
        crime_data = {
            'incidents_24h': 0,
            'risk_level': 'low',
            'patrol_alerts': 0,
            'hotspots': [],
            'by_type': {
                'suspicious_activity': 0,
                'violence': 0,
                'theft': 0,
                'vandalism': 0
            },
            'response_time': 0
        }
        
        # In a real implementation, this would aggregate actual crime detection data
        for node in crime_nodes:
            if hasattr(node, 'last_data') and node.last_data:
                # Process crime data from node
                pass
        
        return crime_data
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        return {
            'data_processing_rate': self._calculate_processing_rate(),
            'response_time': self._calculate_response_time(),
            'throughput': self._calculate_throughput(),
            'error_rate': self._calculate_error_rate(),
            'availability': self._calculate_availability()
        }
    
    def _calculate_system_health(self) -> str:
        """Calculate overall system health."""
        total_nodes = len(self.coordinator.nodes)
        active_nodes = sum(1 for node in self.coordinator.nodes.values() if node.status == 'active')
        
        if total_nodes == 0:
            return 'unknown'
        
        uptime_percentage = (active_nodes / total_nodes) * 100
        
        if uptime_percentage >= 95:
            return 'excellent'
        elif uptime_percentage >= 80:
            return 'good'
        elif uptime_percentage >= 60:
            return 'fair'
        else:
            return 'poor'
    
    def _calculate_processing_rate(self) -> float:
        """Calculate data processing rate."""
        # Simulate processing rate calculation
        return 1500.0  # messages per second
    
    def _calculate_response_time(self) -> float:
        """Calculate average response time."""
        # Simulate response time calculation
        return 0.05  # seconds
    
    def _calculate_throughput(self) -> float:
        """Calculate system throughput."""
        # Simulate throughput calculation
        return 98.5  # percentage
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate."""
        # Simulate error rate calculation
        return 0.01  # percentage
    
    def _calculate_availability(self) -> float:
        """Calculate system availability."""
        # Simulate availability calculation
        return 99.9  # percentage
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache is still valid."""
        if key not in self.cache or key not in self.last_cache_update:
            return False
        
        age = (datetime.now() - self.last_cache_update[key]).total_seconds()
        return age < self.cache_ttl
    
    def invalidate_cache(self, key: Optional[str] = None):
        """Invalidate cache."""
        if key:
            self.cache.pop(key, None)
            self.last_cache_update.pop(key, None)
        else:
            self.cache.clear()
            self.last_cache_update.clear()
    
    def get_real_time_data(self) -> Dict[str, Any]:
        """Get real-time data for live updates."""
        return {
            'timestamp': datetime.now().isoformat(),
            'active_nodes': sum(1 for node in self.coordinator.nodes.values() if node.status == 'active'),
            'recent_alerts': len(self.coordinator.get_alerts(hours=1)),
            'system_load': self._get_current_system_load(),
            'data_flow': self._get_data_flow_rate()
        }
    
    def _get_current_system_load(self) -> float:
        """Get current system load."""
        # Simulate current system load
        return 45.2  # percentage
    
    def _get_data_flow_rate(self) -> float:
        """Get current data flow rate."""
        # Simulate data flow rate
        return 1200.0  # messages per second
