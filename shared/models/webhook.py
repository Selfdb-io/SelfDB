"""
Webhook model implementation for SelfDB webhook integrations.
Based on Functions & Webhooks Improvement Plan requirements.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any


class RetryBackoffStrategy(str, Enum):
    """Webhook retry backoff strategy enumeration."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


class Webhook:
    """
    Webhook model for external integration management.
    
    Attributes:
        id: UUID primary key
        function_id: References Function.id
        owner_id: References User.id
        name: Webhook name
        description: Optional description
        provider: External provider (stripe, github, etc.)
        provider_event_type: Provider-specific event type
        source_url: External webhook source URL
        webhook_token: Unique token for webhook routing
        secret_key: HMAC secret for signature verification
        path_segment: Generated path for routing
        is_active: Webhook enabled/disabled status
        rate_limit_per_minute: Rate limiting
        max_queue_size: Maximum queued deliveries
        retry_enabled: Whether retries are enabled
        retry_attempts: Maximum retry attempts
        retry_backoff_strategy: Retry backoff strategy
        retry_delay_seconds: Initial retry delay
        retry_max_delay_seconds: Maximum retry delay
        payload_schema: JSON schema for payload validation
        expected_headers: Expected HTTP headers
        transform_script: Optional payload transformation
        is_active_delivery: Current delivery status
        last_received_at: Last webhook received timestamp
        last_delivery_status: Last delivery status
        successful_delivery_count: Successful deliveries
        failed_delivery_count: Failed deliveries
        total_delivery_count: Total deliveries
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    def __init__(
        self,
        id: uuid.UUID,
        function_id: uuid.UUID,
        owner_id: uuid.UUID,
        name: str,
        webhook_token: str,
        secret_key: str,
        description: Optional[str] = None,
        provider: Optional[str] = None,
        provider_event_type: Optional[str] = None,
        source_url: Optional[str] = None,
        is_active: bool = True,
        rate_limit_per_minute: int = 100,
        max_queue_size: Optional[int] = 1000,
        retry_enabled: bool = True,
        retry_attempts: int = 3,
        retry_backoff_strategy: RetryBackoffStrategy = RetryBackoffStrategy.EXPONENTIAL,
        retry_delay_seconds: int = 60,
        retry_max_delay_seconds: int = 3600,
        payload_schema: Optional[Dict[str, Any]] = None,
        expected_headers: Optional[Dict[str, str]] = None,
        transform_script: Optional[str] = None,
        is_active_delivery: Optional[bool] = None,
        last_received_at: Optional[datetime] = None,
        last_delivery_status: Optional[str] = None,
        successful_delivery_count: int = 0,
        failed_delivery_count: int = 0,
        total_delivery_count: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        """
        Initialize a Webhook instance.
        
        Args:
            id: UUID for the webhook
            function_id: UUID of the associated function
            owner_id: UUID of the webhook owner
            name: Webhook name
            webhook_token: Unique token for routing
            secret_key: HMAC secret for verification
            description: Optional description
            provider: External provider name
            provider_event_type: Provider event type
            source_url: External source URL
            is_active: Webhook active status
            rate_limit_per_minute: Rate limit (1-10000)
            max_queue_size: Max queued deliveries
            retry_enabled: Enable retries
            retry_attempts: Max retry attempts (1-10)
            retry_backoff_strategy: Retry strategy
            retry_delay_seconds: Initial delay (1-3600)
            retry_max_delay_seconds: Max delay
            payload_schema: JSON schema for validation
            expected_headers: Expected headers dict
            transform_script: Transformation script
            is_active_delivery: Current delivery status
            last_received_at: Last received timestamp
            last_delivery_status: Last delivery status
            successful_delivery_count: Success count
            failed_delivery_count: Failed count
            total_delivery_count: Total count
            created_at: Creation timestamp
            updated_at: Update timestamp
        """
        if not name:
            raise ValueError("Webhook name is required")
        if not isinstance(function_id, uuid.UUID):
            raise ValueError("function_id must be a valid UUID")
        if not isinstance(owner_id, uuid.UUID):
            raise ValueError("owner_id must be a valid UUID")
        if not webhook_token:
            raise ValueError("webhook_token is required")
        if not secret_key:
            raise ValueError("secret_key is required")
        
        # Validate constraints
        if not (1 <= rate_limit_per_minute <= 10000):
            raise ValueError("rate_limit_per_minute must be between 1 and 10000")
        if not (1 <= retry_attempts <= 10):
            raise ValueError("retry_attempts must be between 1 and 10")
        if not (1 <= retry_delay_seconds <= 3600):
            raise ValueError("retry_delay_seconds must be between 1 and 3600")
        
        self.id = id
        self.function_id = function_id
        self.owner_id = owner_id
        self.name = name
        self.description = description
        self.provider = provider
        self.provider_event_type = provider_event_type
        self.source_url = source_url
        self.webhook_token = webhook_token
        self.secret_key = secret_key
        self.path_segment = self._generate_path_segment()
        self.is_active = is_active
        self.rate_limit_per_minute = rate_limit_per_minute
        self.max_queue_size = max_queue_size
        self.retry_enabled = retry_enabled
        self.retry_attempts = retry_attempts
        self.retry_backoff_strategy = retry_backoff_strategy
        self.retry_delay_seconds = retry_delay_seconds
        self.retry_max_delay_seconds = retry_max_delay_seconds
        self.payload_schema = payload_schema
        self.expected_headers = expected_headers or {}
        self.transform_script = transform_script
        self.is_active_delivery = is_active_delivery
        self.last_received_at = last_received_at
        self.last_delivery_status = last_delivery_status
        self.successful_delivery_count = successful_delivery_count
        self.failed_delivery_count = failed_delivery_count
        self.total_delivery_count = total_delivery_count
        
        # Set timestamps
        now = datetime.now(timezone.utc)
        self.created_at = created_at or now
        self.updated_at = updated_at or now
    
    def _generate_path_segment(self) -> str:
        """Generate path segment for webhook routing."""
        provider_part = self.provider or "custom"
        return f"{provider_part}_{self.webhook_token}"
    
    @classmethod
    def create(
        cls,
        function_id: uuid.UUID,
        owner_id: uuid.UUID,
        name: str,
        secret_key: str,
        description: Optional[str] = None,
        provider: Optional[str] = None,
        provider_event_type: Optional[str] = None,
        source_url: Optional[str] = None,
        rate_limit_per_minute: int = 100,
        retry_attempts: int = 3,
        retry_backoff_strategy: RetryBackoffStrategy = RetryBackoffStrategy.EXPONENTIAL
    ) -> 'Webhook':
        """
        Create a new webhook instance.
        
        Args:
            function_id: Associated function UUID
            owner_id: Owner UUID
            name: Webhook name
            secret_key: HMAC secret
            description: Optional description
            provider: External provider
            provider_event_type: Provider event type
            source_url: External URL
            rate_limit_per_minute: Rate limit
            retry_attempts: Max retries
            retry_backoff_strategy: Retry strategy
            
        Returns:
            New Webhook instance
        """
        import secrets
        webhook_token = secrets.token_urlsafe(32)
        
        return cls(
            id=uuid.uuid4(),
            function_id=function_id,
            owner_id=owner_id,
            name=name,
            webhook_token=webhook_token,
            secret_key=secret_key,
            description=description,
            provider=provider,
            provider_event_type=provider_event_type,
            source_url=source_url,
            rate_limit_per_minute=rate_limit_per_minute,
            retry_attempts=retry_attempts,
            retry_backoff_strategy=retry_backoff_strategy
        )
    
    def record_delivery(self, success: bool, status: str) -> None:
        """
        Record a webhook delivery attempt.
        
        Args:
            success: Whether delivery was successful
            status: Delivery status string
        """
        self.total_delivery_count += 1
        if success:
            self.successful_delivery_count += 1
        else:
            self.failed_delivery_count += 1
        
        self.last_delivery_status = status
        self.last_received_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def get_webhook_url(self, base_url: str) -> str:
        """
        Get the full webhook URL for this webhook.
        
        Args:
            base_url: Base URL of the SelfDB instance
            
        Returns:
            Complete webhook URL
        """
        return f"{base_url}/webhooks/ingest/{self.webhook_token}"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert webhook to dictionary, excluding sensitive data.
        
        Returns:
            Dictionary representation of webhook
        """
        return {
            "id": str(self.id),
            "function_id": str(self.function_id),
            "owner_id": str(self.owner_id),
            "name": self.name,
            "description": self.description,
            "provider": self.provider,
            "provider_event_type": self.provider_event_type,
            "source_url": self.source_url,
            "webhook_token": self.webhook_token,
            "path_segment": self.path_segment,
            "is_active": self.is_active,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "max_queue_size": self.max_queue_size,
            "retry_enabled": self.retry_enabled,
            "retry_attempts": self.retry_attempts,
            "retry_backoff_strategy": self.retry_backoff_strategy.value,
            "retry_delay_seconds": self.retry_delay_seconds,
            "retry_max_delay_seconds": self.retry_max_delay_seconds,
            "payload_schema": self.payload_schema,
            "expected_headers": self.expected_headers,
            "transform_script": self.transform_script,
            "is_active_delivery": self.is_active_delivery,
            "last_received_at": self.last_received_at.isoformat() if self.last_received_at else None,
            "last_delivery_status": self.last_delivery_status,
            "successful_delivery_count": self.successful_delivery_count,
            "failed_delivery_count": self.failed_delivery_count,
            "total_delivery_count": self.total_delivery_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def __str__(self) -> str:
        """String representation of webhook."""
        return f"<Webhook {self.name} ({self.provider or 'custom'})>"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return f"<Webhook(id={self.id}, name={self.name}, provider={self.provider}, active={self.is_active})>"