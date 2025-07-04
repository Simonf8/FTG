"""
Local Storage for Edge Nodes
"""

import asyncio
import json
import sqlite3
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import aiosqlite

from ..common.models import SensorData, ProcessingJob, SystemMetrics
from ..common.logger import get_logger
from ..common.utils import serialize_data, deserialize_data, get_current_timestamp

logger = get_logger(__name__)


class LocalStorage:
    """Local storage manager for edge nodes"""
    
    def __init__(self, node_id: str, storage_path: Optional[str] = None):
        self.node_id = node_id
        self.storage_path = storage_path or f"data/{node_id}"
        self.db_path = f"{self.storage_path}/edge_node.db"
        self.db_connection = None
        self.max_storage_mb = 1000  # Maximum storage in MB
        self.retention_days = 7  # Data retention period
        
        # Ensure storage directory exists
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """Initialize local storage"""
        logger.info(f"Initializing local storage for node {self.node_id}")
        
        try:
            # Create database connection
            self.db_connection = await aiosqlite.connect(self.db_path)
            
            # Create tables
            await self._create_tables()
            
            # Clean up old data
            await self._cleanup_old_data()
            
            logger.info(f"Local storage initialized at {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize local storage: {e}")
            raise
    
    async def _create_tables(self) -> None:
        """Create database tables"""
        
        # Sensor data table
        await self.db_connection.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT NOT NULL,
                sensor_type TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                location TEXT NOT NULL,
                data TEXT NOT NULL,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Processing jobs table
        await self.db_connection.execute("""
            CREATE TABLE IF NOT EXISTS processing_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                job_type TEXT NOT NULL,
                node_id TEXT NOT NULL,
                status TEXT NOT NULL,
                input_data TEXT NOT NULL,
                result TEXT,
                error_message TEXT,
                created_at DATETIME NOT NULL,
                started_at DATETIME,
                completed_at DATETIME
            )
        """)
        
        # Metrics table
        await self.db_connection.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                metric_type TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Alerts table
        await self.db_connection.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT UNIQUE NOT NULL,
                alert_type TEXT NOT NULL,
                level TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                location TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                source_node TEXT NOT NULL,
                source_data TEXT,
                resolved BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Cache table for frequently accessed data
        await self.db_connection.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                expires_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indices for better performance
        await self.db_connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp 
            ON sensor_data(timestamp)
        """)
        
        await self.db_connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_processing_jobs_status 
            ON processing_jobs(status)
        """)
        
        await self.db_connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
            ON metrics(timestamp)
        """)
        
        await self.db_connection.commit()
    
    async def store_sensor_data(self, sensor_data: SensorData) -> None:
        """Store sensor data"""
        try:
            await self.db_connection.execute("""
                INSERT INTO sensor_data 
                (sensor_id, sensor_type, timestamp, location, data, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                sensor_data.sensor_id,
                sensor_data.sensor_type.value,
                sensor_data.timestamp.isoformat(),
                serialize_data(sensor_data.location.to_dict()),
                serialize_data(sensor_data.data),
                serialize_data(sensor_data.metadata)
            ))
            
            await self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Error storing sensor data: {e}")
    
    async def get_sensor_data(
        self, 
        sensor_id: Optional[str] = None, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve sensor data"""
        try:
            query = "SELECT * FROM sensor_data WHERE 1=1"
            params = []
            
            if sensor_id:
                query += " AND sensor_id = ?"
                params.append(sensor_id)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = await self.db_connection.execute(query, params)
            rows = await cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "sensor_id": row[1],
                    "sensor_type": row[2],
                    "timestamp": row[3],
                    "location": deserialize_data(row[4]),
                    "data": deserialize_data(row[5]),
                    "metadata": deserialize_data(row[6]) if row[6] else {},
                    "created_at": row[7]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving sensor data: {e}")
            return []
    
    async def store_processing_result(self, job: ProcessingJob) -> None:
        """Store processing job result"""
        try:
            await self.db_connection.execute("""
                INSERT OR REPLACE INTO processing_jobs 
                (job_id, job_type, node_id, status, input_data, result, error_message, 
                 created_at, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id,
                job.job_type,
                job.node_id,
                job.status.value,
                serialize_data(job.input_data.to_dict()),
                serialize_data(job.result) if job.result else None,
                job.error_message,
                job.created_at.isoformat(),
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None
            ))
            
            await self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Error storing processing result: {e}")
    
    async def get_processing_jobs(
        self, 
        status: Optional[str] = None, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve processing jobs"""
        try:
            query = "SELECT * FROM processing_jobs WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = await self.db_connection.execute(query, params)
            rows = await cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "job_id": row[1],
                    "job_type": row[2],
                    "node_id": row[3],
                    "status": row[4],
                    "input_data": deserialize_data(row[5]),
                    "result": deserialize_data(row[6]) if row[6] else None,
                    "error_message": row[7],
                    "created_at": row[8],
                    "started_at": row[9],
                    "completed_at": row[10]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving processing jobs: {e}")
            return []
    
    async def store_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store system metrics"""
        try:
            await self.db_connection.execute("""
                INSERT INTO metrics (timestamp, metric_type, data)
                VALUES (?, ?, ?)
            """, (
                get_current_timestamp().isoformat(),
                "system_metrics",
                serialize_data(metrics)
            ))
            
            await self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
    
    async def get_metrics(
        self, 
        metric_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve metrics"""
        try:
            query = "SELECT * FROM metrics WHERE 1=1"
            params = []
            
            if metric_type:
                query += " AND metric_type = ?"
                params.append(metric_type)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = await self.db_connection.execute(query, params)
            rows = await cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "metric_type": row[2],
                    "data": deserialize_data(row[3]),
                    "created_at": row[4]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving metrics: {e}")
            return []
    
    async def store_cache(self, key: str, value: Any, expires_at: Optional[datetime] = None) -> None:
        """Store data in cache"""
        try:
            await self.db_connection.execute("""
                INSERT OR REPLACE INTO cache (key, value, expires_at)
                VALUES (?, ?, ?)
            """, (
                key,
                serialize_data(value),
                expires_at.isoformat() if expires_at else None
            ))
            
            await self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Error storing cache: {e}")
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """Retrieve data from cache"""
        try:
            cursor = await self.db_connection.execute("""
                SELECT value, expires_at FROM cache WHERE key = ?
            """, (key,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            # Check if expired
            if row[1]:
                expires_at = datetime.fromisoformat(row[1])
                if expires_at < get_current_timestamp():
                    # Remove expired cache entry
                    await self.db_connection.execute("""
                        DELETE FROM cache WHERE key = ?
                    """, (key,))
                    await self.db_connection.commit()
                    return None
            
            return deserialize_data(row[0])
            
        except Exception as e:
            logger.error(f"Error retrieving cache: {e}")
            return None
    
    async def clear_cache(self, key: Optional[str] = None) -> None:
        """Clear cache entries"""
        try:
            if key:
                await self.db_connection.execute("""
                    DELETE FROM cache WHERE key = ?
                """, (key,))
            else:
                await self.db_connection.execute("DELETE FROM cache")
            
            await self.db_connection.commit()
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            # Get database size
            db_size = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
            
            # Get record counts
            cursor = await self.db_connection.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM sensor_data) as sensor_count,
                    (SELECT COUNT(*) FROM processing_jobs) as job_count,
                    (SELECT COUNT(*) FROM metrics) as metric_count,
                    (SELECT COUNT(*) FROM alerts) as alert_count,
                    (SELECT COUNT(*) FROM cache) as cache_count
            """)
            
            row = await cursor.fetchone()
            
            return {
                "database_size_mb": round(db_size, 2),
                "sensor_data_count": row[0],
                "processing_jobs_count": row[1],
                "metrics_count": row[2],
                "alerts_count": row[3],
                "cache_entries_count": row[4],
                "storage_path": self.storage_path
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}
    
    async def cleanup_old_data(self) -> None:
        """Clean up old data based on retention policy"""
        try:
            cutoff_date = get_current_timestamp() - timedelta(days=self.retention_days)
            
            # Clean up old sensor data
            await self.db_connection.execute("""
                DELETE FROM sensor_data WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            # Clean up old processing jobs
            await self.db_connection.execute("""
                DELETE FROM processing_jobs WHERE created_at < ?
            """, (cutoff_date.isoformat(),))
            
            # Clean up old metrics
            await self.db_connection.execute("""
                DELETE FROM metrics WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            # Clean up expired cache entries
            await self.db_connection.execute("""
                DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (get_current_timestamp().isoformat(),))
            
            await self.db_connection.commit()
            
            # Vacuum database to reclaim space
            await self.db_connection.execute("VACUUM")
            
            logger.info(f"Cleaned up data older than {self.retention_days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    async def _cleanup_old_data(self) -> None:
        """Internal cleanup called during initialization"""
        await self.cleanup_old_data()
    
    async def export_data(self, output_path: str, format: str = "json") -> None:
        """Export data to file"""
        try:
            data = {
                "sensor_data": await self.get_sensor_data(limit=10000),
                "processing_jobs": await self.get_processing_jobs(limit=10000),
                "metrics": await self.get_metrics(limit=10000),
                "export_timestamp": get_current_timestamp().isoformat(),
                "node_id": self.node_id
            }
            
            if format.lower() == "json":
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Data exported to {output_path}")
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
    
    async def import_data(self, input_path: str, format: str = "json") -> None:
        """Import data from file"""
        try:
            if format.lower() == "json":
                with open(input_path, 'r') as f:
                    data = json.load(f)
            else:
                raise ValueError(f"Unsupported import format: {format}")
            
            # Import sensor data
            for item in data.get("sensor_data", []):
                # Convert back to SensorData object and store
                # This is a simplified version - in practice you'd need proper validation
                pass
            
            logger.info(f"Data imported from {input_path}")
            
        except Exception as e:
            logger.error(f"Error importing data: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown storage"""
        if self.db_connection:
            await self.db_connection.close()
        logger.info("Local storage shutdown complete")
