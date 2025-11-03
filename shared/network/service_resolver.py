"""
Service Resolver for Dynamic URL Generation

Generates API URLs based on request context (internal vs external)
and provides context-aware service resolution.
"""
import os
from typing import Dict, Optional
from shared.config.config_manager import ConfigManager
from shared.network.network_discovery import NetworkDiscovery


class ServiceResolver:
    """
    Resolves service URLs dynamically based on request context.
    
    Handles:
    - Internal vs external URL generation
    - Custom host configuration for remote access
    - Context-aware URL resolution
    - Mobile and cross-device compatibility
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize ServiceResolver."""
        self.config_manager = config_manager or ConfigManager()
        self.network_discovery = NetworkDiscovery(config_manager)
    
    def generate_api_urls(self, context: str, host: Optional[str] = None) -> Dict[str, str]:
        """
        Generate API URLs for different contexts.
        
        Args:
            context: 'internal' for container-to-container, 'external' for browser
            host: Custom host for external URLs (default: localhost)
            
        Returns:
            Dictionary of service URLs
        """
        if context == 'internal':
            return self._generate_internal_urls()
        elif context == 'external':
            return self._generate_external_urls(host)
        else:
            raise ValueError(f"Unknown context: {context}")
    
    def _generate_internal_urls(self) -> Dict[str, str]:
        """Generate URLs for internal container communication."""
        return {
            'backend_url': self.network_discovery.get_internal_service_url('backend', 8000),
            'storage_url': self.network_discovery.get_internal_service_url('storage', 8001),
            'functions_url': self.network_discovery.get_internal_service_url('deno-runtime', 8090)
        }
    
    def _generate_external_urls(self, host: Optional[str] = None) -> Dict[str, str]:
        """Generate URLs for external browser access."""
        host = host or 'localhost'
        
        backend_port = self.config_manager.get_port('backend')
        storage_port = self.config_manager.get_port('storage')
        functions_port = self.config_manager.get_port('deno-runtime')
        
        return {
            'backend_url': f'http://{host}:{backend_port}',
            'storage_url': f'http://{host}:{storage_port}',
            'functions_url': f'http://{host}:{functions_port}'
        }
    
    def resolve_urls_for_client(self) -> Dict[str, str]:
        """
        Resolve URLs for client based on detected context.
        
        Returns:
            Dictionary of service URLs optimized for the client context
        """
        context = self._detect_request_context()
        
        if context == 'mobile_browser':
            # For mobile browsers, use external URLs
            return self.generate_api_urls('external')
        else:
            # Default to external URLs
            return self.generate_api_urls('external')
    
    def _detect_request_context(self) -> str:
        """
        Detect the request context for URL resolution.
        
        Returns:
            Context string ('mobile_browser', 'desktop_browser', etc.)
        """
        # Simplified context detection for minimal implementation
        # In real implementation, this would analyze request headers
        return 'mobile_browser'