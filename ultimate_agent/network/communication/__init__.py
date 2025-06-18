#!/usr/bin/env python3
"""
ultimate_agent/network/communication/__init__.py
Enhanced network communication with proper agent registration
"""

import time
try:
    import requests
except Exception:  # pragma: no cover - optional dependency
    requests = None
import threading
from typing import Dict, Any, Optional
import ssl
import json


class NetworkManager:
    """Enhanced network manager with proper agent registration"""
    
    def __init__(self, config_manager):
        self.config = config_manager

        if requests is None:
            print(
                "⚠️ 'requests' library not available, network features disabled"
            )
            self.session = None
        else:
            self.session = requests.Session()

        # Store timeout separately since requests.Session has no timeout attribute
        self.request_timeout = self.config.getint('NETWORK', 'connection_timeout', fallback=30)

        self.connected_nodes = {}
        self.connection_stats = {
            'successful_requests': 0,
            'failed_requests': 0,
            'total_bytes_sent': 0,
            'total_bytes_received': 0,
            'last_successful_connection': None,
            'last_failed_connection': None
        }
        
        # Node URL storage
        self._node_url = None
        
        self._setup_session()
        print("🌐 Network manager initialized")
    
    def _setup_session(self):
        """Setup HTTP session with optimal configuration"""
        if self.session is None:
            return

        # Set headers
        self.session.headers.update({
            'User-Agent': 'UltimatePainNetworkAgent-Enhanced/4.0.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })
        
        # Configure timeouts (applied per request)
        self.request_timeout = self.config.getint('NETWORK', 'connection_timeout', fallback=30)
        
        # Configure SSL if enabled
        if self.config.getboolean('NETWORK', 'use_ssl', fallback=True):
            verify_ssl = self.config.getboolean('NETWORK', 'verify_ssl', fallback=True)
            self.session.verify = verify_ssl
        
        # Configure retries
        try:
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            retry_strategy = Retry(
                total=self.config.getint('NETWORK', 'retry_attempts', fallback=3),
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
        except ImportError:
            print("⚠️ urllib3 not available, retries disabled")

    def set_node_url(self, node_url: str):
        """Set the primary node URL"""
        self._node_url = node_url.rstrip('/')
        print(f"🌐 Node URL set to: {self._node_url}")
    
    def register_agent(self, agent_id: str, capabilities: Dict[str, Any]) -> bool:
        """Enhanced agent registration with better error handling"""
        if self.session is None:
            print("❌ Network session not available")
            return False
        
        if not self._node_url:
            print("❌ Node URL not set")
            return False
        
        try:
            print(f"🔄 Attempting registration to {self._node_url}")
            
            # Enhanced registration data
            registration_data = {
                **capabilities,
                "registration_protocol_version": "4.0",
                "modular_architecture": True,
                "network_manager_version": "2.0.0",
                "communication_features": ["websocket", "rest", "real_time"],
                "protocol_support": ["http", "https", "websocket"],
                "registration_timestamp": time.time()
            }
            
            # Try multiple API versions with better error reporting
            endpoints = [
                f"{self._node_url}/api/v4/agents/register",
                f"{self._node_url}/api/v3/agents/register", 
                f"{self._node_url}/api/v2/agents/register",
                f"{self._node_url}/api/agents/register"
            ]
            
            last_error = None
            
            for endpoint in endpoints:
                try:
                    print(f"  📡 Trying endpoint: {endpoint}")
                    
                    response = self._make_request('POST', endpoint, json=registration_data)
                    
                    if response and response.get("success"):
                        # Store successful connection info
                        self.connected_nodes[self._node_url] = {
                            'endpoint': endpoint,
                            'connected_at': time.time(),
                            'last_heartbeat': time.time(),
                            'status': 'connected',
                            'api_version': endpoint.split('/')[-3] if 'v' in endpoint else 'v1',
                            'registration_data': registration_data
                        }
                        
                        self.connection_stats['successful_requests'] += 1
                        self.connection_stats['last_successful_connection'] = time.time()
                        
                        print(f"✅ Agent registered successfully!")
                        print(f"   📡 Endpoint: {endpoint}")
                        print(f"   🆔 Agent ID: {agent_id}")
                        
                        return True
                    else:
                        error_msg = response.get('error', 'Unknown error') if response else 'No response'
                        print(f"  ❌ Registration failed: {error_msg}")
                        last_error = error_msg
                        
                except Exception as e:
                    print(f"  ❌ Endpoint {endpoint} failed: {e}")
                    last_error = str(e)
                    continue
            
            # All endpoints failed
            self.connection_stats['failed_requests'] += 1
            self.connection_stats['last_failed_connection'] = time.time()
            
            print(f"❌ All registration endpoints failed")
            print(f"   Last error: {last_error}")
            
            return False
            
        except Exception as e:
            print(f"❌ Registration error: {e}")
            self.connection_stats['failed_requests'] += 1
            self.connection_stats['last_failed_connection'] = time.time()
            return False
    
    def send_heartbeat(self, agent_id: str, status_data: Dict[str, Any]) -> bool:
        """Enhanced heartbeat with better error handling"""
        if not self.connected_nodes:
            print("⚠️ No connected nodes for heartbeat")
            return False
        
        # Enhanced heartbeat data
        heartbeat_data = {
            **status_data,
            "heartbeat_protocol_version": "4.0",
            "network_stats": self.get_connection_stats(),
            "communication_quality": self._assess_connection_quality(),
            "heartbeat_timestamp": time.time(),
            "modular_heartbeat": True
        }
        
        success_count = 0
        total_nodes = len(self.connected_nodes)
        
        for node_url, node_info in self.connected_nodes.items():
            try:
                # Use the same API version that worked for registration
                api_version = node_info.get('api_version', 'v1')
                if api_version == 'v1':
                    endpoint = f"{node_url}/api/agents/heartbeat"
                else:
                    endpoint = f"{node_url}/api/{api_version}/agents/heartbeat"
                
                response = self._make_request('POST', endpoint, json=heartbeat_data)
                
                if response and response.get("success"):
                    node_info['last_heartbeat'] = time.time()
                    node_info['status'] = 'connected'
                    node_info['heartbeat_count'] = node_info.get('heartbeat_count', 0) + 1
                    success_count += 1
                    self.connection_stats['successful_requests'] += 1
                else:
                    node_info['status'] = 'heartbeat_failed'
                    error_msg = response.get('error', 'Unknown error') if response else 'No response'
                    print(f"⚠️ Heartbeat failed for {node_url}: {error_msg}")
                    
            except Exception as e:
                print(f"❌ Heartbeat error for {node_url}: {e}")
                node_info['status'] = 'error'
                self.connection_stats['failed_requests'] += 1
        
        success_rate = success_count / total_nodes if total_nodes > 0 else 0
        
        if success_count > 0:
            # Only print success messages occasionally to avoid spam
            if success_count == total_nodes and total_nodes > 0:
                print(f"💓 Heartbeat: {success_count}/{total_nodes} nodes (100%)")
        
        return success_count > 0
    
    def _make_request(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request with error handling and stats tracking"""
        try:
            # Calculate request size for stats
            request_data = kwargs.get('json', {})
            request_size = len(json.dumps(request_data)) if request_data else 0
            self.connection_stats['total_bytes_sent'] += request_size

            if self.session is None:
                raise RuntimeError('Network session unavailable')

            # Apply default timeout if none provided
            if 'timeout' not in kwargs:
                kwargs['timeout'] = self.request_timeout

            response = self.session.request(method, url, **kwargs)
            
            # Calculate response size for stats
            response_size = len(response.content) if response.content else 0
            self.connection_stats['total_bytes_received'] += response_size
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ HTTP {response.status_code} for {method} {url}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"⏰ Request timeout for {method} {url}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"🔌 Connection error for {method} {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"🌐 Request error for {method} {url}: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error for {method} {url}: {e}")
            return None
    
    def _assess_connection_quality(self) -> str:
        """Assess connection quality based on success rate"""
        total_requests = (self.connection_stats['successful_requests'] + 
                         self.connection_stats['failed_requests'])
        
        if total_requests == 0:
            return "unknown"
        
        success_rate = self.connection_stats['successful_requests'] / total_requests
        
        if success_rate >= 0.95:
            return "excellent"
        elif success_rate >= 0.85:
            return "good"
        elif success_rate >= 0.70:
            return "fair"
        else:
            return "poor"
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get detailed connection statistics"""
        total_requests = (self.connection_stats['successful_requests'] + 
                         self.connection_stats['failed_requests'])
        
        success_rate = 0
        if total_requests > 0:
            success_rate = self.connection_stats['successful_requests'] / total_requests
        
        return {
            **self.connection_stats,
            'total_requests': total_requests,
            'success_rate': success_rate,
            'connection_quality': self._assess_connection_quality(),
            'connected_nodes': len(self.connected_nodes),
            'active_connections': len([n for n in self.connected_nodes.values() 
                                     if n['status'] == 'connected'])
        }
    
    def get_node_info(self, node_url: str) -> Optional[Dict[str, Any]]:
        """Get information about specific node"""
        return self.connected_nodes.get(node_url)
    
    def disconnect_from_node(self, node_url: str) -> bool:
        """Disconnect from specific node"""
        if node_url in self.connected_nodes:
            del self.connected_nodes[node_url]
            print(f"🔌 Disconnected from {node_url}")
            return True
        return False
    
    def test_connection(self, url: str) -> Dict[str, Any]:
        """Test connection to specific URL"""
        start_time = time.time()
        
        try:
            response = self._make_request('GET', f"{url}/api/health")
            end_time = time.time()
            
            return {
                'success': response is not None,
                'response_time_ms': (end_time - start_time) * 1000,
                'status': 'healthy' if response else 'unhealthy',
                'response': response
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status': 'error'
            }
    
    def discover_nodes(self, discovery_urls: list) -> Dict[str, Any]:
        """Discover available nodes from discovery service"""
        discovered_nodes = {}
        
        for discovery_url in discovery_urls:
            try:
                response = self._make_request('GET', f"{discovery_url}/api/nodes")
                
                if response and 'nodes' in response:
                    for node in response['nodes']:
                        node_url = node.get('url')
                        if node_url:
                            # Test connection to node
                            test_result = self.test_connection(node_url)
                            discovered_nodes[node_url] = {
                                **node,
                                'discovered_from': discovery_url,
                                'test_result': test_result,
                                'discovered_at': time.time()
                            }
                            
            except Exception as e:
                print(f"⚠️ Node discovery failed for {discovery_url}: {e}")
        
        return discovered_nodes
    
    def get_status(self) -> Dict[str, Any]:
        """Get network manager status"""
        return {
            'node_url': self._node_url,
            'connected_nodes': len(self.connected_nodes),
            'active_connections': len([n for n in self.connected_nodes.values() 
                                     if n['status'] == 'connected']),
            'connection_quality': self._assess_connection_quality(),
            'total_requests': (self.connection_stats['successful_requests'] + 
                              self.connection_stats['failed_requests']),
            'success_rate': self.get_connection_stats()['success_rate'],
            'bytes_transferred': {
                'sent': self.connection_stats['total_bytes_sent'],
                'received': self.connection_stats['total_bytes_received']
            },
            'last_activity': max(
                [
                    t
                    for t in (
                        self.connection_stats.get('last_successful_connection'),
                        self.connection_stats.get('last_failed_connection'),
                    )
                    if t is not None
                ],
                default=None,
            )
        }
    
    def optimize_connections(self) -> Dict[str, Any]:
        """Optimize network connections"""
        optimizations = []
        
        # Remove dead connections
        dead_nodes = []
        current_time = time.time()
        
        for node_url, node_info in self.connected_nodes.items():
            # Consider connection dead if no heartbeat for 5 minutes
            if current_time - node_info.get('last_heartbeat', 0) > 300:
                dead_nodes.append(node_url)
        
        for node_url in dead_nodes:
            self.disconnect_from_node(node_url)
            optimizations.append(f"Removed dead connection: {node_url}")
        
        # Adjust timeouts based on connection quality
        quality = self._assess_connection_quality()
        if self.session is not None and quality in ['poor', 'fair']:
            new_timeout = min(60, self.request_timeout * 1.5)
            self.request_timeout = new_timeout
            optimizations.append(
                f"Increased timeout to {new_timeout}s due to {quality} connection quality"
            )
        
        return {
            'optimizations_applied': len(optimizations),
            'optimizations': optimizations,
            'connections_cleaned': len(dead_nodes),
            'connection_quality': quality
        }
    
    def export_network_logs(self, filepath: str) -> bool:
        """Export network activity logs"""
        try:
            log_data = {
                'connection_stats': self.connection_stats,
                'connected_nodes': self.connected_nodes,
                'network_status': self.get_status(),
                'exported_at': time.time()
            }
            
            with open(filepath, 'w') as f:
                json.dump(log_data, f, indent=2, default=str)
            
            print(f"📄 Network logs exported to {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to export network logs: {e}")
            return False
    
    def reset_stats(self):
        """Reset connection statistics"""
        self.connection_stats = {
            'successful_requests': 0,
            'failed_requests': 0,
            'total_bytes_sent': 0,
            'total_bytes_received': 0,
            'last_successful_connection': None,
            'last_failed_connection': None
        }
        print("📊 Network statistics reset")
    
    def close(self):
        """Close network manager and cleanup connections"""
        try:
            if self.session:
                self.session.close()
            self.connected_nodes.clear()
            print("🌐 Network manager closed")
        except Exception as e:
            print(f"⚠️ Network manager close warning: {e}")