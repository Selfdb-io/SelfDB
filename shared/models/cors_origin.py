"""
CORS Origin model for managing allowed cross-origin request sources.
Based on admin access control requirements for CORS management.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlparse


class CorsOrigin:
    """
    CORS Origin model for managing allowed cross-origin request sources.

    Attributes:
        id: UUID primary key
        origin: The allowed origin URL (e.g., "https://app.example.com")
        description: Optional description of the origin
        is_active: Whether this origin is currently active
        extra_metadata: Additional metadata as JSON
        created_by: UUID of the user who created this origin
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    def __init__(
        self,
        id: uuid.UUID,
        origin: str,
        description: Optional[str] = None,
        is_active: bool = True,
        extra_metadata: Optional[Dict[str, Any]] = None,
        created_by: uuid.UUID = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        """
        Initialize a CorsOrigin instance.

        Args:
            id: UUID for the CORS origin
            origin: Origin URL (must be valid URL format)
            description: Optional description
            is_active: Whether the origin is active (defaults to True)
            extra_metadata: Additional metadata
            created_by: UUID of the user who created this origin
            created_at: Creation timestamp (defaults to now)
            updated_at: Update timestamp (defaults to now)
        """
        if not origin:
            raise ValueError("Origin is required")

        # Validate origin format
        self._validate_origin(origin)

        self.id = id
        self.origin = origin.strip()
        self.description = description
        self.is_active = is_active
        self.extra_metadata = extra_metadata or {}
        self.created_by = created_by

        # Set timestamps
        now = datetime.now(timezone.utc)
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    def _validate_origin(self, origin: str) -> None:
        """
        Validate that the origin is a properly formatted URL.

        Args:
            origin: The origin URL to validate

        Raises:
            ValueError: If the origin format is invalid
        """
        if not origin or not isinstance(origin, str):
            raise ValueError("Origin must be a non-empty string")

        origin = origin.strip()

        # Allow "*" for wildcard
        if origin == "*":
            return

        try:
            parsed = urlparse(origin)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
            if parsed.scheme not in ['http', 'https']:
                raise ValueError("Origin must use http or https scheme")
        except Exception as e:
            raise ValueError(f"Invalid origin URL: {str(e)}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the CorsOrigin instance to a dictionary.

        Returns:
            Dictionary representation of the CORS origin
        """
        return {
            'id': str(self.id),
            'origin': self.origin,
            'description': self.description,
            'is_active': self.is_active,
            'extra_metadata': self.extra_metadata,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorsOrigin':
        """
        Create a CorsOrigin instance from a dictionary.

        Args:
            data: Dictionary containing CORS origin data

        Returns:
            CorsOrigin instance
        """
        return cls(
            id=uuid.UUID(data['id']),
            origin=data['origin'],
            description=data.get('description'),
            is_active=data.get('is_active', True),
            extra_metadata=data.get('extra_metadata', {}),
            created_by=uuid.UUID(data['created_by']) if data.get('created_by') else None,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )

    def update(self, **kwargs) -> None:
        """
        Update CORS origin attributes.

        Args:
            **kwargs: Attributes to update
        """
        allowed_fields = {'origin', 'description', 'is_active', 'extra_metadata'}

        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == 'origin' and value is not None:
                    self._validate_origin(value)
                    self.origin = value.strip()
                elif field == 'description':
                    self.description = value
                elif field == 'is_active':
                    self.is_active = bool(value)
                elif field == 'extra_metadata':
                    self.extra_metadata = value or {}

        self.updated_at = datetime.now(timezone.utc)