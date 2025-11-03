"""
WebhookDelivery model implementation for SelfDB webhook delivery audit trail.
Based on Functions & Webhooks Improvement Plan requirements.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List


class WebhookDeliveryStatus(str, Enum):
    """Webhook delivery status enumeration."""
    RECEIVED = "received"
    VALIDATING = "validating"
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_PENDING = "retry_pending"


class WebhookDelivery:
    """
    WebhookDelivery model for tracking webhook delivery attempts and audit trail.
    
    Attributes:
        id: UUID primary key
        webhook_id: References Webhook.id
        function_id: References Function.id
        delivery_attempt: Attempt number (1-based)
        status: Current delivery status
        source_ip: IP address of webhook sender
        user_agent: User agent string
        request_headers: Full request headers (JSON)
        request_body: Raw request body
        request_method: HTTP method
        request_url: Request URL
        signature_valid: Whether HMAC signature was valid
        signature_header: Signature header value
        validation_errors: Validation error messages
        queued_at: When delivery was queued
        processing_started_at: When processing began
        processing_completed_at: When processing finished
        execution_time_ms: Total execution time
        response_status_code: HTTP response status
        response_headers: Response headers (JSON)
        response_body: Response body
        error_message: Error message if failed
        retry_count: Number of retries attempted
        next_retry_at: Next retry timestamp
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    def __init__(
        self,
        id: uuid.UUID,
        webhook_id: uuid.UUID,
        function_id: uuid.UUID,
        delivery_attempt: int = 1,
        status: WebhookDeliveryStatus = WebhookDeliveryStatus.RECEIVED,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_headers: Optional[Dict[str, str]] = None,
        request_body: Optional[str] = None,
        request_method: str = "POST",
        request_url: Optional[str] = None,
        signature_valid: Optional[bool] = None,
        signature_header: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
        queued_at: Optional[datetime] = None,
        processing_started_at: Optional[datetime] = None,
        processing_completed_at: Optional[datetime] = None,
        execution_time_ms: Optional[int] = None,
        response_status_code: Optional[int] = None,
        response_headers: Optional[Dict[str, str]] = None,
        response_body: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        next_retry_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        """
        Initialize a WebhookDelivery instance.
        
        Args:
            id: UUID for the delivery
            webhook_id: Associated webhook UUID
            function_id: Associated function UUID
            delivery_attempt: Attempt number
            status: Delivery status
            source_ip: Sender IP address
            user_agent: User agent string
            request_headers: Request headers dict
            request_body: Raw request body
            request_method: HTTP method
            request_url: Request URL
            signature_valid: Signature validation result
            signature_header: Signature header
            validation_errors: List of validation errors
            queued_at: Queued timestamp
            processing_started_at: Processing start timestamp
            processing_completed_at: Processing end timestamp
            execution_time_ms: Execution duration
            response_status_code: HTTP response status
            response_headers: Response headers dict
            response_body: Response body
            error_message: Error message
            retry_count: Retry attempts
            next_retry_at: Next retry timestamp
            created_at: Creation timestamp
            updated_at: Update timestamp
        """
        if not isinstance(webhook_id, uuid.UUID):
            raise ValueError("webhook_id must be a valid UUID")
        if not isinstance(function_id, uuid.UUID):
            raise ValueError("function_id must be a valid UUID")
        if delivery_attempt < 1:
            raise ValueError("delivery_attempt must be >= 1")
        
        self.id = id
        self.webhook_id = webhook_id
        self.function_id = function_id
        self.delivery_attempt = delivery_attempt
        self.status = status
        self.source_ip = source_ip
        self.user_agent = user_agent
        self.request_headers = request_headers or {}
        self.request_body = request_body
        self.request_method = request_method
        self.request_url = request_url
        self.signature_valid = signature_valid
        self.signature_header = signature_header
        self.validation_errors = validation_errors or []
        self.queued_at = queued_at
        self.processing_started_at = processing_started_at
        self.processing_completed_at = processing_completed_at
        self.execution_time_ms = execution_time_ms
        self.response_status_code = response_status_code
        self.response_headers = response_headers or {}
        self.response_body = response_body
        self.error_message = error_message
        self.retry_count = retry_count
        self.next_retry_at = next_retry_at
        
        # Set timestamps
        now = datetime.now(timezone.utc)
        self.created_at = created_at or now
        self.updated_at = updated_at or now
    
    @classmethod
    def create(
        cls,
        webhook_id: uuid.UUID,
        function_id: uuid.UUID,
        request_headers: Dict[str, str],
        request_body: str,
        request_method: str = "POST",
        request_url: Optional[str] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> 'WebhookDelivery':
        """
        Create a new webhook delivery instance.
        
        Args:
            webhook_id: Associated webhook UUID
            function_id: Associated function UUID
            request_headers: HTTP request headers
            request_body: Raw request body
            request_method: HTTP method
            request_url: Request URL
            source_ip: Sender IP
            user_agent: User agent
            
        Returns:
            New WebhookDelivery instance
        """
        return cls(
            id=uuid.uuid4(),
            webhook_id=webhook_id,
            function_id=function_id,
            request_headers=request_headers,
            request_body=request_body,
            request_method=request_method,
            request_url=request_url,
            source_ip=source_ip,
            user_agent=user_agent,
            queued_at=datetime.now(timezone.utc)
        )
    
    def start_processing(self) -> None:
        """Mark delivery as started processing."""
        self.status = WebhookDeliveryStatus.EXECUTING
        self.processing_started_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def complete_processing(
        self,
        success: bool,
        response_status_code: Optional[int] = None,
        response_headers: Optional[Dict[str, str]] = None,
        response_body: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Mark delivery as completed.
        
        Args:
            success: Whether processing was successful
            response_status_code: HTTP response status
            response_headers: Response headers
            response_body: Response body
            execution_time_ms: Execution duration
            error_message: Error message if failed
        """
        self.processing_completed_at = datetime.now(timezone.utc)
        self.execution_time_ms = execution_time_ms
        self.response_status_code = response_status_code
        self.response_headers = response_headers or {}
        self.response_body = response_body
        self.error_message = error_message
        
        if success:
            self.status = WebhookDeliveryStatus.COMPLETED
        else:
            self.status = WebhookDeliveryStatus.FAILED
            
        self.updated_at = datetime.now(timezone.utc)
    
    def schedule_retry(self, next_retry_at: datetime) -> None:
        """
        Schedule a retry for this delivery.
        
        Args:
            next_retry_at: When to retry
        """
        self.status = WebhookDeliveryStatus.RETRY_PENDING
        self.retry_count += 1
        self.next_retry_at = next_retry_at
        self.updated_at = datetime.now(timezone.utc)
    
    def add_validation_error(self, error: str) -> None:
        """
        Add a validation error to this delivery.
        
        Args:
            error: Validation error message
        """
        if self.validation_errors is None:
            self.validation_errors = []
        self.validation_errors.append(error)
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert delivery to dictionary.
        
        Returns:
            Dictionary representation of delivery
        """
        return {
            "id": str(self.id),
            "webhook_id": str(self.webhook_id),
            "function_id": str(self.function_id),
            "delivery_attempt": self.delivery_attempt,
            "status": self.status.value,
            "source_ip": self.source_ip,
            "user_agent": self.user_agent,
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "request_method": self.request_method,
            "request_url": self.request_url,
            "signature_valid": self.signature_valid,
            "signature_header": self.signature_header,
            "validation_errors": self.validation_errors,
            "queued_at": self.queued_at.isoformat() if self.queued_at else None,
            "processing_started_at": self.processing_started_at.isoformat() if self.processing_started_at else None,
            "completed_at": self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            "execution_time_ms": self.execution_time_ms,
            "response_status_code": self.response_status_code,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def __str__(self) -> str:
        """String representation of delivery."""
        return f"<WebhookDelivery {self.id} ({self.status.value})>"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return f"<WebhookDelivery(id={self.id}, webhook={self.webhook_id}, status={self.status.value}, attempt={self.delivery_attempt})>"