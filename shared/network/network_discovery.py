"""
Network Discovery System for SelfDB

Handles Docker container service name resolution and URL generation
for cross-device and cross-environment compatibility.
"""
import os
from typing import Dict, List, Optional
from shared.config.config_manager import ConfigManager


class NetworkDiscoveryError(Exception):
    """Raised when network discovery operations fail."""
    pass


class NetworkDiscovery:
    """
    Main network discovery service for resolving container names and URLs.
    
    Handles:
    - Docker Compose service name resolution with project prefixes
    - Cross-environment compatibility (dev/staging/prod)
    - Internal vs external URL generation
    - Service availability discovery
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize NetworkDiscovery with optional ConfigManager."""
        self.config_manager = config_manager or ConfigManager()
        self.is_docker = os.getenv('DOCKER_ENV', 'false').lower() == 'true'
        self.project_name = os.getenv('COMPOSE_PROJECT_NAME', 'selfdb')
    
    def resolve_service_name(self, service: str) -> str:
        """
        Resolve service name with appropriate prefix for the environment.
        
        Args:
            service: Base service name (e.g., 'postgres', 'backend')
            
        Returns:
            Full service name with project prefix if in Docker environment
        """
        # Only skip prefix when explicitly in development mode (DOCKER_ENV=false)
        docker_env = os.getenv('DOCKER_ENV', '').lower()
        if docker_env == 'false':
            return service
        else:
            # Use project prefix in all other cases (Docker environment or default)
            return f"{self.project_name}_{service}"
    
    def get_internal_service_url(self, service: str, port: int) -> str:
        """
        Get internal service URL for container-to-container communication.
        
        Args:
            service: Service name
            port: Service port
            
        Returns:
            Service URL using Docker service names or localhost
        """
        if self.is_docker:
            service_name = self.resolve_service_name(service)
            if service == 'postgres':
                return f"postgresql://{service_name}:{port}"
            else:
                return f"http://{service_name}:{port}"
        else:
            if service == 'postgres':
                return f"postgresql://localhost:{port}"
            else:
                return f"http://localhost:{port}"
    
    def get_external_service_url(self, service: str) -> str:
        """
        Get external service URL for client/browser access.
        
        Args:
            service: Service name
            
        Returns:
            External URL using configured ports
        """
        port = self.config_manager.get_port(service)
        return f"http://localhost:{port}"
    
    def discover_available_services(self) -> List[str]:
        """
        Discover all available services in the current environment.
        
        Returns:
            List of available service names with appropriate prefixes
        """
        base_services = ['postgres', 'backend', 'storage', 'frontend', 'deno-runtime']
        
        if self.is_docker:
            return [self.resolve_service_name(service) for service in base_services]
        else:
            return base_services
    
    def discover_containers_on_network(self, network_name: str) -> List:
        """
        Discover containers on a specific Docker network.
        
        Args:
            network_name: Name of the Docker network
            
        Returns:
            List of container objects on the network
        """
        try:
            import docker
            client = docker.from_env()
            containers = client.containers.list()
            
            network_containers = []
            for container in containers:
                networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
                if network_name in networks:
                    network_containers.append(container)
            
            return network_containers
        except Exception:
            # Return empty list if Docker operations fail
            return []
    
    def get_container_network_info(self, container_name: str) -> Dict:
        """
        Get network information for a specific container.
        
        Args:
            container_name: Name of the container
            
        Returns:
            Dictionary containing network information
        """
        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(container_name)
            
            network_info = {'ip_address': None, 'aliases': []}
            networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
            
            for network_name, network_data in networks.items():
                if 'selfdb' in network_name:  # Focus on SelfDB networks
                    network_info['ip_address'] = network_data.get('IPAddress')
                    network_info['aliases'] = network_data.get('Aliases', [])
                    break
            
            return network_info
        except Exception:
            return {'ip_address': None, 'aliases': []}