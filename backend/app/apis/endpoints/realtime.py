from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Any
import json
import asyncio
import logging
import asyncpg
from jose import jwt, JWTError
from sqlalchemy import text

from ...core.config import settings
from ...schemas.token import TokenPayload
from ...crud.user import get_user_by_email
from ..deps import get_db
from ...db.session import engine

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

db_listeners = {}

async def setup_database_listener(channel: str):
    """
    Setup a database notification listener for a specific channel.
    """
    logger.info(f"Setting up database listener for channel: {channel}")

    # Convert SQLAlchemy URL format to standard PostgreSQL URL format that asyncpg can accept
    db_url = str(settings.DATABASE_URL).replace('postgresql+asyncpg://', 'postgresql://')

    try:
        conn = await asyncpg.connect(db_url)
        await conn.add_listener(channel, handle_database_notification)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise

async def handle_database_notification(conn, pid, channel, payload):
    """
    Handle database notifications and forward them to WebSocket clients.
    """
    logger.info(f"Received notification on channel {channel}: {payload}")

    try:
        data = json.loads(payload)
        table_name = data.get("table")

        # Special handling for specific channels that need broader notification
        special_channels = {
            "buckets_changes": "buckets",
            "functions_changes": "functions",
            "tables_changes": None  # Tables is a special case handled separately
        }

        for user_id, subscriptions in manager.subscriptions.items():
            for sub_id, sub_data in subscriptions.items():
                # Different matching strategies
                should_notify = False
                
                # 1. Direct table match: subscription table matches notification table
                if sub_data.get("table") == table_name:
                    should_notify = True
                
                # 2. Channel match: subscription ID matches notification channel
                elif sub_id == channel:
                    should_notify = True
                
                # 3. Special case for tables_changes: notify on any table operation
                elif sub_id == "tables_changes":
                    should_notify = True
                
                # 4. Special case for buckets and functions: match by channel name
                elif sub_id in special_channels and channel == sub_id:
                    should_notify = True

                # If any match condition is met, send the notification
                if should_notify:
                    await manager.broadcast_to_user(
                        user_id,
                        json.dumps({
                            "type": "database_change",
                            "subscription_id": sub_id,
                            "data": data
                        })
                    )
    except Exception as e:
        logger.error(f"Error handling database notification: {e}")

# Store active connections
class ConnectionManager:
    def __init__(self):
        # Maps user_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Maps WebSocket -> user_id
        self.connection_user: Dict[WebSocket, str] = {}
        # Maps user_id -> Dict[subscription_id -> subscription_data]
        self.subscriptions: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        # WebSocket is already accepted in the endpoint function
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        self.connection_user[websocket] = user_id
        logger.info(f"User {user_id} connected. Total connections: {len(self.connection_user)}")

    def disconnect(self, websocket: WebSocket):
        user_id = self.connection_user.get(websocket)
        if user_id:
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            del self.connection_user[websocket]
            logger.info(f"User {user_id} disconnected. Total connections: {len(self.connection_user)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.send_text(message)

    async def broadcast_to_user(self, user_id: str, message: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_text(message)

    def add_subscription(self, user_id: str, subscription_id: str, subscription_data: Any):
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = {}
        self.subscriptions[user_id][subscription_id] = subscription_data
        logger.info(f"User {user_id} subscribed to {subscription_id}")

    def remove_subscription(self, user_id: str, subscription_id: str):
        if user_id in self.subscriptions and subscription_id in self.subscriptions[user_id]:
            del self.subscriptions[user_id][subscription_id]
            logger.info(f"User {user_id} unsubscribed from {subscription_id}")
            if not self.subscriptions[user_id]:
                del self.subscriptions[user_id]

manager = ConnectionManager()

@router.on_event("startup")
async def startup_event():
    """
    Initialize database listeners on startup.
    """
    try:
        async with AsyncSession(engine) as session:
            query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE';
            """
            result = await session.execute(text(query))
            tables = [row.table_name for row in result.fetchall()]

            for table_name in tables:
                channel = f"{table_name}_changes"
                if channel not in db_listeners:
                    db_listeners[channel] = await setup_database_listener(channel)

    except Exception as e:
        logger.error(f"Error setting up database listeners: {e}")

@router.on_event("shutdown")
async def shutdown_event():
    """
    Clean up database listeners on shutdown.
    """
    for channel, conn in db_listeners.items():
        try:
            await conn.close()
            logger.info(f"Closed database listener for channel {channel}")
        except Exception as e:
            logger.error(f"Error closing database listener connection for channel {channel}: {e}")

async def get_user_from_token(token: str, db: AsyncSession) -> str:
    """
    Validate token and return user_id.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            return None
        token_data = TokenPayload(sub=email)
    except JWTError:
        return None

    user = await get_user_by_email(db, email=token_data.sub)
    if not user or not user.is_active:
        return None

    return str(user.id)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    """
    WebSocket endpoint for real-time updates.
    """
    await websocket.accept()

    try:
        # Wait for authentication message
        auth_message = await websocket.receive_text()
        auth_data = json.loads(auth_message)

        if auth_data.get("type") != "authenticate" or "token" not in auth_data:
            await websocket.send_text(json.dumps({"error": "Authentication required"}))
            await websocket.close()
            return

        # Validate token
        user_id = await get_user_from_token(auth_data["token"], db)
        if not user_id:
            await websocket.send_text(json.dumps({"error": "Invalid authentication"}))
            await websocket.close()
            return

        # Connect user
        await manager.connect(websocket, user_id)

        # Send confirmation
        await manager.send_personal_message(
            json.dumps({"type": "connected", "user_id": user_id}),
            websocket
        )

        # Handle messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle subscription
            if message.get("type") == "subscribe":
                subscription_id = message.get("subscription_id")
                subscription_data = message.get("data", {})

                if subscription_id:
                    # Add subscription
                    manager.add_subscription(user_id, subscription_id, subscription_data)

                    # Set up database listener if it's a table subscription
                    if "table" in subscription_data:
                        table_name = subscription_data["table"]
                        channel = f"{table_name}_changes"
                        if channel not in db_listeners:
                            try:
                                db_listeners[channel] = await setup_database_listener(channel)
                                logger.info(f"Set up new database listener for table {table_name}")
                            except Exception as e:
                                logger.error(f"Error setting up listener for table {table_name}: {e}")

                    await manager.send_personal_message(
                        json.dumps({
                            "type": "subscribed",
                            "subscription_id": subscription_id
                        }),
                        websocket
                    )

            # Handle unsubscription
            elif message.get("type") == "unsubscribe":
                subscription_id = message.get("subscription_id")

                if subscription_id:
                    manager.remove_subscription(user_id, subscription_id)
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "unsubscribed",
                            "subscription_id": subscription_id
                        }),
                        websocket
                    )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)

# Background task to simulate notifications (for testing)
@router.websocket("/ws/test")
async def test_websocket(websocket: WebSocket):
    """
    Test WebSocket endpoint that sends periodic messages.
    """
    await websocket.accept()

    try:
        # Send a welcome message
        await websocket.send_text(json.dumps({"message": "Connected to test WebSocket"}))

        # Send periodic messages
        counter = 0
        while True:
            await asyncio.sleep(5)
            counter += 1
            await websocket.send_text(json.dumps({
                "type": "test",
                "message": f"Test message {counter}",
                "timestamp": str(asyncio.get_event_loop().time())
            }))

    except WebSocketDisconnect:
        logger.info("Test WebSocket disconnected")
    except Exception as e:
        logger.error(f"Test WebSocket error: {str(e)}")
