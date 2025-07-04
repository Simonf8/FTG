/**
 * Dashboard Client-side JavaScript
 * Real-time dashboard for the distributed edge AI network
 */

class EdgeAIDashboard {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.performanceChart = null;
        this.nodeTypeChart = null;
        this.realTimeBuffer = [];
        this.maxRealTimeEntries = 100;
        
        this.initializeSocket();
        this.initializeCharts();
        this.bindEventHandlers();
    }
    
    initializeSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            this.isConnected = true;
            this.updateConnectionStatus('online', 'Connected');
            console.log('Connected to dashboard server');
        });
        
        this.socket.on('disconnect', () => {
            this.isConnected = false;
            this.updateConnectionStatus('offline', 'Disconnected');
            console.log('Disconnected from dashboard server');
        });
        
        this.socket.on('initialData', (data) => {
            console.log('Received initial data:', data);
            this.updateSystemOverview(data);
            this.updateNodesList(data.nodes);
            this.updateAlertsList(data.alerts);
            this.updateCharts(data);
        });
        
        this.socket.on('systemUpdate', (data) => {
            console.log('Received system update:', data);
            this.updateSystemOverview(data);
            this.updateNodesList(data.nodes);
            this.updateAlertsList(data.alerts);
            this.updateLastUpdateTime();
        });
        
        this.socket.on('metricsUpdate', (data) => {
            console.log('Received metrics update:', data);
            this.updatePerformanceChart(data.metrics);
        });
        
        this.socket.on('realTimeData', (data) => {
            this.addRealTimeData(data);
        });
        
        this.socket.on('error', (error) => {
            console.error('Socket error:', error);
            this.showNotification('Error: ' + error.message, 'error');
        });
    }
    
    initializeCharts() {
        // Performance Chart
        const performanceCtx = document.getElementById('performanceChart').getContext('2d');
        this.performanceChart = new Chart(performanceCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Messages/sec',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }, {
                    label: 'CPU Usage %',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: true
                    }
                }
            }
        });
        
        // Node Type Chart
        const nodeTypeCtx = document.getElementById('nodeTypeChart').getContext('2d');
        this.nodeTypeChart = new Chart(nodeTypeCtx, {
            type: 'doughnut',
            data: {
                labels: ['Traffic', 'Crime', 'Environment', 'Hybrid'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 205, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    bindEventHandlers() {
        // Refresh button
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
                e.preventDefault();
                this.refreshData();
            }
        });
        
        // Node click handlers
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('node-item')) {
                const nodeId = e.target.dataset.nodeId;
                this.showNodeDetails(nodeId);
            }
            
            if (e.target.classList.contains('alert-item')) {
                const alertId = e.target.dataset.alertId;
                this.showAlertDetails(alertId);
            }
        });
    }
    
    updateConnectionStatus(status, text) {
        const statusIndicator = document.getElementById('connectionStatus');
        const connectionText = document.getElementById('connectionText');
        
        statusIndicator.className = `status-indicator status-${status}`;
        connectionText.textContent = text;
    }
    
    updateSystemOverview(data) {
        const totalNodes = data.nodes ? data.nodes.length : 0;
        const activeNodes = data.nodes ? data.nodes.filter(n => n.status === 'online').length : 0;
        const totalAlerts = data.alerts ? data.alerts.length : 0;
        
        document.getElementById('totalNodes').textContent = totalNodes;
        document.getElementById('activeNodes').textContent = activeNodes;
        document.getElementById('totalAlerts').textContent = totalAlerts;
        
        // Calculate messages per second (mock calculation)
        const messagesPerSecond = Math.floor(Math.random() * 50) + 10;
        document.getElementById('messagesPerSecond').textContent = messagesPerSecond;
    }
    
    updateNodesList(nodes) {
        const nodesList = document.getElementById('nodesList');
        
        if (!nodes || nodes.length === 0) {
            nodesList.innerHTML = '<p class="text-muted">No nodes registered</p>';
            return;
        }
        
        const nodesHTML = nodes.map(node => `
            <div class="node-item d-flex justify-content-between align-items-center p-2 border-bottom" 
                 data-node-id="${node.node_id}" style="cursor: pointer;">
                <div>
                    <span class="status-indicator status-${node.status === 'online' ? 'online' : 'offline'}"></span>
                    <strong>${node.node_id}</strong>
                    <small class="text-muted">(${node.node_type})</small>
                </div>
                <div class="text-end">
                    <small class="text-muted">${node.location.address || 'Unknown location'}</small><br>
                    <small class="text-muted">CPU: ${node.cpu_usage ? node.cpu_usage.toFixed(1) + '%' : 'N/A'}</small>
                </div>
            </div>
        `).join('');
        
        nodesList.innerHTML = nodesHTML;
        
        // Update node type chart
        this.updateNodeTypeChart(nodes);
    }
    
    updateAlertsList(alerts) {
        const alertsList = document.getElementById('alertsList');
        
        if (!alerts || alerts.length === 0) {
            alertsList.innerHTML = '<p class="text-muted">No recent alerts</p>';
            return;
        }
        
        const alertsHTML = alerts.slice(0, 5).map(alert => `
            <div class="alert-item alert-${alert.level}" data-alert-id="${alert.alert_id}" style="cursor: pointer;">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${alert.title}</strong>
                        <p class="mb-1">${alert.description}</p>
                        <small class="text-muted">
                            <i class="fas fa-map-marker-alt"></i> ${alert.source_node} | 
                            <i class="fas fa-clock"></i> ${new Date(alert.timestamp).toLocaleString()}
                        </small>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-${this.getAlertBadgeColor(alert.level)}">${alert.level}</span>
                    </div>
                </div>
            </div>
        `).join('');
        
        alertsList.innerHTML = alertsHTML;
    }
    
    updatePerformanceChart(metrics) {
        if (!this.performanceChart || !metrics) return;
        
        const now = new Date().toLocaleTimeString();
        const labels = this.performanceChart.data.labels;
        const messagesData = this.performanceChart.data.datasets[0].data;
        const cpuData = this.performanceChart.data.datasets[1].data;
        
        // Add new data point
        labels.push(now);
        messagesData.push(metrics.messages_per_second || 0);
        cpuData.push(metrics.cpu_usage || 0);
        
        // Keep only last 20 data points
        if (labels.length > 20) {
            labels.shift();
            messagesData.shift();
            cpuData.shift();
        }
        
        this.performanceChart.update();
    }
    
    updateNodeTypeChart(nodes) {
        if (!this.nodeTypeChart || !nodes) return;
        
        const typeCounts = {
            traffic: 0,
            crime: 0,
            environment: 0,
            hybrid: 0
        };
        
        nodes.forEach(node => {
            if (typeCounts.hasOwnProperty(node.node_type)) {
                typeCounts[node.node_type]++;
            }
        });
        
        this.nodeTypeChart.data.datasets[0].data = [
            typeCounts.traffic,
            typeCounts.crime,
            typeCounts.environment,
            typeCounts.hybrid
        ];
        
        this.nodeTypeChart.update();
    }
    
    updateCharts(data) {
        if (data.metrics) {
            this.updatePerformanceChart(data.metrics);
        }
        
        if (data.nodes) {
            this.updateNodeTypeChart(data.nodes);
        }
    }
    
    addRealTimeData(data) {
        const realTimeData = document.getElementById('realTimeData');
        
        this.realTimeBuffer.push({
            timestamp: new Date().toLocaleTimeString(),
            data: data
        });
        
        // Keep buffer size manageable
        if (this.realTimeBuffer.length > this.maxRealTimeEntries) {
            this.realTimeBuffer.shift();
        }
        
        // Update display
        const displayHTML = this.realTimeBuffer.slice(-10).reverse().map(entry => 
            `<div class="mb-1">
                <span class="text-muted">[${entry.timestamp}]</span> 
                ${JSON.stringify(entry.data, null, 2)}
            </div>`
        ).join('');
        
        realTimeData.innerHTML = displayHTML;
        realTimeData.scrollTop = 0;
    }
    
    updateLastUpdateTime() {
        const lastUpdate = document.getElementById('lastUpdate');
        lastUpdate.textContent = `Last update: ${new Date().toLocaleString()}`;
    }
    
    getAlertBadgeColor(level) {
        const colors = {
            'critical': 'danger',
            'high': 'warning',
            'medium': 'info',
            'low': 'success'
        };
        return colors[level] || 'secondary';
    }
    
    showNodeDetails(nodeId) {
        this.socket.emit('requestNodeDetails', nodeId);
        
        this.socket.once('nodeDetails', (details) => {
            this.showModal('Node Details', `
                <h5>${details.node_id}</h5>
                <p><strong>Type:</strong> ${details.node_type}</p>
                <p><strong>Status:</strong> ${details.status}</p>
                <p><strong>Location:</strong> ${details.location.address || 'Unknown'}</p>
                <p><strong>CPU Usage:</strong> ${details.cpu_usage ? details.cpu_usage.toFixed(1) + '%' : 'N/A'}</p>
                <p><strong>Memory Usage:</strong> ${details.memory_usage ? details.memory_usage.toFixed(1) + '%' : 'N/A'}</p>
                <p><strong>Active Sensors:</strong> ${details.active_sensors ? details.active_sensors.length : 0}</p>
                <p><strong>Last Heartbeat:</strong> ${new Date(details.last_heartbeat).toLocaleString()}</p>
            `);
        });
    }
    
    showAlertDetails(alertId) {
        this.socket.emit('requestAlertDetails', alertId);
        
        this.socket.once('alertDetails', (details) => {
            this.showModal('Alert Details', `
                <h5>${details.title}</h5>
                <p><strong>Level:</strong> <span class="badge bg-${this.getAlertBadgeColor(details.level)}">${details.level}</span></p>
                <p><strong>Description:</strong> ${details.description}</p>
                <p><strong>Source Node:</strong> ${details.source_node}</p>
                <p><strong>Timestamp:</strong> ${new Date(details.timestamp).toLocaleString()}</p>
                <p><strong>Location:</strong> ${details.location.address || 'Unknown'}</p>
                <p><strong>Resolved:</strong> ${details.resolved ? 'Yes' : 'No'}</p>
            `);
        });
    }
    
    showModal(title, content) {
        // Simple modal implementation
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${title}</h5>
                        <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                    </div>
                    <div class="modal-body">
                        ${content}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (modal.parentNode) {
                modal.remove();
            }
        }, 10000);
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
        notification.style.zIndex = '9999';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close float-end" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
    
    refreshData() {
        if (this.isConnected) {
            this.socket.emit('requestRefresh');
            this.showNotification('Data refreshed', 'success');
        } else {
            this.showNotification('Not connected to server', 'warning');
        }
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new EdgeAIDashboard();
    window.dashboard = dashboard; // Make available globally for debugging
});
