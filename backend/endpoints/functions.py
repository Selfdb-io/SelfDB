"""
FastAPI endpoints for serverless function CRUD and execution.
Functions and Webhooks Architecture - Phase Implementation.
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
from shared.services.function_crud_manager import (
    FunctionCRUDManager,
    FunctionNotFoundError,
    FunctionAlreadyExistsError,
    FunctionValidationError,
)
from shared.services.function_deployment_manager import FunctionDeploymentManager
from shared.services.function_log_crud_manager import FunctionLogCRUDManager
from shared.services.function_execution_crud_manager import FunctionExecutionCRUDManager
from shared.models.function import Function, FunctionRuntime, DeploymentStatus
from shared.models.function_log import FunctionLog
from shared.auth.jwt_service import JWTService
from shared.services.webhook_delivery_crud_manager import WebhookDeliveryCRUDManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["functions"])

try:
    _config_manager = ConfigManager()
    _db_manager = DatabaseConnectionManager(_config_manager)
    function_crud_manager = FunctionCRUDManager(_db_manager)
    function_deployment_manager = FunctionDeploymentManager()
    function_log_crud_manager = FunctionLogCRUDManager(_db_manager)
    function_execution_crud_manager = FunctionExecutionCRUDManager(_db_manager)
    webhook_delivery_crud_manager = WebhookDeliveryCRUDManager(_db_manager)
except Exception as exc:
    logger.warning("Failed to initialize CRUD managers: %s", exc)
    function_crud_manager = None
    function_deployment_manager = None
    function_log_crud_manager = None
    function_execution_crud_manager = None
    webhook_delivery_crud_manager = None


# Pydantic request/response models
class CreateFunctionRequest(BaseModel):
    """Request model for creating a new function."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    code: str = Field(..., min_length=1)
    runtime: str = Field(default="deno", pattern="^(deno|node|python)$")
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    memory_limit_mb: int = Field(default=512, ge=128, le=4096)
    max_concurrent: int = Field(default=10, ge=1, le=100)
    env_vars: Optional[Dict[str, str]] = Field(default=None)

    model_config = ConfigDict(protected_namespaces=())


class UpdateFunctionRequest(BaseModel):
    """Request model for updating a function."""
    description: Optional[str] = Field(None, max_length=1000)
    code: Optional[str] = Field(None, min_length=1)
    timeout_seconds: Optional[int] = Field(None, ge=5, le=300)
    memory_limit_mb: Optional[int] = Field(None, ge=128, le=4096)
    max_concurrent: Optional[int] = Field(None, ge=1, le=100)

    model_config = ConfigDict(protected_namespaces=())


class SetFunctionStateRequest(BaseModel):
    """Request model for enabling/disabling a function."""
    is_active: bool

    model_config = ConfigDict(protected_namespaces=())


class SetEnvVarsRequest(BaseModel):
    """Request model for setting environment variables."""
    env_vars: Dict[str, str] = Field(..., min_length=1)

    model_config = ConfigDict(protected_namespaces=())


class FunctionResponse(BaseModel):
    """Response model for function data."""
    id: str
    name: str
    description: Optional[str]
    code: str
    runtime: str
    owner_id: str
    is_active: bool
    deployment_status: str
    deployment_error: Optional[str]
    version: int
    timeout_seconds: int
    memory_limit_mb: int
    max_concurrent: int
    env_vars: Dict[str, str]
    execution_count: int
    execution_success_count: int
    execution_error_count: int
    last_executed_at: Optional[str]
    avg_execution_time_ms: Optional[int]
    last_deployed_at: Optional[str]
    created_at: str
    updated_at: str

    model_config = ConfigDict(protected_namespaces=())


class FunctionListResponse(BaseModel):
    """Response model for function list."""
    functions: List[FunctionResponse]
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
    "/functions",
    response_model=FunctionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new function"
)
async def create_function(
    request: CreateFunctionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> FunctionResponse:
    """
    Create a new serverless function.
    
    Auto-deploys to Deno runtime upon creation.
    
    Args:
        request: Function creation request
        current_user: Authenticated user
        
    Returns:
        Created function details
        
    Raises:
        400: Invalid function data or name already exists
        401: Not authenticated
        500: Database or deployment error
    """
    if not function_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        owner_id_str = current_user.get("id")
        if not owner_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user context")
        
        try:
            owner_id = uuid.UUID(owner_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
        
        runtime_enum = FunctionRuntime(request.runtime)
        
        function = await function_crud_manager.create_function(
            name=request.name,
            code=request.code,
            owner_id=owner_id,
            description=request.description,
            runtime=runtime_enum,
            timeout_seconds=request.timeout_seconds,
            memory_limit_mb=request.memory_limit_mb,
            max_concurrent=request.max_concurrent,
            env_vars=request.env_vars
        )
        
        # Auto-deploy to Deno runtime
        if function_deployment_manager:
            try:
                deployment_result = await function_deployment_manager.deploy_function(
                    function_name=function.name,
                    code=function.code,
                    is_active=function.is_active,
                    env_vars=function.env_vars
                )
                # Update deployment status in database
                await function_crud_manager.update_deployment_status(
                    function_id=function.id,
                    status=DeploymentStatus.DEPLOYED if deployment_result["success"] else DeploymentStatus.FAILED,
                    error=None if deployment_result["success"] else deployment_result.get("message", "Deployment failed")
                )
                logger.info(f"Auto-deployed function {function.name}: {deployment_result}")
            except Exception as deploy_exc:
                logger.error(f"Failed to auto-deploy function {function.name}: {deploy_exc}")
                # Update deployment status to failed but don't fail the creation
                try:
                    await function_crud_manager.update_deployment_status(
                        function_id=function.id,
                        status=DeploymentStatus.FAILED,
                        error=str(deploy_exc)
                    )
                except Exception as status_exc:
                    logger.error(f"Failed to update deployment status for {function.name}: {status_exc}")
        
        return FunctionResponse(
            id=str(function.id),
            name=function.name,
            description=function.description,
            code=function.code,
            runtime=function.runtime.value,
            owner_id=str(function.owner_id),
            is_active=function.is_active,
            deployment_status=function.deployment_status.value,
            deployment_error=function.deployment_error,
            version=function.version,
            timeout_seconds=function.timeout_seconds,
            memory_limit_mb=function.memory_limit_mb,
            max_concurrent=function.max_concurrent,
            env_vars=dict(function.env_vars) if function.env_vars else {},
            execution_count=function.execution_count,
            execution_success_count=function.execution_success_count,
            execution_error_count=function.execution_error_count,
            last_executed_at=function.last_executed_at.isoformat() if function.last_executed_at else None,
            avg_execution_time_ms=function.avg_execution_time_ms,
            last_deployed_at=function.last_deployed_at.isoformat() if function.last_deployed_at else None,
            created_at=function.created_at.isoformat(),
            updated_at=function.updated_at.isoformat()
        )
    
    except FunctionAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FunctionValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating function: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create function")


@router.get(
    "/functions",
    response_model=FunctionListResponse,
    summary="List all functions"
)
async def list_functions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> FunctionListResponse:
    """
    List all functions for the authenticated user.
    
    Args:
        limit: Maximum number of functions to return
        offset: Number of functions to skip
        current_user: Authenticated user
        
    Returns:
        List of functions with pagination info
        
    Raises:
        401: Not authenticated
        500: Database error
    """
    if not function_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        owner_id = current_user.get("id")
        
        functions = await function_crud_manager.list_functions(
            owner_id=owner_id
        )
        
        # Apply pagination to the results
        total = len(functions)
        paginated_functions = functions[offset:offset + limit]
        
        return FunctionListResponse(
            functions=[
                FunctionResponse(
                    id=str(fn.id),
                    name=fn.name,
                    description=fn.description,
                    code=fn.code,
                    runtime=fn.runtime.value,
                    owner_id=str(fn.owner_id),
                    is_active=fn.is_active,
                    deployment_status=fn.deployment_status.value,
                    deployment_error=fn.deployment_error,
                    version=fn.version,
                    timeout_seconds=fn.timeout_seconds,
                    memory_limit_mb=fn.memory_limit_mb,
                    max_concurrent=fn.max_concurrent,
                    env_vars=dict(fn.env_vars) if fn.env_vars else {},
                    execution_count=fn.execution_count,
                    execution_success_count=fn.execution_success_count,
                    execution_error_count=fn.execution_error_count,
                    last_executed_at=fn.last_executed_at.isoformat() if fn.last_executed_at else None,
                    avg_execution_time_ms=fn.avg_execution_time_ms,
                    last_deployed_at=fn.last_deployed_at.isoformat() if fn.last_deployed_at else None,
                    created_at=fn.created_at.isoformat(),
                    updated_at=fn.updated_at.isoformat()
                )
                for fn in paginated_functions
            ],
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error listing functions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list functions")


@router.get(
    "/functions/{function_id}",
    response_model=FunctionResponse,
    summary="Get function details"
)
async def get_function(
    function_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> FunctionResponse:
    """
    Get details for a specific function.
    
    Args:
        function_id: Function UUID
        current_user: Authenticated user
        
    Returns:
        Function details
        
    Raises:
        401: Not authenticated
        404: Function not found or not owned by user
        500: Database error
    """
    if not function_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        function = await function_crud_manager.get_function(function_id)
        
        if str(function.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this function")
        
        return FunctionResponse(
            id=str(function.id),
            name=function.name,
            description=function.description,
            code=function.code,
            runtime=function.runtime.value,
            owner_id=str(function.owner_id),
            is_active=function.is_active,
            deployment_status=function.deployment_status.value,
            deployment_error=function.deployment_error,
            version=function.version,
            timeout_seconds=function.timeout_seconds,
            memory_limit_mb=function.memory_limit_mb,
            max_concurrent=function.max_concurrent,
            env_vars=dict(function.env_vars) if function.env_vars else {},
            execution_count=function.execution_count,
            execution_success_count=function.execution_success_count,
            execution_error_count=function.execution_error_count,
            last_executed_at=function.last_executed_at.isoformat() if function.last_executed_at else None,
            avg_execution_time_ms=function.avg_execution_time_ms,
            last_deployed_at=function.last_deployed_at.isoformat() if function.last_deployed_at else None,
            created_at=function.created_at.isoformat(),
            updated_at=function.updated_at.isoformat()
        )
    
    except FunctionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Function not found")
    except Exception as e:
        logger.error(f"Error retrieving function: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve function")



@router.post(
    "/functions/{function_name}/execution-result",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive execution result callbacks from runtime"
)
async def receive_execution_result(
    function_name: str,
    request: Request
) -> Response:
    """Endpoint for runtimes to post execution results. Expects JSON body with execution_id, delivery_id, success, result, logs, execution_time_ms."""
    if not function_crud_manager or not function_execution_crud_manager or not function_log_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    execution_id = body.get("execution_id")
    delivery_id = body.get("delivery_id")
    success = bool(body.get("success"))
    result = body.get("result")
    logs = body.get("logs", [])
    execution_time_ms = body.get("execution_time_ms")
    timestamp = body.get("timestamp")

    # Serialize result to string if it's not already
    if result is not None and not isinstance(result, str):
        import json
        result = json.dumps(result)

    if not execution_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="execution_id is required")

    try:
        execution_uuid = uuid.UUID(execution_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid execution_id format")

    try:
        # Get function by name
        function = await function_crud_manager.get_function_by_name(function_name)
        
        # Get user (assume first user for now - in real implementation, this should be determined from execution context)
        # For now, we'll use the function owner
        user_id = function.owner_id

        # Create execution record
        execution = await function_execution_crud_manager.create_execution(
            function_id=function.id,
            user_id=user_id,
            trigger_type="webhook" if delivery_id else "http",  # Default trigger type
            trigger_source=f"runtime_callback_{function_name}",
            webhook_delivery_id=uuid.UUID(delivery_id) if delivery_id else None
        )

        # Complete the execution
        await function_execution_crud_manager.complete_execution(
            execution_id=execution.id,
            success=success,
            result=result,
            memory_used_mb=None,  # Runtime doesn't provide this yet
            cpu_usage_percent=None,  # Runtime doesn't provide this yet
            error_message=str(result) if not success else None,
            error_stack_trace=None,
            error_type=None,
            env_vars_used=None,
            execution_trace=None
        )

        # Create log records
        if logs:
            log_entries = []
            for log_line in logs:
                if isinstance(log_line, str):
                    # Parse log level from message if possible
                    log_level = "info"
                    message = log_line
                    if log_line.upper().startswith("ERROR"):
                        log_level = "error"
                    elif log_line.upper().startswith("WARN"):
                        log_level = "warn"
                    elif log_line.upper().startswith("DEBUG"):
                        log_level = "debug"
                    
                    from shared.models.function_log import LogLevel
                    log_entries.append(
                        FunctionLog.create(
                            execution_id=execution.id,
                            function_id=function.id,
                            message=message,
                            log_level=LogLevel(log_level),
                            source="runtime"
                        )
                    )
            
            if log_entries:
                await function_log_crud_manager.bulk_create_logs(log_entries)

        # Update function execution metrics (legacy support)
        await function_crud_manager.record_execution(function.id, success, execution_time_ms)

        # If delivery_id provided, mark delivery complete
        if delivery_id and webhook_delivery_crud_manager:
            try:
                delivery_uuid = uuid.UUID(delivery_id)
                await webhook_delivery_crud_manager.complete_processing(
                    delivery_uuid,
                    success=success,
                    response_status_code=200 if success else 500,
                    response_body=str(result) if result is not None else None,
                    execution_time_ms=execution_time_ms,
                    error_message=None if success else str(result)
                )
            except Exception as e:
                logger.error(f"Failed to update webhook delivery {delivery_id}: {e}")

        return Response(status_code=status.HTTP_202_ACCEPTED)

    except Exception as e:
        logger.error(f"Error processing execution result for {function_name}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process execution result")


@router.put(
    "/functions/{function_id}",
    response_model=FunctionResponse,
    summary="Update function code"
)
async def update_function(
    function_id: str,
    request: UpdateFunctionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> FunctionResponse:
    """
    Update function code and configuration.
    
    Auto-redeploys to Deno upon code changes.
    
    Args:
        function_id: Function UUID
        request: Update request
        current_user: Authenticated user
        
    Returns:
        Updated function details
        
    Raises:
        400: Invalid update data
        401: Not authenticated
        403: Not authorized
        404: Function not found
        500: Database or deployment error
    """
    if not function_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        func_id = uuid.UUID(function_id)
        function = await function_crud_manager.get_function(func_id)
        
        if str(function.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this function")
        
        # Build updates dictionary
        updates = {}
        if request.description is not None:
            updates["description"] = request.description
        if request.code is not None:
            updates["code"] = request.code
        if request.timeout_seconds is not None:
            updates["timeout_seconds"] = request.timeout_seconds
        if request.memory_limit_mb is not None:
            updates["memory_limit_mb"] = request.memory_limit_mb
        if request.max_concurrent is not None:
            updates["max_concurrent"] = request.max_concurrent
        
        updated_function = await function_crud_manager.update_function(
            function_id=func_id,
            updates=updates
        )
        
        return FunctionResponse(
            id=str(updated_function.id),
            name=updated_function.name,
            description=updated_function.description,
            code=updated_function.code,
            runtime=updated_function.runtime.value,
            owner_id=str(updated_function.owner_id),
            is_active=updated_function.is_active,
            deployment_status=updated_function.deployment_status.value,
            deployment_error=updated_function.deployment_error,
            version=updated_function.version,
            timeout_seconds=updated_function.timeout_seconds,
            memory_limit_mb=updated_function.memory_limit_mb,
            max_concurrent=updated_function.max_concurrent,
            env_vars=dict(updated_function.env_vars) if updated_function.env_vars else {},
            execution_count=updated_function.execution_count,
            execution_success_count=updated_function.execution_success_count,
            execution_error_count=updated_function.execution_error_count,
            last_executed_at=updated_function.last_executed_at.isoformat() if updated_function.last_executed_at else None,
            avg_execution_time_ms=updated_function.avg_execution_time_ms,
            last_deployed_at=updated_function.last_deployed_at.isoformat() if updated_function.last_deployed_at else None,
            created_at=updated_function.created_at.isoformat(),
            updated_at=updated_function.updated_at.isoformat()
        )
    
    except FunctionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Function not found")
    except FunctionValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating function: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update function")


@router.patch(
    "/functions/{function_id}/state",
    response_model=FunctionResponse,
    summary="Enable/disable function"
)
async def set_function_state(
    function_id: str,
    request: SetFunctionStateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> FunctionResponse:
    """
    Enable or disable a function.
    
    When enabled: function is deployed to Deno and processes triggers
    When disabled: function is undeployed from Deno (no triggers processed)
    
    Args:
        function_id: Function UUID
        request: State request with is_active flag
        current_user: Authenticated user
        
    Returns:
        Updated function details
        
    Raises:
        401: Not authenticated
        403: Not authorized
        404: Function not found
        500: Database or deployment error
    """
    if not function_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        function = await function_crud_manager.get_function(function_id)
        
        if str(function.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this function")
        
        updated_function = await function_crud_manager.set_function_state(
            function_id=function_id,
            is_active=request.is_active
        )
        
        return FunctionResponse(
            id=str(updated_function.id),
            name=updated_function.name,
            description=updated_function.description,
            runtime=updated_function.runtime.value,
            owner_id=str(updated_function.owner_id),
            is_active=updated_function.is_active,
            deployment_status=updated_function.deployment_status.value,
            deployment_error=updated_function.deployment_error,
            version=updated_function.version,
            timeout_seconds=updated_function.timeout_seconds,
            memory_limit_mb=updated_function.memory_limit_mb,
            max_concurrent=updated_function.max_concurrent,
            env_vars=dict(updated_function.env_vars) if updated_function.env_vars else {},
            execution_count=updated_function.execution_count,
            execution_success_count=updated_function.execution_success_count,
            execution_error_count=updated_function.execution_error_count,
            last_executed_at=updated_function.last_executed_at.isoformat() if updated_function.last_executed_at else None,
            avg_execution_time_ms=updated_function.avg_execution_time_ms,
            last_deployed_at=updated_function.last_deployed_at.isoformat() if updated_function.last_deployed_at else None,
            created_at=updated_function.created_at.isoformat(),
            updated_at=updated_function.updated_at.isoformat()
        )
    
    except FunctionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Function not found")
    except Exception as e:
        logger.error(f"Error updating function state: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update function state")


@router.delete(
    "/functions/{function_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete function"
)
async def delete_function(
    function_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Response:
    """
    Delete a function and all related data.
    
    Also removes from Deno runtime and cleans up execution history.
    
    Args:
        function_id: Function UUID
        current_user: Authenticated user
        
    Raises:
        401: Not authenticated
        403: Not authorized
        404: Function not found
        500: Database or deletion error
    """
    if not function_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        function = await function_crud_manager.get_function(function_id)
        
        if str(function.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this function")
        
        await function_crud_manager.delete_function(function_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    except FunctionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Function not found")
    except Exception as e:
        logger.error(f"Error deleting function: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete function")


@router.post(
    "/functions/{function_id}/env-vars",
    response_model=FunctionResponse,
    summary="Set environment variables"
)
async def set_env_vars(
    function_id: str,
    request: SetEnvVarsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> FunctionResponse:
    """
    Set environment variables for a function.
    
    Variables are encrypted at rest and never exposed in responses.
    
    Args:
        function_id: Function UUID
        request: Environment variables to set
        current_user: Authenticated user
        
    Returns:
        Updated function with env var names (values not exposed)
        
    Raises:
        400: Invalid env vars
        401: Not authenticated
        403: Not authorized
        404: Function not found
        500: Database error
    """
    if not function_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        function = await function_crud_manager.get_function(function_id)
        
        if str(function.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this function")
        
        updated_function = await function_crud_manager.set_env_vars(
            function_id=function_id,
            env_vars=request.env_vars
        )
        
        return FunctionResponse(
            id=str(updated_function.id),
            name=updated_function.name,
            description=updated_function.description,
            runtime=updated_function.runtime.value,
            owner_id=str(updated_function.owner_id),
            is_active=updated_function.is_active,
            deployment_status=updated_function.deployment_status.value,
            deployment_error=updated_function.deployment_error,
            version=updated_function.version,
            timeout_seconds=updated_function.timeout_seconds,
            memory_limit_mb=updated_function.memory_limit_mb,
            max_concurrent=updated_function.max_concurrent,
            env_vars=dict(updated_function.env_vars) if updated_function.env_vars else {},
            execution_count=updated_function.execution_count,
            execution_success_count=updated_function.execution_success_count,
            execution_error_count=updated_function.execution_error_count,
            last_executed_at=updated_function.last_executed_at.isoformat() if updated_function.last_executed_at else None,
            avg_execution_time_ms=updated_function.avg_execution_time_ms,
            last_deployed_at=updated_function.last_deployed_at.isoformat() if updated_function.last_deployed_at else None,
            created_at=updated_function.created_at.isoformat(),
            updated_at=updated_function.updated_at.isoformat()
        )
    
    except FunctionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Function not found")
    except FunctionValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting env vars: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set environment variables")


@router.get(
    "/functions/{function_id}/env-vars",
    summary="Get environment variable names"
)
async def get_env_vars(
    function_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, List[str]]:
    """
    Get environment variable names for a function.
    
    Note: Only variable names are returned, not values (for security).
    
    Args:
        function_id: Function UUID
        current_user: Authenticated user
        
    Returns:
        List of env var names
        
    Raises:
        401: Not authenticated
        403: Not authorized
        404: Function not found
        500: Database error
    """
    if not function_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        function = await function_crud_manager.get_function(function_id)
        
        if str(function.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this function")
        
        return {"env_vars": list(function.env_vars.keys()) if function.env_vars else []}
    
    except FunctionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Function not found")
    except Exception as e:
        logger.error(f"Error retrieving env vars: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve environment variables")


@router.get(
    "/functions/{function_id}/logs",
    summary="Get function execution logs"
)
async def get_function_logs(
    function_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    Get execution logs for a function.
    
    Returns paginated logs from all executions of the function.
    
    Args:
        function_id: Function UUID
        current_user: Authenticated user
        limit: Maximum number of logs to return
        offset: Number of logs to skip
        
    Returns:
        Paginated list of logs
        
    Raises:
        401: Not authenticated
        403: Not authorized
        404: Function not found
        500: Database error
    """
    if not function_crud_manager or not function_log_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        func_id = uuid.UUID(function_id)
        function = await function_crud_manager.get_function(func_id)
        
        if str(function.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this function")
        
        logs = await function_log_crud_manager.get_function_logs(
            function_id=func_id
        )
        
        # Apply pagination
        total = len(logs)
        paginated_logs = logs[offset:offset + limit]
        
        return {
            "logs": [
                {
                    "id": log.id if hasattr(log, 'id') else idx,
                    "execution_id": str(log.execution_id) if hasattr(log, 'execution_id') else None,
                    "level": log.log_level if hasattr(log, 'log_level') else "info",
                    "message": log.message if hasattr(log, 'message') else str(log),
                    "timestamp": log.timestamp.isoformat() if hasattr(log, 'timestamp') and log.timestamp else None,
                    "source": log.source if hasattr(log, 'source') else "function"
                }
                for idx, log in enumerate(paginated_logs)
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    except FunctionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Function not found")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid function ID")
    except Exception as e:
        logger.error(f"Error retrieving function logs: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve function logs")


@router.get(
    "/functions/{function_id}/metrics",
    summary="Get function execution metrics"
)
async def get_function_metrics(
    function_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get execution metrics and statistics for a function.
    
    Includes execution counts, success rates, average execution time, etc.
    
    Args:
        function_id: Function UUID
        current_user: Authenticated user
        
    Returns:
        Function execution metrics
        
    Raises:
        401: Not authenticated
        403: Not authorized
        404: Function not found
        500: Database error
    """
    if not function_crud_manager or not function_execution_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        func_id = uuid.UUID(function_id)
        function = await function_crud_manager.get_function(func_id)
        
        if str(function.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this function")
        
        # Get execution stats
        executions = await function_execution_crud_manager.list_executions(
            function_id=func_id
        )
        
        total_executions = len(executions)
        successful = sum(1 for e in executions if hasattr(e, 'status') and e.status == "completed")
        failed = sum(1 for e in executions if hasattr(e, 'status') and e.status in ["failed", "timeout"])
        
        # Calculate average execution time
        execution_times = [
            e.duration_ms for e in executions 
            if hasattr(e, 'duration_ms') and e.duration_ms is not None
        ]
        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        return {
            "function_id": str(function.id),
            "total_executions": total_executions,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": (successful / total_executions * 100) if total_executions > 0 else 0,
            "average_execution_time_ms": avg_time,
            "execution_count": function.execution_count,
            "execution_success_count": function.execution_success_count,
            "execution_error_count": function.execution_error_count,
            "last_executed_at": function.last_executed_at.isoformat() if function.last_executed_at else None,
            "avg_execution_time_ms": function.avg_execution_time_ms,
            "is_active": function.is_active,
            "deployment_status": function.deployment_status.value
        }
    
    except FunctionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Function not found")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid function ID")
    except Exception as e:
        logger.error(f"Error retrieving function metrics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve function metrics")


@router.get(
    "/functions/{function_id}/executions",
    summary="Get function executions"
)
async def get_function_executions(
    function_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by status"),
    trigger_type: Optional[str] = Query(None, description="Filter by trigger type")
) -> Dict[str, Any]:
    """
    Get paginated executions for a function.
    
    Args:
        function_id: Function UUID
        current_user: Authenticated user
        limit: Maximum number of executions to return
        offset: Number of executions to skip
        status: Filter by execution status
        trigger_type: Filter by trigger type
        
    Returns:
        Paginated list of function executions
        
    Raises:
        401: Not authenticated
        403: Not authorized
        404: Function not found
        500: Database error
    """
    if not function_crud_manager or not function_execution_crud_manager:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Service unavailable")
    
    try:
        func_id = uuid.UUID(function_id)
        function = await function_crud_manager.get_function(func_id)
        
        if str(function.owner_id) != current_user.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this function")
        
        # Get executions
        executions = await function_execution_crud_manager.list_executions(
            function_id=func_id,
            status=status,
            trigger_type=trigger_type,
            limit=limit,
            offset=offset
        )
        
        total = len(await function_execution_crud_manager.list_executions(
            function_id=func_id,
            status=status,
            trigger_type=trigger_type,
            limit=10000,  # Large limit to get total count
            offset=0
        ))
        
        return {
            "executions": [
                {
                    "id": str(e.id),
                    "function_id": str(e.function_id),
                    "user_id": str(e.user_id),
                    "trigger_type": e.trigger_type,
                    "trigger_source": e.trigger_source,
                    "webhook_delivery_id": str(e.webhook_delivery_id) if e.webhook_delivery_id else None,
                    "status": e.status,
                    "started_at": e.started_at.isoformat() if e.started_at else None,
                    "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                    "duration_ms": e.duration_ms,
                    "memory_used_mb": e.memory_used_mb,
                    "cpu_usage_percent": e.cpu_usage_percent,
                    "result": e.result,
                    "error_message": e.error_message,
                    "error_type": e.error_type,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "updated_at": e.updated_at.isoformat() if e.updated_at else None
                }
                for e in executions
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    except FunctionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Function not found")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid function ID")
    except Exception as e:
        logger.error(f"Error retrieving function executions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve function executions")
