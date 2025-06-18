#!/usr/bin/env python3
"""
ultimate_agent/monitoring/metrics/__init__.py
Performance monitoring and metrics collection
"""

import time
try:
    import psutil
except Exception:  # pragma: no cover - optional dependency
    psutil = None
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import deque
import json


class MonitoringManager:
    """Manages performance monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics_history = deque(maxlen=1440)  # 24 hours of minute-by-minute data
        self.alerts = []
        self.monitoring_enabled = True
        self.collection_interval = 60  # seconds
        self.alert_thresholds = {
            'cpu_percent': 85.0,
            'memory_percent': 90.0,
            'disk_usage_percent': 95.0,
            'task_failure_rate': 20.0,
            'response_time_ms': 5000
        }
        
        # Metrics collection thread
        self.collection_thread = None
        self.running = False
        
        # Current metrics
        self.current_metrics = {}
        self.last_collection_time = 0
        
        print("📊 Monitoring manager initialized")
    
    def start_monitoring(self):
        """Start metrics collection"""
        if not self.monitoring_enabled or self.running:
            return
        
        self.running = True
        self.collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=True,
            name="MetricsCollector"
        )
        self.collection_thread.start()
        print("📊 Metrics collection started")
    
    def stop_monitoring(self):
        """Stop metrics collection"""
        self.running = False
        if self.collection_thread and self.collection_thread.is_alive():
            self.collection_thread.join(timeout=5)
        print("📊 Metrics collection stopped")
    
    def _collection_loop(self):
        """Main metrics collection loop"""
        while self.running:
            try:
                self.collect_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                print(f"⚠️ Metrics collection error: {e}")
                time.sleep(30)  # Wait before retrying
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        try:
            timestamp = time.time()
            
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O
            try:
                network = psutil.net_io_counters()
                network_io = {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                }
            except Exception:
                network_io = {'bytes_sent': 0, 'bytes_recv': 0, 'packets_sent': 0, 'packets_recv': 0}
            
            # Process information
            try:
                process = psutil.Process()
                process_info = {
                    'cpu_percent': process.cpu_percent(),
                    'memory_mb': process.memory_info().rss / (1024 * 1024),
                    'threads': process.num_threads(),
                    'open_files': len(process.open_files()),
                    'connections': len(process.connections())
                }
            except Exception:
                process_info = {
                    'cpu_percent': 0,
                    'memory_mb': 0,
                    'threads': 0,
                    'open_files': 0,
                    'connections': 0
                }
            
            # GPU metrics (if available)
            gpu_metrics = self._collect_gpu_metrics()
            
            metrics = {
                'timestamp': timestamp,
                'datetime': datetime.fromtimestamp(timestamp).isoformat(),
                
                # System resources
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'memory_used_mb': memory.used / (1024 * 1024),
                'disk_usage_percent': disk.percent,
                'disk_free_gb': disk.free / (1024 * 1024 * 1024),
                
                # Network
                'network_io': network_io,
                
                # Process metrics
                'process': process_info,
                
                # GPU metrics
                'gpu': gpu_metrics,
                
                # Performance indicators
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0],
                'boot_time': psutil.boot_time(),
            }
            
            # Add application-specific metrics
            app_metrics = self._collect_application_metrics()
            metrics.update(app_metrics)
            
            # Store metrics
            self.current_metrics = metrics
            self.metrics_history.append(metrics)
            self.last_collection_time = timestamp
            
            # Check for alerts
            self._check_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            print(f"❌ Failed to collect metrics: {e}")
            return {}
    
    def _collect_gpu_metrics(self) -> Dict[str, Any]:
        """Collect GPU metrics if available"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            
            if gpus:
                gpu = gpus[0]  # Primary GPU
                return {
                    'available': True,
                    'name': gpu.name,
                    'gpu_percent': gpu.load * 100,
                    'memory_percent': gpu.memoryUtil * 100,
                    'memory_used_mb': gpu.memoryUsed,
                    'memory_total_mb': gpu.memoryTotal,
                    'temperature': gpu.temperature
                }
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️ GPU metrics collection failed: {e}")
        
        return {
            'available': False,
            'gpu_percent': 0,
            'memory_percent': 0,
            'memory_used_mb': 0,
            'memory_total_mb': 0,
            'temperature': 0
        }
    
    def _collect_application_metrics(self) -> Dict[str, Any]:
        """Collect application-specific metrics"""
        # This would be implemented by the agent to provide app-specific metrics
        return {
            'tasks_completed': 0,
            'tasks_running': 0,
            'tasks_failed': 0,
            'total_earnings': 0.0,
            'blockchain_balance': 0.0,
            'ai_models_loaded': 0,
            'efficiency_score': 100.0
        }
    
    def update_application_metrics(self, app_metrics: Dict[str, Any]):
        """Update application-specific metrics"""
        if self.current_metrics:
            self.current_metrics.update(app_metrics)
    
    def _check_alerts(self, metrics: Dict[str, Any]):
        """Check metrics against alert thresholds"""
        alerts_triggered = []
        
        # CPU alert
        if metrics.get('cpu_percent', 0) > self.alert_thresholds['cpu_percent']:
            alerts_triggered.append({
                'type': 'cpu_high',
                'message': f"High CPU usage: {metrics['cpu_percent']:.1f}%",
                'value': metrics['cpu_percent'],
                'threshold': self.alert_thresholds['cpu_percent'],
                'severity': 'warning'
            })
        
        # Memory alert
        if metrics.get('memory_percent', 0) > self.alert_thresholds['memory_percent']:
            alerts_triggered.append({
                'type': 'memory_high',
                'message': f"High memory usage: {metrics['memory_percent']:.1f}%",
                'value': metrics['memory_percent'],
                'threshold': self.alert_thresholds['memory_percent'],
                'severity': 'critical'
            })
        
        # Disk alert
        if metrics.get('disk_usage_percent', 0) > self.alert_thresholds['disk_usage_percent']:
            alerts_triggered.append({
                'type': 'disk_full',
                'message': f"Disk usage critical: {metrics['disk_usage_percent']:.1f}%",
                'value': metrics['disk_usage_percent'],
                'threshold': self.alert_thresholds['disk_usage_percent'],
                'severity': 'critical'
            })
        
        # GPU temperature alert (if available)
        gpu_temp = metrics.get('gpu', {}).get('temperature', 0)
        if gpu_temp > 80:  # GPU temperature threshold
            alerts_triggered.append({
                'type': 'gpu_temperature',
                'message': f"GPU temperature high: {gpu_temp}°C",
                'value': gpu_temp,
                'threshold': 80,
                'severity': 'warning'
            })
        
        # Add alerts to history
        for alert in alerts_triggered:
            alert['timestamp'] = time.time()
            alert['datetime'] = datetime.now().isoformat()
            self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        if not self.current_metrics:
            return self.collect_metrics()
        return self.current_metrics
    
    def get_metrics_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics history for specified hours"""
        cutoff_time = time.time() - (hours * 3600)
        return [m for m in self.metrics_history if m['timestamp'] > cutoff_time]
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for specified period"""
        history = self.get_metrics_history(hours)
        
        if not history:
            return {}
        
        # Calculate averages and peaks
        cpu_values = [m.get('cpu_percent', 0) for m in history]
        memory_values = [m.get('memory_percent', 0) for m in history]
        
        summary = {
            'period_hours': hours,
            'data_points': len(history),
            'cpu_stats': {
                'average': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'peak': max(cpu_values) if cpu_values else 0,
                'minimum': min(cpu_values) if cpu_values else 0
            },
            'memory_stats': {
                'average': sum(memory_values) / len(memory_values) if memory_values else 0,
                'peak': max(memory_values) if memory_values else 0,
                'minimum': min(memory_values) if memory_values else 0
            },
            'alerts_count': len([a for a in self.alerts 
                               if a['timestamp'] > time.time() - (hours * 3600)]),
            'uptime_hours': (time.time() - min(m['timestamp'] for m in history)) / 3600 if history else 0
        }
        
        return summary
    
    def get_alerts(self, severity: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.get('severity') == severity]
        
        # Return most recent alerts
        return sorted(alerts, key=lambda x: x['timestamp'], reverse=True)[:limit]
    
    def clear_alerts(self, older_than_hours: int = 24):
        """Clear old alerts"""
        cutoff_time = time.time() - (older_than_hours * 3600)
        self.alerts = [a for a in self.alerts if a['timestamp'] > cutoff_time]
    
    def set_alert_threshold(self, metric: str, threshold: float):
        """Set alert threshold for metric"""
        if metric in self.alert_thresholds:
            self.alert_thresholds[metric] = threshold
            print(f"📊 Alert threshold for {metric} set to {threshold}")
        else:
            print(f"⚠️ Unknown metric: {metric}")
    
    def get_health_score(self) -> Dict[str, Any]:
        """Calculate overall system health score"""
        if not self.current_metrics:
            return {'score': 0, 'status': 'unknown'}
        
        metrics = self.current_metrics
        
        # Calculate individual component scores (0-100)
        cpu_score = max(0, 100 - metrics.get('cpu_percent', 0))
        memory_score = max(0, 100 - metrics.get('memory_percent', 0))
        disk_score = max(0, 100 - metrics.get('disk_usage_percent', 0))
        
        # GPU score (if available)
        gpu_metrics = metrics.get('gpu', {})
        if gpu_metrics.get('available', False):
            gpu_temp = gpu_metrics.get('temperature', 50)
            gpu_score = max(0, 100 - (gpu_temp - 30) * 2)  # Penalize high temps
        else:
            gpu_score = 100  # No penalty if GPU not available
        
        # Recent alerts penalty
        recent_alerts = len([a for a in self.alerts 
                           if a['timestamp'] > time.time() - 3600])
        alert_penalty = min(50, recent_alerts * 10)
        
        # Calculate weighted overall score
        overall_score = (
            cpu_score * 0.3 +
            memory_score * 0.3 +
            disk_score * 0.2 +
            gpu_score * 0.1 +
            (100 - alert_penalty) * 0.1
        )
        
        # Determine status
        if overall_score >= 90:
            status = 'excellent'
        elif overall_score >= 75:
            status = 'good'
        elif overall_score >= 60:
            status = 'fair'
        elif overall_score >= 40:
            status = 'poor'
        else:
            status = 'critical'
        
        return {
            'score': round(overall_score, 1),
            'status': status,
            'components': {
                'cpu': round(cpu_score, 1),
                'memory': round(memory_score, 1),
                'disk': round(disk_score, 1),
                'gpu': round(gpu_score, 1)
            },
            'recent_alerts': recent_alerts,
            'last_updated': datetime.now().isoformat()
        }
    
    def export_metrics(self, filepath: str, hours: int = 24) -> bool:
        """Export metrics data to file"""
        try:
            export_data = {
                'export_timestamp': time.time(),
                'export_period_hours': hours,
                'metrics_history': self.get_metrics_history(hours),
                'performance_summary': self.get_performance_summary(hours),
                'alerts': self.get_alerts(limit=500),
                'health_score': self.get_health_score(),
                'alert_thresholds': self.alert_thresholds
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            print(f"📄 Metrics exported to {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to export metrics: {e}")
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            import platform
            
            return {
                'platform': {
                    'system': platform.system(),
                    'release': platform.release(),
                    'version': platform.version(),
                    'machine': platform.machine(),
                    'processor': platform.processor(),
                    'python_version': platform.python_version()
                },
                'cpu': {
                    'physical_cores': psutil.cpu_count(logical=False),
                    'logical_cores': psutil.cpu_count(logical=True),
                    'max_frequency': psutil.cpu_freq().max if psutil.cpu_freq() else 0,
                    'current_frequency': psutil.cpu_freq().current if psutil.cpu_freq() else 0
                },
                'memory': {
                    'total_gb': psutil.virtual_memory().total / (1024**3),
                    'available_gb': psutil.virtual_memory().available / (1024**3)
                },
                'disk': {
                    'total_gb': psutil.disk_usage('/').total / (1024**3),
                    'free_gb': psutil.disk_usage('/').free / (1024**3)
                },
                'network': {
                    'interfaces': len(psutil.net_if_addrs())
                },
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
            
        except Exception as e:
            print(f"⚠️ Failed to get system info: {e}")
            return {}
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitoring manager status"""
        return {
            'monitoring_enabled': self.monitoring_enabled,
            'collection_running': self.running,
            'collection_interval_seconds': self.collection_interval,
            'metrics_history_size': len(self.metrics_history),
            'alerts_count': len(self.alerts),
            'last_collection_time': self.last_collection_time,
            'health_score': self.get_health_score()['score'],
            'alert_thresholds': self.alert_thresholds
        }
    
    def close(self):
        """Close monitoring manager"""
        self.stop_monitoring()
        print("📊 Monitoring manager closed")
