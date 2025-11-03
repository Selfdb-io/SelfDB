"""
Backend API Service - Unified API Gateway
FastAPI service with unified file endpoints using existing proxy components
"""
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Global PG NOTIFY listener instance
pg_listener: Optional[Any] = None

# Import file, function, webhook, webhook reception, function execution, and realtime endpoints
try:
    # Docker environment (relative imports)
    from endpoints.files import router as files_router
    from endpoints.users import router as users_router
    from endpoints.admin_users import router as admin_users_router
    from endpoints.realtime import router as realtime_router
    from endpoints.tables import router as tables_router
    from endpoints.sql import router as sql_router
    from endpoints.buckets import router as buckets_router
    from endpoints.functions import router as functions_router
    from endpoints.webhooks import router as webhooks_router
    from endpoints.cors import router as cors_router
    from middleware.auth import CombinedAuthMiddleware
except ImportError:
    # Local environment (absolute imports)
    from backend.endpoints.files import router as files_router
    from backend.endpoints.users import router as users_router
    from backend.endpoints.admin_users import router as admin_users_router
    from backend.endpoints.realtime import router as realtime_router
    from backend.endpoints.tables import router as tables_router
    from backend.endpoints.sql import router as sql_router
    from backend.endpoints.buckets import router as buckets_router
    from backend.endpoints.functions import router as functions_router
    from backend.endpoints.webhooks import router as webhooks_router
    from backend.endpoints.cors import router as cors_router
    from backend.middleware.auth import CombinedAuthMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle events."""
    global pg_listener
    
    # Startup
    try:
        from shared.database.connection_manager import DatabaseConnectionManager
        from shared.config.config_manager import ConfigManager
        from shared.database.pg_notify_listener import PgNotifyListener

        # Initialize database connection and schema
        config = ConfigManager()
        db_manager = DatabaseConnectionManager(config)
        await db_manager.initialize_schema()

        logger.info("Database schema initialized successfully")
        
        # Start PG NOTIFY listener (only if Phoenix service is enabled)
        pg_listener = None
        if os.getenv('PHOENIX_ENABLED', 'false').lower() == 'true':
            try:
                pg_listener = PgNotifyListener(
                    direct_connection_string=config.get_direct_postgres_url(),
                    phoenix_url=os.getenv('REALTIME_INTERNAL_URL', 'http://realtime:4000'),
                    internal_api_key=os.getenv('INTERNAL_API_KEY')
                )
                
                channels = [
                    'users_events',
                    'files_events',
                    'buckets_events',
                    'functions_events',
                    'tables_events',
                    'webhooks_events',
                    'webhook_deliveries_events'
                ]
                
                await pg_listener.start(channels)
                logger.info("PG NOTIFY listener started successfully")
                
            except Exception as e:
                logger.error(f"Failed to start PG NOTIFY listener: {e}")
                pg_listener = None
        else:
            logger.info("Phoenix realtime service disabled (PHOENIX_ENABLED=false)")
            
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")

    yield

    # Shutdown
    if pg_listener:
        try:
            await pg_listener.stop()
            logger.info("PG NOTIFY listener stopped")
        except Exception as e:
            logger.error(f"Error stopping PG NOTIFY listener: {e}")

# Create FastAPI app with lifespan handler
# Configure OpenAPI tags to control documentation order
openapi_tags = [
    {"name": "authentication", "description": "User authentication endpoints (login, register, token management)"},
    {"name": "user-management", "description": "User management endpoints (admin-only user CRUD operations)"},
    {"name": "tables", "description": "Dynamic table management endpoints"},
    {"name": "realtime", "description": "Realtime WebSocket connections and subscriptions"},
    {"name": "buckets", "description": "Storage bucket management endpoints"},
    {"name": "files", "description": "File upload, download, and management endpoints"},
    {"name": "sql", "description": "SQL execution and snippet management endpoints"},
    {"name": "functions", "description": "Serverless function CRUD and execution endpoints"},
    {"name": "webhooks", "description": "Webhook management and delivery endpoints"},
    {"name": "cors", "description": "CORS origin management endpoints (admin-only)"},
]

app = FastAPI(
    title="SelfDB Backend", 
    version=os.getenv("SELFDB_VERSION"), 
    lifespan=lifespan,
    openapi_tags=openapi_tags
)

# Add authentication middleware
app.add_middleware(CombinedAuthMiddleware)

# Include routers in the desired documentation order
# Order: authentication, user-management, tables, realtime, buckets, files, sql, functions, webhooks, cors
app.include_router(users_router)
app.include_router(admin_users_router)
app.include_router(tables_router)
app.include_router(realtime_router)
app.include_router(buckets_router)
app.include_router(files_router)
app.include_router(sql_router)
app.include_router(functions_router)
app.include_router(webhooks_router)
app.include_router(cors_router)

# Configure CORS
allowed_origins = os.getenv("ALLOWED_CORS")
if allowed_origins:
    allowed_origins = allowed_origins.split(",")
else:
    # If ALLOWED_CORS is not set, use a default for testing
    allowed_origins = ["*"]
    
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    websocket_path = "/api/v1/realtime/ws"
    websocket_doc = {
        "get": {
            "tags": ["realtime"],
            "summary": "Realtime WebSocket Proxy",
            "description": "Establish a WebSocket connection proxied to the Phoenix Realtime service.",
            "parameters": [
                {
                    "name": "token",
                    "in": "query",
                    "required": True,
                    "description": "JWT token authorizing the realtime session.",
                    "schema": {"type": "string"},
                }
            ],
            "responses": {
                "101": {"description": "Switching Protocols"},
                "400": {"description": "Invalid WebSocket handshake"},
                "403": {"description": "Authentication required"},
                "500": {"description": "Internal server error"},
            },
        }
    }

    if websocket_path in openapi_schema["paths"]:
        openapi_schema["paths"][websocket_path].update(websocket_doc)
    else:
        openapi_schema["paths"][websocket_path] = websocket_doc

    paths = openapi_schema["paths"]
    websocket_entry = paths.pop(websocket_path, None)

    if websocket_entry:
        reordered_paths = {}
        inserted = False

        for path, doc in paths.items():
            reordered_paths[path] = doc

            if path == "/api/v1/realtime/status":
                reordered_paths[websocket_path] = websocket_entry
                inserted = True

        if not inserted:
            reordered_paths[websocket_path] = websocket_entry

        openapi_schema["paths"] = reordered_paths

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

class HealthResponse(BaseModel):
    service: str
    status: str
    version: str
    environment: Dict[str, Any]
    database: Dict[str, str]
    message: str

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "SelfDB Backend API", "status": "ready"}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint showing service configuration"""
    return HealthResponse(
        service="backend",
        status="ready",
        version= os.getenv("SELFDB_VERSION"),
        environment={
            "env": os.getenv("ENV"),
            "debug": os.getenv("DEBUG"),
            "api_port": int(os.getenv("API_PORT")),
            "api_key_configured": bool(os.getenv("API_KEY")),
            "admin_email": os.getenv("ADMIN_EMAIL"),
        },
        database={
            "host": "postgres",
            "port": os.getenv("POSTGRES_PORT"),
            "database": os.getenv("POSTGRES_DB"),
            "user": os.getenv("POSTGRES_USER"),
        },
        message="Backend service is ready and configured"
    )

@app.get("/api/v1/status")
async def api_status():
    """API v1 status endpoint"""
    return {
        "api_version": os.getenv("SELFDB_VERSION"),
        "services": {
            "backend": "ready",
            "storage_url": f"http://storage:{os.getenv('STORAGE_PORT')}",
            "functions_url": f"http://deno-runtime:{os.getenv('DENO_PORT')}",
        },
        "ports": {
            "api": int(os.getenv("API_PORT")),
            "storage": int(os.getenv("STORAGE_PORT")),
            "functions": int(os.getenv("DENO_PORT")),
            "postgres": int(os.getenv("POSTGRES_PORT")),
            "frontend": int(os.getenv("FRONTEND_PORT")),
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT"))
    uvicorn.run(app, host="0.0.0.0", port=port)