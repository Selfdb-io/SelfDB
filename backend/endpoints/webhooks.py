"""
FastAPI endpoints for webhook management.
Webhooks & Functions Architecture - Phase Implementation.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request, Response
from pydantic import BaseModel, Field, ConfigDict

from shared.config.config_manager import ConfigManager
from shared.database.connection_manager import DatabaseConnectionManager
from shared.services.webhook_crud_manager import (
    WebhookCRUDManager,
    WebhookNotFoundError,
    WebhookAlreadyExistsError,
    WebhookValidationError,
)
from shared.services.webhook_delivery_crud_manager import WebhookDeliveryCRUDManager
from shared.models.webhook import Webhook, RetryBackoffStrategy
from shared.auth.jwt_service import JWTService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["webhooks"])

try:
    _config_manager = ConfigManager()
    _db_manager = DatabaseConnectionManager(_config_manager)
    webhook_crud_manager = WebhookCRUDManager(_db_manager)
    webhook_delivery_crud_manager = WebhookDeliveryCRUDManager(_db_manager)
except Exception as exc:
    logger.warning("Failed to initialize webhook CRUD managers: %s", exc)
    webhook_crud_manager = None
    webhook_delivery_crud_manager = None


# Pydantic request/response models
class CreateWebhookRequest(BaseModel):
    """Request model for creating a webhook."""
    name: str = Field(..., min_length=1, max_length=255)
    function_id: str
    description: Optional[str] = Field(None, max_length=1000)
    provider: Optional[str] = Field(None, max_length=50)
    provider_event_type: Optional[str] = Field(None, max_length=255)
    source_url: Optional[str] = Field(None, max_length=500)
    secret_key: str = Field(..., min_length=1)
    rate_limit_per_minute: int = Field(default=100, ge=1, le=10000)
    retry_attempts: int = Field(default=3, ge=1, le=10)
    retry_backoff_strategy: str = Field(default="exponential", pattern="^(exponential|linear|fixed)$")
    retry_delay_seconds: int = Field(default=60, ge=1, le=3600)
    retry_max_delay_seconds: int = Field(default=3600, ge=1, le=86400)

    model_config = ConfigDict(protected_namespaces=())


class UpdateWebhookRequest(BaseModel):
    """Request model for updating a webhook."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    secret_key: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=10000)
    retry_attempts: Optional[int] = Field(None, ge=1, le=10)
    retry_delay_seconds: Optional[int] = Field(None, ge=1, le=3600)

    model_config = ConfigDict(protected_namespaces=())


class WebhookResponse(BaseModel):
    """Response model for webhook data."""
    id: str
    function_id: str
    owner_id: str
    name: str
    description: Optional[str]
    provider: Optional[str]
    provider_event_type: Optional[str]
    source_url: Optional[str]
    webhook_token: str
    secret_key: str
    path_segment: str
    is_active: bool
    rate_limit_per_minute: int
    retry_attempts: int
    retry_backoff_strategy: str
    retry_delay_seconds: int
    retry_max_delay_seconds: int
    last_received_at: Optional[str]
    last_delivery_status: Optional[str]
    successful_delivery_count: int
    failed_delivery_count: int
    total_delivery_count: int
    created_at: str
    updated_at: str

    model_config = ConfigDict(protected_namespaces=())


class WebhookListResponse(BaseModel):
    """Response model for webhook list."""
    webhooks: List[WebhookResponse]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(protected_namespaces=())


class WebhookDeliveryResponse(BaseModel):
    """Response model for webhook delivery data."""
    id: str
    webhook_id: str
    function_id: str
    source_ip: Optional[str]
    source_user_agent: Optional[str]
    request_headers: Optional[Dict[str, Any]]
    request_body: Optional[Any]
    request_body_size_bytes: Optional[int]
    request_method: Optional[str]
    request_url: Optional[str]
    signature_header_name: Optional[str]
    signature_provided: Optional[str]
    signature_valid: Optional[bool]
    signature_error: Optional[str]
    payload_valid: Optional[bool]
    validation_errors: Optional[Any]
    transformed_payload: Optional[Any]
    transform_error: Optional[str]
    queued_at: Optional[str]
    status: str
    delivery_attempt: Optional[int]
    processing_started_at: Optional[str]
    function_execution_id: Optional[str]
    execution_result: Optional[Any]
    execution_error: Optional[str]
    error_message: Optional[str]
    execution_time_ms: Optional[int]
    response_status_code: Optional[int]
    response_headers: Optional[Dict[str, Any]]
    response_body: Optional[Any]
    retry_count: int
    next_retry_at: Optional[str]
    retry_reason: Optional[str]
    processed_by_user_id: Optional[str]
    processed_at: Optional[str]
    created_at: str
    received_at: Optional[str]
    processing_completed_at: Optional[str]
    updated_at: str

    model_config = ConfigDict(protected_namespaces=())


class WebhookDeliveryListResponse(BaseModel):
    """Response model for webhook delivery list."""
    deliveries: List[WebhookDeliveryResponse]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(protected_namespaces=())


async def get_current_user(request: Request) -> Dict[str, Any]:
    """Extract current user from request context set by auth middleware."""
    if not hasattr(request.state, "user_id"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return {
        "id": request.state.user_id,
        "role": getattr(request.state, "user_role", "USER"),
        "auth_method": getattr(request.state, "auth_method", "unknown"),
    }


@router.post(
    "/webhooks",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new webhook"
)
async def create_webhook(
    request: CreateWebhookRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> WebhookResponse:
    """
    Create a new webhook for a function.
    
    Args:
        request: Webhook creation request
        current_user: Authenticated user
        
    Returns:
        Created webhook details
        
    Raises:
        400: Invalid webhook data or name already exists
        401: Not authenticated
        500: Database error
    """
    if not webhook_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        function_id = uuid.UUID(request.function_id)

        owner_id_str = current_user.get("id")
        if not owner_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user context")

        try:
            owner_id = uuid.UUID(owner_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")

        webhook = await webhook_crud_manager.create_webhook(
            function_id=function_id,
            owner_id=owner_id,
            name=request.name,
            secret_key=request.secret_key,
            description=request.description,
            provider=request.provider,
            provider_event_type=request.provider_event_type,
            source_url=request.source_url,
            rate_limit_per_minute=request.rate_limit_per_minute,
            retry_attempts=request.retry_attempts,
            retry_backoff_strategy=RetryBackoffStrategy(request.retry_backoff_strategy)
        )
        
        # Compute delivery stats if possible
        last_received_at = webhook.last_received_at.isoformat() if webhook.last_received_at else None
        last_delivery_status = webhook.last_delivery_status
        successful = int(getattr(webhook, 'successful_delivery_count', 0) or 0)
        failed = int(getattr(webhook, 'failed_delivery_count', 0) or 0)
        total_count = int(getattr(webhook, 'total_delivery_count', 0) or 0)

        if webhook_delivery_crud_manager:
            try:
                stats = await webhook_delivery_crud_manager.get_delivery_stats(webhook_id=webhook.id)
                if stats:
                    total_count = int(stats.get('total_deliveries') or total_count)
                    successful = int(stats.get('successful_deliveries') or successful)
                    failed = int(stats.get('failed_deliveries') or failed)
                    newest = stats.get('newest_delivery')
                    if newest:
                        if hasattr(newest, 'isoformat'):
                            last_received_at = newest.isoformat()
                        else:
                            last_received_at = str(newest)
            except Exception as e:
                logger.warning(f"Failed to retrieve delivery stats for webhook {webhook.id}: {e}")

        return WebhookResponse(
            id=str(webhook.id),
            function_id=str(webhook.function_id),
            owner_id=str(webhook.owner_id),
            name=webhook.name,
            description=webhook.description,
            provider=webhook.provider,
            provider_event_type=webhook.provider_event_type,
            source_url=webhook.source_url,
            webhook_token=webhook.webhook_token,
            secret_key=webhook.secret_key,
            path_segment=webhook.path_segment,
            is_active=webhook.is_active,
            rate_limit_per_minute=webhook.rate_limit_per_minute,
            retry_attempts=webhook.retry_attempts,
            retry_backoff_strategy=webhook.retry_backoff_strategy.value,
            retry_delay_seconds=webhook.retry_delay_seconds,
            retry_max_delay_seconds=webhook.retry_max_delay_seconds,
            last_received_at=last_received_at,
            last_delivery_status=last_delivery_status,
            successful_delivery_count=successful,
            failed_delivery_count=failed,
            total_delivery_count=total_count,
            created_at=webhook.created_at.isoformat(),
            updated_at=webhook.updated_at.isoformat()
        )
    
    except WebhookAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except WebhookValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating webhook: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create webhook")


@router.get(
    "/webhooks",
    response_model=WebhookListResponse,
    summary="List all webhooks"
)
async def list_webhooks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> WebhookListResponse:
    """
    List all webhooks for the authenticated user.
    
    Args:
        limit: Maximum number of webhooks to return
        offset: Number of webhooks to skip
        current_user: Authenticated user
        
    Returns:
        List of webhooks with pagination info
        
    Raises:
        401: Not authenticated
        500: Database error
    """
    if not webhook_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        owner_id = current_user.get("id")
        
        webhooks = await webhook_crud_manager.list_webhooks(owner_id=owner_id)

        total = len(webhooks)
        paginated_webhooks = webhooks[offset:offset + limit]

        response_webhooks = []
        for w in paginated_webhooks:
            # Defaults from model
            last_received_at = w.last_received_at.isoformat() if w.last_received_at else None
            last_delivery_status = w.last_delivery_status
            successful = int(getattr(w, 'successful_delivery_count', 0) or 0)
            failed = int(getattr(w, 'failed_delivery_count', 0) or 0)
            total_count = int(getattr(w, 'total_delivery_count', 0) or 0)

            # Try to compute fresh stats from deliveries table if available
            if webhook_delivery_crud_manager:
                try:
                    stats = await webhook_delivery_crud_manager.get_delivery_stats(webhook_id=w.id)
                    if stats:
                        total_count = int(stats.get('total_deliveries') or total_count)
                        successful = int(stats.get('successful_deliveries') or successful)
                        failed = int(stats.get('failed_deliveries') or failed)
                        newest = stats.get('newest_delivery')
                        if newest:
                            # newest may be a datetime or a string depending on DB driver
                            if hasattr(newest, 'isoformat'):
                                last_received_at = newest.isoformat()
                            else:
                                last_received_at = str(newest)
                except Exception as e:
                    logger.warning(f"Failed to retrieve delivery stats for webhook {w.id}: {e}")

            response_webhooks.append(
                WebhookResponse(
                    id=str(w.id),
                    function_id=str(w.function_id),
                    owner_id=str(w.owner_id),
                    name=w.name,
                    description=w.description,
                    provider=w.provider,
                    provider_event_type=w.provider_event_type,
                    source_url=w.source_url,
                    webhook_token=w.webhook_token,
                    secret_key=w.secret_key,
                    path_segment=w.path_segment,
                    is_active=w.is_active,
                    rate_limit_per_minute=w.rate_limit_per_minute,
                    retry_attempts=w.retry_attempts,
                    retry_backoff_strategy=w.retry_backoff_strategy.value,
                    retry_delay_seconds=w.retry_delay_seconds,
                    retry_max_delay_seconds=w.retry_max_delay_seconds,
                    last_received_at=last_received_at,
                    last_delivery_status=last_delivery_status,
                    successful_delivery_count=successful,
                    failed_delivery_count=failed,
                    total_delivery_count=total_count,
                    created_at=w.created_at.isoformat(),
                    updated_at=w.updated_at.isoformat(),
                )
            )

        return WebhookListResponse(
            webhooks=response_webhooks,
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error listing webhooks: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list webhooks")


@router.get(
    "/webhooks/{webhook_id}",
    response_model=WebhookResponse,
    summary="Get webhook details"
)
async def get_webhook(
    webhook_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> WebhookResponse:
    """
    Get details for a specific webhook.
    
    Args:
        webhook_id: Webhook UUID
        current_user: Authenticated user
        
    Returns:
        Webhook details
        
    Raises:
        401: Not authenticated
        403: Not authorized
        404: Webhook not found
        500: Database error
    """
    if not webhook_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        webhook_uuid = uuid.UUID(webhook_id)
        webhook = await webhook_crud_manager.get_webhook(webhook_uuid)
        
        if str(webhook.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this webhook")
        
        return WebhookResponse(
            id=str(webhook.id),
            function_id=str(webhook.function_id),
            owner_id=str(webhook.owner_id),
            name=webhook.name,
            description=webhook.description,
            provider=webhook.provider,
            provider_event_type=webhook.provider_event_type,
            source_url=webhook.source_url,
            webhook_token=webhook.webhook_token,
            secret_key=webhook.secret_key,
            path_segment=webhook.path_segment,
            is_active=webhook.is_active,
            rate_limit_per_minute=webhook.rate_limit_per_minute,
            retry_attempts=webhook.retry_attempts,
            retry_backoff_strategy=webhook.retry_backoff_strategy.value,
            retry_delay_seconds=webhook.retry_delay_seconds,
            retry_max_delay_seconds=webhook.retry_max_delay_seconds,
            last_received_at=webhook.last_received_at.isoformat() if webhook.last_received_at else None,
            last_delivery_status=webhook.last_delivery_status,
            successful_delivery_count=webhook.successful_delivery_count,
            failed_delivery_count=webhook.failed_delivery_count,
            total_delivery_count=webhook.total_delivery_count,
            created_at=webhook.created_at.isoformat(),
            updated_at=webhook.updated_at.isoformat()
        )
    
    except WebhookNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook ID")
    except Exception as e:
        logger.error(f"Error retrieving webhook: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve webhook")


@router.put(
    "/webhooks/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update webhook configuration"
)
async def update_webhook(
    webhook_id: str,
    request: UpdateWebhookRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> WebhookResponse:
    """
    Update webhook configuration.
    
    Args:
        webhook_id: Webhook UUID
        request: Update request
        current_user: Authenticated user
        
    Returns:
        Updated webhook details
        
    Raises:
        400: Invalid update data
        401: Not authenticated
        403: Not authorized
        404: Webhook not found
        500: Database error
    """
    if not webhook_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        webhook_uuid = uuid.UUID(webhook_id)
        webhook = await webhook_crud_manager.get_webhook(webhook_uuid)
        
        if str(webhook.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this webhook")
        
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        if request.secret_key is not None:
            updates["secret_key"] = request.secret_key
        if request.is_active is not None:
            updates["is_active"] = request.is_active
        if request.rate_limit_per_minute is not None:
            updates["rate_limit_per_minute"] = request.rate_limit_per_minute
        if request.retry_attempts is not None:
            updates["retry_attempts"] = request.retry_attempts
        if request.retry_delay_seconds is not None:
            updates["retry_delay_seconds"] = request.retry_delay_seconds
        
        updated_webhook = await webhook_crud_manager.update_webhook(
            webhook_id=webhook_uuid,
            updates=updates
        )
        
        return WebhookResponse(
            id=str(updated_webhook.id),
            function_id=str(updated_webhook.function_id),
            owner_id=str(updated_webhook.owner_id),
            name=updated_webhook.name,
            description=updated_webhook.description,
            provider=updated_webhook.provider,
            provider_event_type=updated_webhook.provider_event_type,
            source_url=updated_webhook.source_url,
            webhook_token=updated_webhook.webhook_token,
            secret_key=updated_webhook.secret_key,
            path_segment=updated_webhook.path_segment,
            is_active=updated_webhook.is_active,
            rate_limit_per_minute=updated_webhook.rate_limit_per_minute,
            retry_attempts=updated_webhook.retry_attempts,
            retry_backoff_strategy=updated_webhook.retry_backoff_strategy.value,
            retry_delay_seconds=updated_webhook.retry_delay_seconds,
            retry_max_delay_seconds=updated_webhook.retry_max_delay_seconds,
            last_received_at=updated_webhook.last_received_at.isoformat() if updated_webhook.last_received_at else None,
            last_delivery_status=updated_webhook.last_delivery_status,
            successful_delivery_count=updated_webhook.successful_delivery_count,
            failed_delivery_count=updated_webhook.failed_delivery_count,
            total_delivery_count=updated_webhook.total_delivery_count,
            created_at=updated_webhook.created_at.isoformat(),
            updated_at=updated_webhook.updated_at.isoformat()
        )
    
    except WebhookNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    except WebhookValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook ID")
    except Exception as e:
        logger.error(f"Error updating webhook: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update webhook")


@router.delete(
    "/webhooks/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete webhook"
)
async def delete_webhook(
    webhook_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Response:
    """
    Delete a webhook.
    
    Args:
        webhook_id: Webhook UUID
        current_user: Authenticated user
        
    Raises:
        401: Not authenticated
        403: Not authorized
        404: Webhook not found
        500: Database error
    """
    if not webhook_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        webhook_uuid = uuid.UUID(webhook_id)
        webhook = await webhook_crud_manager.get_webhook(webhook_uuid)
        
        if str(webhook.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this webhook")
        
        await webhook_crud_manager.delete_webhook(webhook_uuid)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    except WebhookNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook ID")
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete webhook")


@router.get(
    "/webhooks/{webhook_id}/deliveries",
    response_model=WebhookDeliveryListResponse,
    summary="Get webhook delivery history"
)
async def get_webhook_deliveries(
    webhook_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> WebhookDeliveryListResponse:
    """
    Get delivery history for a webhook.
    
    Args:
        webhook_id: Webhook UUID
        current_user: Authenticated user
        limit: Maximum deliveries to return
        offset: Number of deliveries to skip
        
    Returns:
        Paginated delivery history
        
    Raises:
        401: Not authenticated
        403: Not authorized
        404: Webhook not found
        500: Database error
    """
    if not webhook_crud_manager or not webhook_delivery_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        webhook_uuid = uuid.UUID(webhook_id)
        webhook = await webhook_crud_manager.get_webhook(webhook_uuid)
        
        if str(webhook.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this webhook")
        
        deliveries = await webhook_delivery_crud_manager.list_deliveries(webhook_id=webhook_uuid)

        total = len(deliveries)
        paginated_deliveries = deliveries[offset:offset + limit]

        # Serialize full delivery objects so frontend can render the same fields that exist in DB
        serialized = []
        for d in paginated_deliveries:
            # Helper to isoformat datetimes if present
            def _fmt(dt):
                try:
                    return dt.isoformat() if dt is not None else None
                except Exception:
                    return str(dt) if dt is not None else None

            payload = {
                'id': str(d.id),
                'webhook_id': str(d.webhook_id),
                'function_id': str(d.function_id),
                'source_ip': getattr(d, 'source_ip', None),
                'source_user_agent': getattr(d, 'user_agent', None) or getattr(d, 'source_user_agent', None),
                'request_headers': getattr(d, 'request_headers', None),
                'request_body': getattr(d, 'request_body', None),
                'request_body_size_bytes': getattr(d, 'request_body_size_bytes', None),
                'request_method': getattr(d, 'request_method', None),
                'request_url': getattr(d, 'request_url', None),
                'signature_header_name': getattr(d, 'signature_header_name', None),
                'signature_provided': getattr(d, 'signature_header', None) or getattr(d, 'signature_provided', None),
                'signature_valid': getattr(d, 'signature_valid', None),
                'signature_error': getattr(d, 'signature_error', None),
                'payload_valid': getattr(d, 'payload_valid', None),
                'validation_errors': getattr(d, 'validation_errors', None),
                'transformed_payload': getattr(d, 'transformed_payload', None),
                'transform_error': getattr(d, 'transform_error', None),
                'queued_at': _fmt(getattr(d, 'queued_at', None)),
                'status': d.status.value if hasattr(d.status, 'value') else getattr(d, 'status', None),
                'delivery_attempt': getattr(d, 'delivery_attempt', None),
                'processing_started_at': _fmt(getattr(d, 'processing_started_at', None)),
                'function_execution_id': getattr(d, 'function_execution_id', None),
                'execution_result': getattr(d, 'execution_result', None),
                'execution_error': getattr(d, 'execution_error', None),
                'error_message': getattr(d, 'error_message', None),
                'execution_time_ms': getattr(d, 'execution_time_ms', None),
                'response_status_code': getattr(d, 'response_status_code', None),
                'response_headers': getattr(d, 'response_headers', None),
                'response_body': getattr(d, 'response_body', None),
                'retry_count': getattr(d, 'retry_count', 0) or 0,
                'next_retry_at': _fmt(getattr(d, 'next_retry_at', None)),
                'retry_reason': getattr(d, 'retry_reason', None),
                'processed_by_user_id': getattr(d, 'processed_by_user_id', None),
                'processed_at': _fmt(getattr(d, 'processed_at', None)),
                'created_at': _fmt(getattr(d, 'created_at', None)) or _fmt(getattr(d, 'created', None)),
                'received_at': _fmt(getattr(d, 'received_at', None)),
                'processing_completed_at': _fmt(getattr(d, 'processing_completed_at', None)),
                'updated_at': _fmt(getattr(d, 'updated_at', None)) or _fmt(getattr(d, 'updated', None)),
            }
            serialized.append(payload)

        return WebhookDeliveryListResponse(
            deliveries=serialized,
            total=total,
            limit=limit,
            offset=offset,
        )
    
    except WebhookNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook ID")
    except Exception as e:
        logger.error(f"Error retrieving webhook deliveries: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve webhook deliveries")


import hashlib
import hmac
from shared.services.function_deployment_manager import FunctionDeploymentManager

try:
    webhook_deployment_manager = FunctionDeploymentManager()
except Exception as exc:
    logger.warning("Failed to initialize FunctionDeploymentManager: %s", exc)
    webhook_deployment_manager = None


class WebhookIngestRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    """Request model for webhook ingestion (dynamic payload)."""
    
    
    def __init__(self, **data):
        super().__init__(**data)


@router.post(
    "/webhooks/ingest/{function_id}",
    summary="Ingest webhook payload and trigger function"
)
async def ingest_webhook(
    function_id: str,
    req: Request
) -> Dict[str, Any]:
    """
    Webhook ingestion endpoint that receives payloads from external providers.
    
    This endpoint:
    1. Validates webhook signature (if secret provided)
    2. Triggers function execution via Deno
    3. Returns immediately (async execution)
    
    Args:
        function_id: Function UUID to trigger
        req: Request containing webhook payload
        
    Returns:
        Acknowledgement with execution_id
        
    Raises:
        400: Invalid function_id or signature validation failed
        401: Unauthorized (invalid signature)
        404: Function or webhook not found
        500: Execution error
    """
    if not webhook_crud_manager or not webhook_deployment_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        func_id = uuid.UUID(function_id)
        logger.info(f"Starting webhook ingestion for function {function_id}")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid function ID format")
    
    try:
        # Get webhook for this function (there may be multiple)
        # For now, we'll use the first one or create a generic one
        logger.info(f"About to call list_webhooks for function {function_id}")
        webhooks = await webhook_crud_manager.list_webhooks()
        logger.info(f"list_webhooks returned {len(webhooks)} webhooks")
        webhook = None
        
        logger.info(f"Looking for webhook for function {function_id}, found {len(webhooks)} total webhooks")
        for w in webhooks:
            logger.info(f"Checking webhook {w.id} with function_id {w.function_id} (type: {type(w.function_id)})")
            if str(w.function_id) == function_id:
                webhook = w
                logger.info(f"Found matching webhook: {w.id}")
                break
        
        if not webhook:
            logger.warning(f"No webhook configured for function {function_id}")
            # Continue without webhook (no signature validation)
            webhook_secret = None
        else:
            webhook_secret = webhook.secret_key
        
        # Read and parse request body
        try:
            body_bytes = await req.body()
            payload = await req.json()
        except Exception as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")
        
        # Validate webhook signature if secret is provided
        if webhook_secret:
            signature_header = req.headers.get("x-webhook-signature") or req.headers.get("x-stripe-signature")
            
            if not signature_header:
                logger.warning(f"Missing signature header for webhook {function_id}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature")
            
            # Compute expected signature (HMAC-SHA256)
            expected_signature = hmac.new(
                webhook_secret.encode(),
                body_bytes,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures (timing-safe comparison)
            if not hmac.compare_digest(signature_header, expected_signature):
                logger.warning(f"Invalid signature for webhook {function_id}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
        
        # Create execution record
        execution_id = str(uuid.uuid4())
        delivery_id = str(uuid.uuid4())
        
        logger.info(
            f"Webhook ingested for function {function_id}: "
            f"execution_id={execution_id}, delivery_id={delivery_id}"
        )
        
        # Get environment variables for this function
        # (implementation depends on function_crud_manager having access to env_vars)
        env_vars = {}
        try:
            from shared.services.function_crud_manager import FunctionCRUDManager
            from shared.config.config_manager import ConfigManager
            from shared.database.connection_manager import DatabaseConnectionManager
            
            config_manager = ConfigManager()
            db_manager = DatabaseConnectionManager(config_manager)
            function_crud_manager_temp = FunctionCRUDManager(db_manager)
            
            function = await function_crud_manager_temp.get_function(func_id)
            env_vars = function.env_vars or {}
            
            logger.debug(f"Retrieved {len(env_vars)} env vars for function {function_id}")
            
        except Exception as e:
            logger.warning(f"Failed to retrieve function env vars: {e}")
        
        # Ensure signature_header is defined even if no secret (used later when storing)
        signature_header = locals().get('signature_header', None)

        # Store delivery record if webhook manager available (do this BEFORE triggering runtime)
        if webhook and webhook_delivery_crud_manager:
            logger.info(f"Creating delivery record for webhook {webhook.id} and function {function_id}")
            try:
                # Build request header dict
                try:
                    headers_dict = {k: v for k, v in req.headers.items()}
                except Exception:
                    headers_dict = {}

                # Decode body bytes to string for storage
                try:
                    body_text = body_bytes.decode('utf-8') if isinstance(body_bytes, (bytes, bytearray)) else str(body_bytes)
                except Exception:
                    body_text = ''

                client_host = None
                try:
                    client = req.client
                    if client and hasattr(client, 'host'):
                        client_host = client.host
                except Exception:
                    client_host = None

                delivery = await webhook_delivery_crud_manager.create_delivery(
                    webhook_id=webhook.id,
                    function_id=func_id,
                    request_headers=headers_dict,
                    request_body=body_text,
                    request_method=req.method,
                    request_url=str(req.url),
                    source_ip=client_host,
                    user_agent=req.headers.get('user-agent'),
                    signature_valid=True if webhook_secret else None,
                    signature_header=signature_header if webhook_secret else None
                )

                # Use the actual delivery ID from the created record
                delivery_id = str(delivery.id)

                logger.info(f"Stored delivery record: {delivery_id} for webhook {webhook.id}")

            except Exception as e:
                logger.warning(f"Failed to store delivery record: {e}")

        # Trigger function execution in Deno (async, don't wait)
        if webhook_deployment_manager:
            try:
                function_name = None
                if 'function' in locals() and hasattr(function, 'name'):
                    function_name = function.name

                if not function_name:
                    # Fallback to using the function_id string, but prefer the actual name
                    function_name = function_id

                # Send webhook to Deno for execution
                await webhook_deployment_manager.send_webhook(
                    function_name=function_name,
                    payload=payload,
                    env_vars=env_vars,
                    execution_id=execution_id,
                    delivery_id=delivery_id
                )

                logger.info(f"Webhook execution triggered in Deno: {execution_id}")

            except Exception as e:
                logger.error(f"Failed to trigger webhook execution: {e}")
                # Continue anyway - return acknowledgement even if trigger fails
        
        # Return immediately with execution_id (execution happens asynchronously)
        return {
            "success": True,
            "message": "Webhook received and queued for execution",
            "execution_id": execution_id,
            "delivery_id": delivery_id,
            "function_id": function_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook ingestion: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process webhook")
