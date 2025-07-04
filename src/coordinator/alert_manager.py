"""
Alert management system for the central coordinator.
Handles alert generation, prioritization, notification, and response coordination.
"""
import json
import logging
import time
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import threading
from enum import Enum
from dataclasses import dataclass, field

from ..common.logger import setup_logger
from ..common.models import Alert, AlertStatus, AlertSeverity

logger = setup_logger(__name__)

class AlertPriority(Enum):
    """Alert priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5

@dataclass
class AlertRule:
    """Alert rule configuration."""
    rule_id: str
    name: str
    conditions: Dict[str, Any]
    alert_type: str
    severity: AlertSeverity
    cooldown_minutes: int = 5
    enabled: bool = True
    notification_channels: List[str] = field(default_factory=list)

@dataclass
class AlertResponse:
    """Alert response configuration."""
    alert_type: str
    response_actions: List[str]
    auto_escalate_minutes: int = 30
    requires_human_intervention: bool = False

class AlertManager:
    """Central alert management system."""
    
    def __init__(self, coordinator_core):
        self.coordinator = coordinator_core
        self.alerts = {}  # alert_id -> Alert
        self.alert_history = []
        self.alert_rules = {}
        self.alert_responses = {}
        self.active_alerts = set()
        self.suppressed_alerts = set()
        self.notification_channels = {}
        self.escalation_queue = asyncio.Queue()
        self.alert_counters = defaultdict(int)
        self.cooldown_tracker = {}
        
        self.setup_default_rules()
        self.setup_notification_channels()
        self.start_background_tasks()
    
    def setup_default_rules(self):
        """Setup default alert rules."""
        self.alert_rules = {
            'traffic_congestion': AlertRule(
                rule_id='traffic_congestion',
                name='Traffic Congestion Detection',
                conditions={
                    'congestion_level': 'high',
                    'duration_minutes': 10
                },
                alert_type='traffic_congestion',
                severity=AlertSeverity.MEDIUM,
                cooldown_minutes=15,
                notification_channels=['dashboard', 'traffic_management']
            ),
            'air_quality_unhealthy': AlertRule(
                rule_id='air_quality_unhealthy',
                name='Unhealthy Air Quality',
                conditions={
                    'air_quality_index': {'gt': 150}
                },
                alert_type='air_quality',
                severity=AlertSeverity.HIGH,
                cooldown_minutes=30,
                notification_channels=['dashboard', 'environmental_agency', 'public_health']
            ),
            'security_threat': AlertRule(
                rule_id='security_threat',
                name='Security Threat Detection',
                conditions={
                    'threat_score': {'gt': 0.8}
                },
                alert_type='security_threat',
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=5,
                notification_channels=['dashboard', 'security_team', 'emergency_services']
            ),
            'system_failure': AlertRule(
                rule_id='system_failure',
                name='System Component Failure',
                conditions={
                    'health_score': {'lt': 0.3}
                },
                alert_type='system_health',
                severity=AlertSeverity.HIGH,
                cooldown_minutes=10,
                notification_channels=['dashboard', 'technical_team']
            ),
            'node_offline': AlertRule(
                rule_id='node_offline',
                name='Node Offline',
                conditions={
                    'status': 'offline',
                    'duration_minutes': 5
                },
                alert_type='node_status',
                severity=AlertSeverity.MEDIUM,
                cooldown_minutes=20,
                notification_channels=['dashboard', 'technical_team']
            )
        }
        
        # Setup alert responses
        self.alert_responses = {
            'traffic_congestion': AlertResponse(
                alert_type='traffic_congestion',
                response_actions=['notify_traffic_control', 'suggest_alternative_routes'],
                auto_escalate_minutes=30,
                requires_human_intervention=False
            ),
            'air_quality': AlertResponse(
                alert_type='air_quality',
                response_actions=['notify_public_health', 'issue_health_advisory'],
                auto_escalate_minutes=60,
                requires_human_intervention=True
            ),
            'security_threat': AlertResponse(
                alert_type='security_threat',
                response_actions=['notify_security', 'dispatch_patrol', 'activate_emergency_protocols'],
                auto_escalate_minutes=5,
                requires_human_intervention=True
            ),
            'system_health': AlertResponse(
                alert_type='system_health',
                response_actions=['restart_services', 'notify_technical_team'],
                auto_escalate_minutes=15,
                requires_human_intervention=False
            ),
            'node_status': AlertResponse(
                alert_type='node_status',
                response_actions=['ping_node', 'notify_technical_team'],
                auto_escalate_minutes=10,
                requires_human_intervention=False
            )
        }
    
    def setup_notification_channels(self):
        """Setup notification channels."""
        self.notification_channels = {
            'dashboard': {'type': 'websocket', 'enabled': True},
            'email': {'type': 'email', 'enabled': True, 'recipients': []},
            'sms': {'type': 'sms', 'enabled': True, 'recipients': []},
            'slack': {'type': 'webhook', 'enabled': False, 'webhook_url': ''},
            'traffic_management': {'type': 'api', 'enabled': True, 'endpoint': '/api/traffic/alerts'},
            'environmental_agency': {'type': 'api', 'enabled': True, 'endpoint': '/api/environment/alerts'},
            'public_health': {'type': 'api', 'enabled': True, 'endpoint': '/api/health/alerts'},
            'security_team': {'type': 'api', 'enabled': True, 'endpoint': '/api/security/alerts'},
            'emergency_services': {'type': 'api', 'enabled': True, 'endpoint': '/api/emergency/alerts'},
            'technical_team': {'type': 'api', 'enabled': True, 'endpoint': '/api/technical/alerts'}
        }
    
    def start_background_tasks(self):
        """Start background tasks for alert processing."""
        self.escalation_thread = threading.Thread(target=self._escalation_loop, daemon=True)
        self.escalation_thread.start()
        
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
    
    async def create_alert(self, alert_type: str, severity: AlertSeverity, message: str, 
                          source_node: str = None, data: Dict[str, Any] = None) -> Alert:
        """Create a new alert."""
        alert_id = f"{alert_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            source_node=source_node,
            data=data or {}
        )
        
        return await self.process_alert(alert)
    
    async def process_alert(self, alert: Alert) -> Alert:
        """Process an incoming alert."""
        try:
            # Check if alert should be suppressed
            if self._should_suppress_alert(alert):
                logger.info(f"Alert suppressed: {alert.alert_id}")
                return alert
            
            # Check alert rules
            rule = self.alert_rules.get(alert.alert_type)
            if rule and not rule.enabled:
                logger.info(f"Alert rule disabled: {alert.alert_type}")
                return alert
            
            # Check cooldown
            if self._is_in_cooldown(alert.alert_type, alert.source_node):
                logger.info(f"Alert in cooldown: {alert.alert_type} from {alert.source_node}")
                return alert
            
            # Store alert
            self.alerts[alert.alert_id] = alert
            self.alert_history.append(alert)
            self.active_alerts.add(alert.alert_id)
            
            # Update counters
            self.alert_counters[alert.alert_type] += 1
            
            # Set cooldown
            self._set_cooldown(alert.alert_type, alert.source_node)
            
            # Send notifications
            await self._send_notifications(alert)
            
            # Trigger automated response
            await self._trigger_response(alert)
            
            # Add to escalation queue if needed
            if self._needs_escalation(alert):
                await self.escalation_queue.put(alert)
            
            logger.info(f"Alert processed: {alert.alert_id} - {alert.message}")
            return alert
            
        except Exception as e:
            logger.error(f"Error processing alert {alert.alert_id}: {e}")
            alert.status = AlertStatus.FAILED
            return alert
    
    def _should_suppress_alert(self, alert: Alert) -> bool:
        """Check if alert should be suppressed."""
        # Check if alert type is suppressed
        if alert.alert_type in self.suppressed_alerts:
            return True
        
        # Check for duplicate recent alerts
        recent_alerts = self.get_alerts(hours=1, alert_type=alert.alert_type)
        if len(recent_alerts) > 10:  # Too many similar alerts
            return True
        
        # Check for maintenance mode
        if alert.source_node and self.coordinator.is_node_in_maintenance(alert.source_node):
            return True
        
        return False
    
    def _is_in_cooldown(self, alert_type: str, source_node: str) -> bool:
        """Check if alert type is in cooldown period."""
        cooldown_key = f"{alert_type}_{source_node}"
        if cooldown_key in self.cooldown_tracker:
            cooldown_end = self.cooldown_tracker[cooldown_key]
            return datetime.now() < cooldown_end
        return False
    
    def _set_cooldown(self, alert_type: str, source_node: str):
        """Set cooldown period for alert type."""
        rule = self.alert_rules.get(alert_type)
        if rule:
            cooldown_key = f"{alert_type}_{source_node}"
            cooldown_end = datetime.now() + timedelta(minutes=rule.cooldown_minutes)
            self.cooldown_tracker[cooldown_key] = cooldown_end
    
    async def _send_notifications(self, alert: Alert):
        """Send notifications for an alert."""
        rule = self.alert_rules.get(alert.alert_type)
        if not rule:
            return
        
        for channel_name in rule.notification_channels:
            channel = self.notification_channels.get(channel_name)
            if channel and channel.get('enabled', False):
                try:
                    await self._send_notification(alert, channel_name, channel)
                except Exception as e:
                    logger.error(f"Error sending notification to {channel_name}: {e}")
    
    async def _send_notification(self, alert: Alert, channel_name: str, channel: Dict[str, Any]):
        """Send notification to a specific channel."""
        if channel['type'] == 'websocket':
            # Send to dashboard via WebSocket
            if hasattr(self.coordinator, 'api') and self.coordinator.api:
                self.coordinator.api.emit_alert(alert)
        
        elif channel['type'] == 'email':
            # Send email notification
            await self._send_email_notification(alert, channel)
        
        elif channel['type'] == 'sms':
            # Send SMS notification
            await self._send_sms_notification(alert, channel)
        
        elif channel['type'] == 'webhook':
            # Send webhook notification
            await self._send_webhook_notification(alert, channel)
        
        elif channel['type'] == 'api':
            # Send API notification
            await self._send_api_notification(alert, channel)
        
        logger.info(f"Notification sent to {channel_name} for alert {alert.alert_id}")
    
    async def _send_email_notification(self, alert: Alert, channel: Dict[str, Any]):
        """Send email notification."""
        # Implementation would use an email service
        logger.info(f"Email notification sent for alert {alert.alert_id}")
    
    async def _send_sms_notification(self, alert: Alert, channel: Dict[str, Any]):
        """Send SMS notification."""
        # Implementation would use an SMS service
        logger.info(f"SMS notification sent for alert {alert.alert_id}")
    
    async def _send_webhook_notification(self, alert: Alert, channel: Dict[str, Any]):
        """Send webhook notification."""
        # Implementation would make HTTP request to webhook
        logger.info(f"Webhook notification sent for alert {alert.alert_id}")
    
    async def _send_api_notification(self, alert: Alert, channel: Dict[str, Any]):
        """Send API notification."""
        # Implementation would make API call
        logger.info(f"API notification sent for alert {alert.alert_id}")
    
    async def _trigger_response(self, alert: Alert):
        """Trigger automated response for an alert."""
        response = self.alert_responses.get(alert.alert_type)
        if not response:
            return
        
        for action in response.response_actions:
            try:
                await self._execute_response_action(alert, action)
            except Exception as e:
                logger.error(f"Error executing response action {action}: {e}")
    
    async def _execute_response_action(self, alert: Alert, action: str):
        """Execute a specific response action."""
        if action == 'notify_traffic_control':
            await self._notify_traffic_control(alert)
        elif action == 'suggest_alternative_routes':
            await self._suggest_alternative_routes(alert)
        elif action == 'notify_public_health':
            await self._notify_public_health(alert)
        elif action == 'issue_health_advisory':
            await self._issue_health_advisory(alert)
        elif action == 'notify_security':
            await self._notify_security(alert)
        elif action == 'dispatch_patrol':
            await self._dispatch_patrol(alert)
        elif action == 'activate_emergency_protocols':
            await self._activate_emergency_protocols(alert)
        elif action == 'restart_services':
            await self._restart_services(alert)
        elif action == 'notify_technical_team':
            await self._notify_technical_team(alert)
        elif action == 'ping_node':
            await self._ping_node(alert)
        else:
            logger.warning(f"Unknown response action: {action}")
    
    # Response action implementations (simplified)
    async def _notify_traffic_control(self, alert: Alert):
        """Notify traffic control systems."""
        logger.info(f"Traffic control notified for alert {alert.alert_id}")
    
    async def _suggest_alternative_routes(self, alert: Alert):
        """Suggest alternative routes."""
        logger.info(f"Alternative routes suggested for alert {alert.alert_id}")
    
    async def _notify_public_health(self, alert: Alert):
        """Notify public health authorities."""
        logger.info(f"Public health notified for alert {alert.alert_id}")
    
    async def _issue_health_advisory(self, alert: Alert):
        """Issue health advisory."""
        logger.info(f"Health advisory issued for alert {alert.alert_id}")
    
    async def _notify_security(self, alert: Alert):
        """Notify security teams."""
        logger.info(f"Security team notified for alert {alert.alert_id}")
    
    async def _dispatch_patrol(self, alert: Alert):
        """Dispatch security patrol."""
        logger.info(f"Patrol dispatched for alert {alert.alert_id}")
    
    async def _activate_emergency_protocols(self, alert: Alert):
        """Activate emergency protocols."""
        logger.info(f"Emergency protocols activated for alert {alert.alert_id}")
    
    async def _restart_services(self, alert: Alert):
        """Restart system services."""
        logger.info(f"Services restarted for alert {alert.alert_id}")
    
    async def _notify_technical_team(self, alert: Alert):
        """Notify technical team."""
        logger.info(f"Technical team notified for alert {alert.alert_id}")
    
    async def _ping_node(self, alert: Alert):
        """Ping node to check status."""
        if alert.source_node:
            result = await self.coordinator.ping_node(alert.source_node)
            logger.info(f"Node ping result for {alert.source_node}: {result}")
    
    def _needs_escalation(self, alert: Alert) -> bool:
        """Check if alert needs escalation."""
        return alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]
    
    def _escalation_loop(self):
        """Background loop for alert escalation."""
        while True:
            try:
                # Process escalation queue
                # This would be implemented with proper async queue processing
                time.sleep(10)
            except Exception as e:
                logger.error(f"Error in escalation loop: {e}")
                time.sleep(60)
    
    def _cleanup_loop(self):
        """Background loop for alert cleanup."""
        while True:
            try:
                # Clean up old alerts
                cutoff_time = datetime.now() - timedelta(days=7)
                
                # Remove old alerts from history
                self.alert_history = [
                    alert for alert in self.alert_history 
                    if alert.timestamp >= cutoff_time
                ]
                
                # Clean up cooldown tracker
                current_time = datetime.now()
                expired_cooldowns = [
                    key for key, end_time in self.cooldown_tracker.items()
                    if current_time >= end_time
                ]
                for key in expired_cooldowns:
                    del self.cooldown_tracker[key]
                
                logger.info(f"Alert cleanup completed. Removed {len(expired_cooldowns)} expired cooldowns")
                
                time.sleep(3600)  # Run cleanup every hour
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                time.sleep(3600)
    
    def get_alerts(self, hours: int = 24, severity: AlertSeverity = None, 
                  alert_type: str = None, status: AlertStatus = None) -> List[Alert]:
        """Get alerts based on criteria."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        alerts = [
            alert for alert in self.alert_history
            if alert.timestamp >= cutoff_time
        ]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        if alert_type:
            alerts = [alert for alert in alerts if alert.alert_type == alert_type]
        
        if status:
            alerts = [alert for alert in alerts if alert.status == status]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        return self.alerts.get(alert_id)
    
    def update_alert_status(self, alert_id: str, status: AlertStatus, notes: str = None) -> bool:
        """Update alert status."""
        alert = self.alerts.get(alert_id)
        if not alert:
            return False
        
        alert.status = status
        if notes:
            alert.notes = notes
        
        if status in [AlertStatus.RESOLVED, AlertStatus.DISMISSED]:
            self.active_alerts.discard(alert_id)
        
        logger.info(f"Alert {alert_id} status updated to {status}")
        return True
    
    def suppress_alert_type(self, alert_type: str):
        """Suppress alerts of a specific type."""
        self.suppressed_alerts.add(alert_type)
        logger.info(f"Alert type {alert_type} suppressed")
    
    def unsuppress_alert_type(self, alert_type: str):
        """Unsuppress alerts of a specific type."""
        self.suppressed_alerts.discard(alert_type)
        logger.info(f"Alert type {alert_type} unsuppressed")
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        total_alerts = len(self.alert_history)
        active_count = len(self.active_alerts)
        
        severity_counts = defaultdict(int)
        type_counts = defaultdict(int)
        
        for alert in self.alert_history:
            severity_counts[alert.severity.value] += 1
            type_counts[alert.alert_type] += 1
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': active_count,
            'alerts_by_severity': dict(severity_counts),
            'alerts_by_type': dict(type_counts),
            'suppressed_types': list(self.suppressed_alerts),
            'cooldowns_active': len(self.cooldown_tracker)
        }
    
    def get_new_alerts(self, since_minutes: int = 5) -> List[Alert]:
        """Get new alerts since specified time."""
        since_time = datetime.now() - timedelta(minutes=since_minutes)
        return [
            alert for alert in self.alert_history
            if alert.timestamp >= since_time
        ]
