"""
Proxy Configuration Generator for Frontend Middleware

Generates proxy configurations for different environments and proxy servers
to route frontend requests to backend services.
"""
import os
from typing import Dict, List, Any, Optional
from shared.config.config_manager import ConfigManager
from shared.network.network_discovery import NetworkDiscovery


class ProxyConfigGenerator:
    """
    Generates proxy configurations for frontend middleware.
    
    Supports:
    - Development and production environments
    - Webpack development server proxy
    - Nginx proxy configuration
    - Docker service routing
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize ProxyConfigGenerator."""
        self.config_manager = config_manager or ConfigManager()
        self.network_discovery = NetworkDiscovery(config_manager)
        self.is_docker = os.getenv('DOCKER_ENV', 'false').lower() == 'true'
    
    def generate_proxy_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Generate general proxy configuration.
        
        Returns:
            Dictionary containing proxy rules for different routes
        """
        if self.is_docker:
            return self._generate_docker_proxy_config()
        else:
            return self._generate_development_proxy_config()
    
    def _generate_development_proxy_config(self) -> Dict[str, Dict[str, Any]]:
        """Generate proxy configuration for development environment."""
        backend_port = self.config_manager.get_port('backend')
        storage_port = self.config_manager.get_port('storage')
        
        return {
            '/api': {
                'target': f'http://localhost:{backend_port}',
                'changeOrigin': True,
                'secure': False
            },
            '/storage': {
                'target': f'http://localhost:{storage_port}',
                'changeOrigin': True,
                'secure': False
            }
        }
    
    def _generate_docker_proxy_config(self) -> Dict[str, Dict[str, Any]]:
        """Generate proxy configuration for Docker environment."""
        backend_service = self.network_discovery.resolve_service_name('backend')
        storage = self.network_discovery.resolve_service_name('storage')
        backend_port = self.config_manager.get_port('backend')
        storage_port = self.config_manager.get_port('storage')
        
        return {
            '/api': {
                'target': f'http://{backend_service}:{backend_port}',
                'changeOrigin': True,
                'secure': False
            },
            '/storage': {
                'target': f'http://{storage}:{storage_port}',
                'changeOrigin': True,
                'secure': False
            }
        }
    
    def generate_webpack_proxy_config(self) -> Dict[str, Any]:
        """
        Generate Webpack development server proxy configuration.
        
        Returns:
            Webpack proxy configuration object
        """
        proxy_rules = []
        base_config = self.generate_proxy_config()
        
        for path, config in base_config.items():
            proxy_rules.append({
                'context': [f'{path}/**'],
                'target': config['target'],
                'changeOrigin': config['changeOrigin'],
                'secure': config.get('secure', False)
            })
        
        return {'proxy': proxy_rules}
    
    def generate_nginx_proxy_config(self) -> str:
        """
        Generate Nginx proxy configuration.
        
        Returns:
            Nginx configuration string with proxy_pass directives
        """
        base_config = self.generate_proxy_config()
        nginx_config = []
        
        for path, config in base_config.items():
            nginx_config.extend([
                f"location {path} {{",
                f"    proxy_pass {config['target']};",
                "    proxy_set_header Host $host;",
                "    proxy_set_header X-Real-IP $remote_addr;",
                "    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
                "}",
                ""
            ])
        
        return '\n'.join(nginx_config)