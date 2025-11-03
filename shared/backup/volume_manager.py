"""
Docker Volume Manager

Handles Docker volume discovery and enumeration.
"""

import docker
from typing import Dict, List, Any, Optional


class VolumeManager:
    """Manages Docker volume discovery and operations."""
    
    def __init__(self, docker_client=None):
        """Initialize VolumeManager with Docker client."""
        if docker_client is None:
            self.docker_client = docker.from_env()
        else:
            self.docker_client = docker_client
    
    def list_volumes(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """List Docker volumes, optionally filtered by prefix."""
        volumes = self.docker_client.volumes.list()
        volume_list = []
        
        for volume in volumes:
            volume_name = volume.name
            
            # Filter by prefix if specified
            if prefix and not volume_name.startswith(prefix):
                continue
                
            volume_info = {
                'name': volume_name,
                'driver': volume.attrs.get('Driver', 'unknown'),
                'mountpoint': volume.attrs.get('Mountpoint', '')
            }
            volume_list.append(volume_info)
            
        return volume_list
    
    def get_volume_metadata(self, volume_name: str) -> Dict[str, Any]:
        """Get detailed metadata for a specific volume."""
        volume = self.docker_client.volumes.get(volume_name)
        
        return {
            'name': volume.attrs['Name'],
            'driver': volume.attrs['Driver'],
            'mountpoint': volume.attrs['Mountpoint'],
            'created_at': volume.attrs.get('CreatedAt'),
            'labels': volume.attrs.get('Labels', {}),
            'options': volume.attrs.get('Options', {}),
            'scope': volume.attrs.get('Scope', 'local')
        }