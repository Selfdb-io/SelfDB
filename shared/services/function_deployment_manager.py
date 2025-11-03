"""
Function Deployment Manager

Handles deployment of function code from Backend to Deno runtime.
Manages function lifecycle: deploy, update, undeploy.
"""

import httpx
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class FunctionDeploymentManager:
    """Manages function code deployment to Deno runtime."""
    
    def __init__(self):
        """Initialize deployment manager."""
        deno_host = os.getenv("DENO_HOST", "deno")
        deno_port = os.getenv("DENO_PORT", "8090")
        self.deno_url = f"http://{deno_host}:{deno_port}"
        
        logger.info(f"FunctionDeploymentManager initialized with Deno URL: {self.deno_url}")
    
    async def deploy_function(
        self, 
        function_name: str, 
        code: str, 
        is_active: bool = True,
        timeout: int = 30,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Deploy function code to Deno runtime.
        
        Args:
            function_name: Name of function (will be used as filename)
            code: TypeScript/JavaScript code content
            is_active: Whether function should be immediately active
            timeout: Request timeout in seconds
            
        Returns:
            {
                "success": bool,
                "message": str,
                "function_name": str,
                "deployment_status": "deployed" | "failed"
            }
            
        Raises:
            Exception: If deployment fails
        """
        try:
            logger.info(f"Deploying function: {function_name}")
            
            if not function_name or not code:
                raise ValueError("function_name and code are required")
            
            if len(code) > 1_000_000:
                raise ValueError("Function code exceeds 1MB limit")
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.deno_url}/deploy",
                    json={
                        "functionName": function_name,
                        "code": code,
                        "isActive": is_active,
                        "env": env_vars or {}
                    }
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(
                        f"Deployment failed for {function_name}: "
                        f"HTTP {response.status_code}: {error_text}"
                    )
                    raise Exception(
                        f"Deno deployment failed: {response.status_code} - {error_text}"
                    )
                
                result = response.json()
                logger.info(f"Successfully deployed function: {function_name}")
                
                return {
                    "success": True,
                    "message": f"Function {function_name} deployed successfully",
                    "function_name": function_name,
                    "deployment_status": "deployed"
                }
                
        except httpx.RequestError as e:
            logger.error(f"Network error deploying function {function_name}: {e}")
            raise Exception(f"Deno connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error deploying function {function_name}: {e}")
            raise
    
    async def update_function(
        self, 
        function_name: str, 
        code: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Update existing function code (redeploy)."""
        return await self.deploy_function(function_name, code, timeout=timeout)
    
    async def undeploy_function(
        self, 
        function_name: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Undeploy function from Deno runtime (remove file)."""
        try:
            logger.info(f"Undeploying function: {function_name}")
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.delete(
                    f"{self.deno_url}/deploy/{function_name}"
                )
                
                if response.status_code not in [200, 204]:
                    error_text = response.text
                    logger.warning(
                        f"Undeployment may have failed for {function_name}: "
                        f"HTTP {response.status_code}"
                    )
                
                logger.info(f"Successfully undeployed function: {function_name}")
                
                return {
                    "success": True,
                    "message": f"Function {function_name} undeployed",
                    "function_name": function_name
                }
                
        except Exception as e:
            logger.error(f"Error undeploying function {function_name}: {e}")
            return {
                "success": False,
                "message": f"Error undeploying: {str(e)}",
                "function_name": function_name
            }
    
    async def send_webhook(
        self,
        function_name: str,
        payload: Dict[str, Any],
        env_vars: Dict[str, str],
        execution_id: str,
        delivery_id: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """Send webhook payload to Deno for function execution."""
        try:
            logger.info(
                f"Sending webhook to function {function_name}: "
                f"execution_id={execution_id}, delivery_id={delivery_id}"
            )
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.deno_url}/webhook/{function_name}",
                    json={
                        "payload": payload,
                        "env_vars": env_vars,
                        "execution_id": execution_id,
                        "delivery_id": delivery_id,
                        "function_name": function_name
                    },
                    headers={
                        "X-Execution-ID": execution_id,
                        "X-Delivery-ID": delivery_id
                    }
                )
                
                if response.status_code not in [200, 202]:
                    error_text = response.text
                    logger.error(
                        f"Webhook send failed for {function_name}: "
                        f"HTTP {response.status_code}: {error_text}"
                    )
                    raise Exception(
                        f"Webhook execution failed: {response.status_code} - {error_text}"
                    )
                
                logger.info(
                    f"Webhook sent successfully to {function_name}: "
                    f"execution_id={execution_id}"
                )
                
                return {
                    "success": True,
                    "message": f"Webhook queued for execution",
                    "queued": True,
                    "execution_id": execution_id
                }
                
        except httpx.RequestError as e:
            logger.error(f"Network error sending webhook to {function_name}: {e}")
            raise Exception(f"Deno connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Error sending webhook to {function_name}: {e}")
            raise
