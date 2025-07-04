/**
 * JavaScript/Node.js Dashboard Server
 * Real-time monitoring dashboard for the distributed edge AI network
 */

const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const axios = require('axios');
const path = require('path');

class DashboardServer {
    constructor(config = {}) {
        this.config = {
            port: config.port || 3000,
            coordinatorUrl: config.coordinatorUrl || 'http://localhost:8080',
            staticPath: config.staticPath || path.join(__dirname, 'public'),
            ...config
        };
        
        this.app = express();
        this.server = http.createServer(this.app);
        this.io = socketIo(this.server, {
            cors: {
                origin: "*",
                methods: ["GET", "POST"]
            }
        });
        
        this.connectedClients = new Map();
        this.systemData = {
            nodes: [],
            alerts: [],
            metrics: {},
            insights: []
        };
        
        this.setupRoutes();
        this.setupSocketHandlers();
        this.setupDataPolling();
    }
    
    setupRoutes() {
        // Serve static files
        this.app.use(express.static(this.config.staticPath));
        this.app.use(express.json());
        
        // API endpoints
        this.app.get('/api/dashboard/status', (req, res) => {
            res.json({
                status: 'online',
                connectedClients: this.connectedClients.size,
                lastUpdate: new Date().toISOString()
            });
        });
        
        this.app.get('/api/dashboard/nodes', (req, res) => {
            res.json(this.systemData.nodes);
        });
        
        this.app.get('/api/dashboard/alerts', (req, res) => {
            res.json(this.systemData.alerts);
        });
        
        this.app.get('/api/dashboard/metrics', (req, res) => {
            res.json(this.systemData.metrics);
        });
        
        // Main dashboard page
        this.app.get('/', (req, res) => {
            res.sendFile(path.join(this.config.staticPath, 'index.html'));
        });
    }
    
    setupSocketHandlers() {
        this.io.on('connection', (socket) => {
            console.log(`Client connected: ${socket.id}`);
            this.connectedClients.set(socket.id, {
                connectedAt: new Date(),
                lastActivity: new Date()
            });
            
            // Send initial data
            socket.emit('initialData', {
                nodes: this.systemData.nodes,
                alerts: this.systemData.alerts.slice(-50), // Last 50 alerts
                metrics: this.systemData.metrics
            });
            
            // Handle client requests
            socket.on('requestNodeDetails', (nodeId) => {
                this.fetchNodeDetails(nodeId)
                    .then(details => socket.emit('nodeDetails', details))
                    .catch(err => socket.emit('error', { message: 'Failed to fetch node details' }));
            });
            
            socket.on('requestAlertDetails', (alertId) => {
                this.fetchAlertDetails(alertId)
                    .then(details => socket.emit('alertDetails', details))
                    .catch(err => socket.emit('error', { message: 'Failed to fetch alert details' }));
            });
            
            socket.on('disconnect', () => {
                console.log(`Client disconnected: ${socket.id}`);
                this.connectedClients.delete(socket.id);
            });
        });
    }
    
    setupDataPolling() {
        // Poll coordinator for updates every 5 seconds
        setInterval(() => {
            this.pollCoordinatorData();
        }, 5000);
        
        // Poll metrics every 10 seconds
        setInterval(() => {
            this.pollMetrics();
        }, 10000);
    }
    
    async pollCoordinatorData() {
        try {
            // Fetch system status
            const statusResponse = await axios.get(`${this.config.coordinatorUrl}/api/system/status`);
            const status = statusResponse.data;
            
            // Update system data
            this.systemData.nodes = status.nodes || [];
            this.systemData.alerts = status.recent_alerts || [];
            
            // Broadcast updates to connected clients
            this.io.emit('systemUpdate', {
                nodes: this.systemData.nodes,
                alerts: this.systemData.alerts.slice(-10), // Last 10 alerts
                timestamp: new Date().toISOString()
            });
            
        } catch (error) {
            console.error('Error polling coordinator data:', error.message);
        }
    }
    
    async pollMetrics() {
        try {
            // Fetch metrics
            const metricsResponse = await axios.get(`${this.config.coordinatorUrl}/api/metrics`);
            const metrics = metricsResponse.data;
            
            this.systemData.metrics = metrics;
            
            // Broadcast metrics update
            this.io.emit('metricsUpdate', {
                metrics: metrics,
                timestamp: new Date().toISOString()
            });
            
        } catch (error) {
            console.error('Error polling metrics:', error.message);
        }
    }
    
    async fetchNodeDetails(nodeId) {
        try {
            const response = await axios.get(`${this.config.coordinatorUrl}/api/nodes/${nodeId}`);
            return response.data;
        } catch (error) {
            throw new Error(`Failed to fetch node details: ${error.message}`);
        }
    }
    
    async fetchAlertDetails(alertId) {
        try {
            const response = await axios.get(`${this.config.coordinatorUrl}/api/alerts/${alertId}`);
            return response.data;
        } catch (error) {
            throw new Error(`Failed to fetch alert details: ${error.message}`);
        }
    }
    
    // Real-time data processing
    processRealTimeData(data) {
        const processedData = {
            ...data,
            processedAt: new Date().toISOString(),
            clientCount: this.connectedClients.size
        };
        
        // Broadcast to all connected clients
        this.io.emit('realTimeData', processedData);
        
        return processedData;
    }
    
    // Traffic analysis visualization data
    getTrafficVisualizationData() {
        return this.systemData.nodes
            .filter(node => node.node_type === 'traffic')
            .map(node => ({
                nodeId: node.node_id,
                location: node.location,
                congestionLevel: node.last_data?.congestion_level || 0,
                vehicleCount: node.last_data?.vehicle_count || 0,
                averageSpeed: node.last_data?.average_speed || 0,
                timestamp: node.last_heartbeat
            }));
    }
    
    // Crime detection visualization data
    getCrimeVisualizationData() {
        return this.systemData.nodes
            .filter(node => node.node_type === 'crime')
            .map(node => ({
                nodeId: node.node_id,
                location: node.location,
                suspiciousActivity: node.last_data?.suspicious_activity || false,
                riskLevel: node.last_data?.risk_assessment || 0,
                timestamp: node.last_heartbeat
            }));
    }
    
    // Environmental monitoring visualization data
    getEnvironmentVisualizationData() {
        return this.systemData.nodes
            .filter(node => node.node_type === 'environment')
            .map(node => ({
                nodeId: node.node_id,
                location: node.location,
                airQualityIndex: node.last_data?.air_quality_index || 0,
                noiseLevel: node.last_data?.noise_level || 0,
                temperature: node.last_data?.temperature || 0,
                timestamp: node.last_heartbeat
            }));
    }
    
    start() {
        return new Promise((resolve, reject) => {
            this.server.listen(this.config.port, (err) => {
                if (err) {
                    reject(err);
                } else {
                    console.log(`Dashboard server listening on port ${this.config.port}`);
                    console.log(`Dashboard URL: http://localhost:${this.config.port}`);
                    resolve();
                }
            });
        });
    }
    
    stop() {
        return new Promise((resolve) => {
            this.server.close(() => {
                console.log('Dashboard server stopped');
                resolve();
            });
        });
    }
}

// Export for module use
module.exports = DashboardServer;

// CLI usage
if (require.main === module) {
    const config = {
        port: process.env.DASHBOARD_PORT || 3000,
        coordinatorUrl: process.env.COORDINATOR_URL || 'http://localhost:8080'
    };
    
    const dashboard = new DashboardServer(config);
    
    dashboard.start().then(() => {
        console.log('Dashboard server started successfully');
    }).catch(err => {
        console.error('Failed to start dashboard server:', err);
        process.exit(1);
    });
    
    // Graceful shutdown
    process.on('SIGINT', () => {
        console.log('Received SIGINT, shutting down gracefully...');
        dashboard.stop().then(() => {
            process.exit(0);
        });
    });
}
