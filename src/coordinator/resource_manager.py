"""
Resource management for the central coordinator.
Handles resource allocation, optimization, and load balancing across edge nodes.
"""
import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import threading
from dataclasses import dataclass
from enum import Enum

from ..common.logger import setup_logger
from ..common.models import EdgeNode, NodeStatus

logger = setup_logger(__name__)

class ResourceType(Enum):
    """Types of resources that can be managed."""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    GPU = "gpu"
    POWER = "power"

@dataclass
class ResourceAllocation:
    """Resource allocation for a node."""
    node_id: str
    resource_type: ResourceType
    allocated: float
    limit: float
    usage: float
    timestamp: datetime
    
    @property
    def utilization(self) -> float:
        """Calculate utilization percentage."""
        return (self.usage / self.limit) * 100 if self.limit > 0 else 0
    
    @property
    def available(self) -> float:
        """Calculate available resources."""
        return max(0, self.limit - self.usage)

@dataclass
class ResourceQuota:
    """Resource quota for a node or service."""
    name: str
    cpu_limit: float = 0.0
    memory_limit: float = 0.0  # MB
    storage_limit: float = 0.0  # GB
    network_limit: float = 0.0  # Mbps
    gpu_limit: float = 0.0
    power_limit: float = 0.0  # Watts

@dataclass
class LoadBalancingRule:
    """Load balancing rule configuration."""
    rule_id: str
    name: str
    target_services: List[str]
    balancing_strategy: str  # round_robin, least_connections, resource_based
    health_check_interval: int = 30  # seconds
    enabled: bool = True

class ResourceManager:
    """Central resource management system."""
    
    def __init__(self, coordinator_core):
        self.coordinator = coordinator_core
        self.resource_allocations = {}  # node_id -> {resource_type -> ResourceAllocation}
        self.resource_quotas = {}  # node_id -> ResourceQuota
        self.load_balancing_rules = {}
        self.resource_history = defaultdict(list)
        self.optimization_schedules = {}
        self.resource_locks = {}
        self.metrics = {
            'total_allocations': 0,
            'failed_allocations': 0,
            'optimization_runs': 0,
            'load_balancing_events': 0
        }
        
        self.setup_default_quotas()
        self.setup_load_balancing_rules()
        self.start_background_tasks()
    
    def setup_default_quotas(self):
        """Setup default resource quotas."""
        # Default quotas for different node types
        self.default_quotas = {
            'traffic_monitor': ResourceQuota(
                name='traffic_monitor',
                cpu_limit=2.0,
                memory_limit=4096,
                storage_limit=100,
                network_limit=100,
                power_limit=150
            ),
            'environmental_sensor': ResourceQuota(
                name='environmental_sensor',
                cpu_limit=1.0,
                memory_limit=2048,
                storage_limit=50,
                network_limit=50,
                power_limit=100
            ),
            'crime_detector': ResourceQuota(
                name='crime_detector',
                cpu_limit=4.0,
                memory_limit=8192,
                storage_limit=200,
                network_limit=200,
                gpu_limit=1.0,
                power_limit=300
            ),
            'edge_gateway': ResourceQuota(
                name='edge_gateway',
                cpu_limit=8.0,
                memory_limit=16384,
                storage_limit=500,
                network_limit=1000,
                power_limit=400
            )
        }
    
    def setup_load_balancing_rules(self):
        """Setup load balancing rules."""
        self.load_balancing_rules = {
            'traffic_processing': LoadBalancingRule(
                rule_id='traffic_processing',
                name='Traffic Data Processing',
                target_services=['traffic_ai_processor'],
                balancing_strategy='resource_based',
                health_check_interval=30
            ),
            'environmental_analysis': LoadBalancingRule(
                rule_id='environmental_analysis',
                name='Environmental Data Analysis',
                target_services=['environmental_ai_processor'],
                balancing_strategy='least_connections',
                health_check_interval=60
            ),
            'crime_detection': LoadBalancingRule(
                rule_id='crime_detection',
                name='Crime Detection Processing',
                target_services=['crime_ai_processor'],
                balancing_strategy='resource_based',
                health_check_interval=15
            ),
            'data_aggregation': LoadBalancingRule(
                rule_id='data_aggregation',
                name='Data Aggregation',
                target_services=['data_aggregator'],
                balancing_strategy='round_robin',
                health_check_interval=30
            )
        }
    
    def start_background_tasks(self):
        """Start background tasks for resource management."""
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()
        
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
    
    def register_node_resources(self, node_id: str, node_type: str, 
                              resources: Dict[str, float]) -> bool:
        """Register node resources."""
        try:
            # Get or create quota for this node
            quota = self.resource_quotas.get(node_id)
            if not quota:
                default_quota = self.default_quotas.get(node_type)
                if default_quota:
                    quota = ResourceQuota(
                        name=f"{node_type}_{node_id}",
                        cpu_limit=default_quota.cpu_limit,
                        memory_limit=default_quota.memory_limit,
                        storage_limit=default_quota.storage_limit,
                        network_limit=default_quota.network_limit,
                        gpu_limit=default_quota.gpu_limit,
                        power_limit=default_quota.power_limit
                    )
                    self.resource_quotas[node_id] = quota
                else:
                    # Create default quota
                    quota = ResourceQuota(name=f"default_{node_id}")
                    self.resource_quotas[node_id] = quota
            
            # Initialize resource allocations
            self.resource_allocations[node_id] = {}
            
            for resource_name, limit in resources.items():
                try:
                    resource_type = ResourceType(resource_name.lower())
                    allocation = ResourceAllocation(
                        node_id=node_id,
                        resource_type=resource_type,
                        allocated=0.0,
                        limit=limit,
                        usage=0.0,
                        timestamp=datetime.now()
                    )
                    self.resource_allocations[node_id][resource_type] = allocation
                except ValueError:
                    logger.warning(f"Unknown resource type: {resource_name}")
            
            logger.info(f"Resources registered for node {node_id}: {resources}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering node resources: {e}")
            return False
    
    def update_resource_usage(self, node_id: str, resource_usage: Dict[str, float]) -> bool:
        """Update resource usage for a node."""
        try:
            if node_id not in self.resource_allocations:
                logger.warning(f"Node {node_id} not registered for resource management")
                return False
            
            node_allocations = self.resource_allocations[node_id]
            
            for resource_name, usage in resource_usage.items():
                try:
                    resource_type = ResourceType(resource_name.lower())
                    if resource_type in node_allocations:
                        allocation = node_allocations[resource_type]
                        allocation.usage = usage
                        allocation.timestamp = datetime.now()
                        
                        # Store usage history
                        self.resource_history[f"{node_id}_{resource_type.value}"].append({
                            'timestamp': datetime.now(),
                            'usage': usage,
                            'utilization': allocation.utilization
                        })
                        
                        # Keep only last 1000 entries
                        if len(self.resource_history[f"{node_id}_{resource_type.value}"]) > 1000:
                            self.resource_history[f"{node_id}_{resource_type.value}"].pop(0)
                        
                        # Check for resource alerts
                        if allocation.utilization > 90:
                            self._trigger_resource_alert_sync(node_id, resource_type, allocation)
                        
                except ValueError:
                    logger.warning(f"Unknown resource type: {resource_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating resource usage: {e}")
            return False
    
    def allocate_resources(self, node_id: str, service_name: str, 
                          resource_requirements: Dict[str, float]) -> bool:
        """Allocate resources for a service on a node."""
        try:
            if node_id not in self.resource_allocations:
                logger.warning(f"Node {node_id} not registered for resource management")
                return False
            
            node_allocations = self.resource_allocations[node_id]
            
            # Check if resources are available
            for resource_name, required in resource_requirements.items():
                try:
                    resource_type = ResourceType(resource_name.lower())
                    if resource_type in node_allocations:
                        allocation = node_allocations[resource_type]
                        if allocation.available < required:
                            logger.warning(f"Insufficient {resource_name} on node {node_id}")
                            return False
                except ValueError:
                    logger.warning(f"Unknown resource type: {resource_name}")
                    return False
            
            # Allocate resources
            for resource_name, required in resource_requirements.items():
                resource_type = ResourceType(resource_name.lower())
                if resource_type in node_allocations:
                    allocation = node_allocations[resource_type]
                    allocation.allocated += required
            
            self.metrics['total_allocations'] += 1
            logger.info(f"Resources allocated for {service_name} on node {node_id}: {resource_requirements}")
            return True
            
        except Exception as e:
            logger.error(f"Error allocating resources: {e}")
            self.metrics['failed_allocations'] += 1
            return False
    
    def deallocate_resources(self, node_id: str, service_name: str, 
                           resource_requirements: Dict[str, float]) -> bool:
        """Deallocate resources for a service on a node."""
        try:
            if node_id not in self.resource_allocations:
                logger.warning(f"Node {node_id} not registered for resource management")
                return False
            
            node_allocations = self.resource_allocations[node_id]
            
            # Deallocate resources
            for resource_name, required in resource_requirements.items():
                try:
                    resource_type = ResourceType(resource_name.lower())
                    if resource_type in node_allocations:
                        allocation = node_allocations[resource_type]
                        allocation.allocated = max(0, allocation.allocated - required)
                except ValueError:
                    logger.warning(f"Unknown resource type: {resource_name}")
            
            logger.info(f"Resources deallocated for {service_name} on node {node_id}: {resource_requirements}")
            return True
            
        except Exception as e:
            logger.error(f"Error deallocating resources: {e}")
            return False
    
    def find_optimal_node(self, resource_requirements: Dict[str, float], 
                         node_filter: Optional[List[str]] = None) -> Optional[str]:
        """Find the optimal node for resource allocation."""
        try:
            available_nodes = []
            
            for node_id, node_allocations in self.resource_allocations.items():
                # Skip nodes not in filter
                if node_filter and node_id not in node_filter:
                    continue
                
                # Check if node is active
                node = self.coordinator.nodes.get(node_id)
                if not node or node.status != 'active':
                    continue
                
                # Check if resources are available
                can_allocate = True
                total_utilization = 0
                resource_count = 0
                
                for resource_name, required in resource_requirements.items():
                    try:
                        resource_type = ResourceType(resource_name.lower())
                        if resource_type in node_allocations:
                            allocation = node_allocations[resource_type]
                            if allocation.available < required:
                                can_allocate = False
                                break
                            total_utilization += allocation.utilization
                            resource_count += 1
                    except ValueError:
                        continue
                
                if can_allocate and resource_count > 0:
                    avg_utilization = total_utilization / resource_count
                    available_nodes.append((node_id, avg_utilization))
            
            if not available_nodes:
                return None
            
            # Sort by lowest utilization (best fit)
            available_nodes.sort(key=lambda x: x[1])
            return available_nodes[0][0]
            
        except Exception as e:
            logger.error(f"Error finding optimal node: {e}")
            return None
    
    def balance_load(self, service_name: str) -> List[str]:
        """Balance load for a service across available nodes."""
        try:
            # Find load balancing rule
            rule = None
            for r in self.load_balancing_rules.values():
                if service_name in r.target_services:
                    rule = r
                    break
            
            if not rule or not rule.enabled:
                return []
            
            # Get healthy nodes
            healthy_nodes = []
            for node_id, node in self.coordinator.nodes.items():
                if node.status == 'active' and node_id in self.resource_allocations:
                    healthy_nodes.append(node_id)
            
            if not healthy_nodes:
                return []
            
            # Apply balancing strategy
            if rule.balancing_strategy == 'round_robin':
                return self._balance_round_robin(healthy_nodes)
            elif rule.balancing_strategy == 'least_connections':
                return self._balance_least_connections(healthy_nodes, service_name)
            elif rule.balancing_strategy == 'resource_based':
                return self._balance_resource_based(healthy_nodes)
            else:
                return healthy_nodes
                
        except Exception as e:
            logger.error(f"Error balancing load: {e}")
            return []
    
    def _balance_round_robin(self, nodes: List[str]) -> List[str]:
        """Round-robin load balancing."""
        # Simple round-robin
        return nodes
    
    def _balance_least_connections(self, nodes: List[str], service_name: str) -> List[str]:
        """Least connections load balancing."""
        # Sort by connection count (simplified)
        return sorted(nodes, key=lambda x: len(self.coordinator.get_node_connections(x)))
    
    def _balance_resource_based(self, nodes: List[str]) -> List[str]:
        """Resource-based load balancing."""
        # Sort by average resource utilization
        node_utilizations = []
        
        for node_id in nodes:
            allocations = self.resource_allocations.get(node_id, {})
            if allocations:
                total_util = sum(alloc.utilization for alloc in allocations.values())
                avg_util = total_util / len(allocations)
                node_utilizations.append((node_id, avg_util))
        
        # Sort by lowest utilization first
        node_utilizations.sort(key=lambda x: x[1])
        return [node_id for node_id, _ in node_utilizations]
    
    def optimize_resources(self) -> Dict[str, Any]:
        """Optimize resource allocation across nodes."""
        try:
            optimization_results = {
                'optimizations_applied': 0,
                'nodes_optimized': 0,
                'recommendations': []
            }
            
            # Find nodes with high resource utilization
            high_util_nodes = []
            for node_id, allocations in self.resource_allocations.items():
                avg_util = sum(alloc.utilization for alloc in allocations.values()) / len(allocations)
                if avg_util > 80:  # High utilization threshold
                    high_util_nodes.append((node_id, avg_util))
            
            # Generate optimization recommendations
            for node_id, utilization in high_util_nodes:
                recommendations = self._generate_optimization_recommendations(node_id)
                optimization_results['recommendations'].extend(recommendations)
                optimization_results['nodes_optimized'] += 1
            
            # Apply automatic optimizations
            for recommendation in optimization_results['recommendations']:
                if recommendation.get('auto_apply', False):
                    if self._apply_optimization(recommendation):
                        optimization_results['optimizations_applied'] += 1
            
            self.metrics['optimization_runs'] += 1
            logger.info(f"Resource optimization completed: {optimization_results}")
            return optimization_results
            
        except Exception as e:
            logger.error(f"Error optimizing resources: {e}")
            return {'error': str(e)}
    
    def _generate_optimization_recommendations(self, node_id: str) -> List[Dict[str, Any]]:
        """Generate optimization recommendations for a node."""
        recommendations = []
        
        allocations = self.resource_allocations.get(node_id, {})
        node = self.coordinator.nodes.get(node_id)
        
        if not allocations or not node:
            return recommendations
        
        # Check for resource bottlenecks
        for resource_type, allocation in allocations.items():
            if allocation.utilization > 90:
                recommendations.append({
                    'type': 'scale_up',
                    'node_id': node_id,
                    'resource_type': resource_type.value,
                    'current_utilization': allocation.utilization,
                    'recommendation': f'Increase {resource_type.value} capacity',
                    'auto_apply': False
                })
            elif allocation.utilization < 20:
                recommendations.append({
                    'type': 'scale_down',
                    'node_id': node_id,
                    'resource_type': resource_type.value,
                    'current_utilization': allocation.utilization,
                    'recommendation': f'Reduce {resource_type.value} allocation',
                    'auto_apply': True
                })
        
        # Check for load balancing opportunities
        if self._should_rebalance_node(node_id):
            recommendations.append({
                'type': 'rebalance',
                'node_id': node_id,
                'recommendation': 'Rebalance workload to other nodes',
                'auto_apply': False
            })
        
        return recommendations
    
    def _apply_optimization(self, recommendation: Dict[str, Any]) -> bool:
        """Apply an optimization recommendation."""
        try:
            if recommendation['type'] == 'scale_down':
                # Reduce resource allocation
                node_id = recommendation['node_id']
                resource_type = ResourceType(recommendation['resource_type'])
                
                if node_id in self.resource_allocations:
                    allocation = self.resource_allocations[node_id].get(resource_type)
                    if allocation:
                        # Reduce allocated resources by 10%
                        reduction = allocation.allocated * 0.1
                        allocation.allocated = max(0, allocation.allocated - reduction)
                        logger.info(f"Applied scale-down optimization for {node_id}: {resource_type.value}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error applying optimization: {e}")
            return False
    
    def _should_rebalance_node(self, node_id: str) -> bool:
        """Check if node should be rebalanced."""
        allocations = self.resource_allocations.get(node_id, {})
        if not allocations:
            return False
        
        avg_util = sum(alloc.utilization for alloc in allocations.values()) / len(allocations)
        return avg_util > 85
    
    def _trigger_resource_alert_sync(self, node_id: str, resource_type: ResourceType, 
                                    allocation: ResourceAllocation):
        """Trigger resource alert synchronously."""
        try:
            if hasattr(self.coordinator, 'alert_manager'):
                # Create alert data
                alert_data = {
                    'alert_type': 'resource_utilization',
                    'severity': 'medium',
                    'message': f'High {resource_type.value} utilization on node {node_id}: {allocation.utilization:.1f}%',
                    'source_node': node_id,
                    'data': {
                        'resource_type': resource_type.value,
                        'utilization': allocation.utilization,
                        'usage': allocation.usage,
                        'limit': allocation.limit
                    }
                }
                # Add to coordinator's alert queue for processing
                logger.warning(f"Resource alert: {alert_data['message']}")
        except Exception as e:
            logger.error(f"Error triggering resource alert: {e}")
    
    async def _trigger_resource_alert(self, node_id: str, resource_type: ResourceType, 
                                    allocation: ResourceAllocation):
        """Trigger resource alert."""
        if hasattr(self.coordinator, 'alert_manager'):
            await self.coordinator.alert_manager.create_alert(
                alert_type='resource_utilization',
                severity='medium',
                message=f'High {resource_type.value} utilization on node {node_id}: {allocation.utilization:.1f}%',
                source_node=node_id,
                data={
                    'resource_type': resource_type.value,
                    'utilization': allocation.utilization,
                    'usage': allocation.usage,
                    'limit': allocation.limit
                }
            )
    
    def _optimization_loop(self):
        """Background optimization loop."""
        while True:
            try:
                # Run optimization every 10 minutes
                time.sleep(600)
                self.optimize_resources()
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                time.sleep(600)
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                # Monitor resource usage every 30 seconds
                time.sleep(30)
                self._monitor_resource_thresholds()
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)
    
    def _monitor_resource_thresholds(self):
        """Monitor resource thresholds."""
        for node_id, allocations in self.resource_allocations.items():
            for resource_type, allocation in allocations.items():
                if allocation.utilization > 95:
                    logger.warning(f"Critical resource utilization on {node_id}: {resource_type.value} at {allocation.utilization:.1f}%")
    
    def _cleanup_loop(self):
        """Background cleanup loop."""
        while True:
            try:
                # Clean up old resource history
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                for key in list(self.resource_history.keys()):
                    self.resource_history[key] = [
                        entry for entry in self.resource_history[key]
                        if entry['timestamp'] >= cutoff_time
                    ]
                
                time.sleep(3600)  # Run cleanup every hour
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                time.sleep(3600)
    
    def get_resource_status(self, node_id: str = None) -> Dict[str, Any]:
        """Get resource status for nodes."""
        if node_id:
            # Get status for specific node
            allocations = self.resource_allocations.get(node_id, {})
            return {
                'node_id': node_id,
                'resources': {
                    resource_type.value: {
                        'allocated': allocation.allocated,
                        'usage': allocation.usage,
                        'limit': allocation.limit,
                        'utilization': allocation.utilization,
                        'available': allocation.available
                    }
                    for resource_type, allocation in allocations.items()
                }
            }
        else:
            # Get status for all nodes
            return {
                node_id: {
                    'resources': {
                        resource_type.value: {
                            'allocated': allocation.allocated,
                            'usage': allocation.usage,
                            'limit': allocation.limit,
                            'utilization': allocation.utilization,
                            'available': allocation.available
                        }
                        for resource_type, allocation in allocations.items()
                    }
                }
                for node_id, allocations in self.resource_allocations.items()
            }
    
    def get_resource_history(self, node_id: str, resource_type: str, 
                           hours: int = 1) -> List[Dict[str, Any]]:
        """Get resource usage history."""
        key = f"{node_id}_{resource_type}"
        if key not in self.resource_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            entry for entry in self.resource_history[key]
            if entry['timestamp'] >= cutoff_time
        ]
    
    def get_management_metrics(self) -> Dict[str, Any]:
        """Get resource management metrics."""
        return self.metrics.copy()
