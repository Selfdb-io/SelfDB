from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
from fastapi.openapi.utils import get_openapi

# Import API routers
from .apis.endpoints import health, auth, users, files, realtime, tables, sql, schema, buckets
from .apis.endpoints.functions import router as functions_router
from .core.config import settings
from .db.session import engine
from sqlalchemy.ext.asyncio import AsyncSession
from .db.base import Base
from .core.middleware import AnonKeyEnforcerMiddleware
from .db.notify import create_trigger_for_all_tables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Set DEBUG level specifically for critical modules
logging.getLogger("app.apis.deps_storage").setLevel(logging.DEBUG)
logging.getLogger("app.apis.endpoints.files").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.INFO)  # Set httpx to INFO to see request/response details

# Create FastAPI app instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Define custom OpenAPI schema to adjust security requirements
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="SelfDB API with customized security documentation",
        routes=app.routes,
    )

    # Define security schemes
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}
    
    # Define the APIKey security scheme
    openapi_schema["components"]["securitySchemes"]["APIKeyHeader"] = {
        "type": "apiKey",
        "in": "header",
        "name": "apikey",
        "description": "API Key authentication for anonymous access"
    }
    
    # Define the OAuth2 security scheme (already defined by FastAPI)
    if "OAuth2PasswordBearer" not in openapi_schema["components"]["securitySchemes"]:
        openapi_schema["components"]["securitySchemes"]["OAuth2PasswordBearer"] = {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": f"{settings.API_V1_STR}/auth/login",
                    "scopes": {}
                }
            }
        }

    # Customize security for specific paths
    for path, path_item in openapi_schema["paths"].items():
        # Skip documentation paths
        if path in [f"{settings.API_V1_STR}/docs", f"{settings.API_V1_STR}/redoc", f"{settings.API_V1_STR}/openapi.json"]:
            continue
            
        # Auth endpoints should require only API key
        if path.startswith(f"{settings.API_V1_STR}/auth"):
            for method in path_item:
                path_item[method]["security"] = [{"APIKeyHeader": []}]
        else:
            # Other endpoints should require both OAuth2 and API key
            for method in path_item:
                # To express AND relationship, both schemes must be in the same object
                path_item[method]["security"] = [
                    {"OAuth2PasswordBearer": [], "APIKeyHeader": []}
                ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Assign the custom OpenAPI function
app.openapi = custom_openapi

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://frontend:3000",
    "https://100.83.47.61:3000",  # Docker service name
    # Add your production frontend URL here
]

# Make sure to add CORS middleware before any routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for debugging
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Authorization"],
    max_age=86400,  # Cache preflight requests for 24 hours
)

app.add_middleware(AnonKeyEnforcerMiddleware)

# Include API routers
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["Health"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
app.include_router(files.router, prefix=f"{settings.API_V1_STR}/files", tags=["Files"])
app.include_router(buckets.router, prefix=f"{settings.API_V1_STR}/buckets", tags=["Buckets"])
app.include_router(realtime.router, prefix=f"{settings.API_V1_STR}/realtime", tags=["Realtime"])
app.include_router(tables.router, prefix=f"{settings.API_V1_STR}/tables", tags=["Tables"])
app.include_router(sql.router, prefix=f"{settings.API_V1_STR}/sql", tags=["SQL"])
app.include_router(schema.router, prefix=f"{settings.API_V1_STR}/schema", tags=["Schema"])
app.include_router(functions_router, prefix=f"{settings.API_V1_STR}/functions", tags=["Functions"])

# Root endpoint
@app.get("/", tags=["Root"])
async def read_root():
    """
    Simple root endpoint to confirm the API is running.
    """
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Initialize services on startup.
    """
    logger.info("Starting up SelfDB API...")
    
    # Debug configuration loading
    logger.info(f"ANON_KEY loaded: {'***' + settings.ANON_KEY[-5:] if settings.ANON_KEY and len(settings.ANON_KEY) > 5 else 'NOT SET'}")
    logger.info(f"STORAGE_SERVICE_EXTERNAL_URL: {settings.STORAGE_SERVICE_EXTERNAL_URL}")

    # Create database tables
    async def init_db():
        # Create tables in a transaction that auto-commits
        async with engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)  # Uncomment to reset DB
            await conn.run_sync(Base.metadata.create_all)
        
        # Create triggers with proper session management
        async with AsyncSession(engine) as session:
            try:
                await create_trigger_for_all_tables(session)
                # Explicitly commit any pending changes
                await session.commit()
            except Exception as e:
                # Make sure to rollback in case of error
                await session.rollback()
                logger.error(f"Error during trigger creation: {e}")
                raise

    await init_db()
    logger.info("Database tables created and triggers set up")

    # Initialize Storage Service client
    try:
        # No need to initialize the client here as it's created on-demand via dependency injection
        logger.info("Storage Service client will be initialized on-demand")
        logger.info("IMPORTANT: All buckets must be created through the admin dashboard")
        logger.info("No default buckets are created automatically")

    except Exception as e:
        logger.error(f"Error during startup: {e}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean up resources on shutdown.
    """
    logger.info("Shutting down SelfDB API...")
