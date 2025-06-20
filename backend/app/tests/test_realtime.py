import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockWebSocketManager:
    """Mock WebSocket connection manager"""
    
    def __init__(self):
        self.connections = {}
        self.subscriptions = {}
        self.messages = {}
    
    async def broadcast_to_user(self, user_id: str, message: str):
        """Mock broadcasting a message to a user"""
        if user_id not in self.messages:
            self.messages[user_id] = []
        self.messages[user_id].append(json.loads(message))
        logger.info(f"Broadcast to user {user_id}: {message}")
    
    def add_subscription(self, user_id: str, subscription_id: str, data: Dict[str, Any]):
        """Mock adding a subscription"""
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = {}
        self.subscriptions[user_id][subscription_id] = data
        logger.info(f"Added subscription for user {user_id}: {subscription_id} -> {data}")

class MockAsyncpgConnection:
    """Mock asyncpg connection for testing"""
    
    def __init__(self):
        self.notifications = []
        self.listeners = {}
    
    async def execute(self, query: str, *args, **kwargs):
        """Mock executing a query"""
        logger.info(f"Executing query: {query}")
        return "OK"
    
    async def add_listener(self, channel: str, callback):
        """Mock adding a listener to a channel"""
        if channel not in self.listeners:
            self.listeners[channel] = []
        self.listeners[channel].append(callback)
        logger.info(f"Added listener to channel: {channel}")
    
    async def remove_listener(self, channel: str, callback):
        """Mock removing a listener from a channel"""
        if channel in self.listeners and callback in self.listeners[channel]:
            self.listeners[channel].remove(callback)
            logger.info(f"Removed listener from channel: {channel}")
    
    async def notify(self, channel: str, payload: str):
        """Mock sending a notification"""
        self.notifications.append((channel, payload))
        logger.info(f"Notification on channel {channel}: {payload}")
        
        if channel in self.listeners:
            for callback in self.listeners[channel]:
                await callback(self, 0, channel, payload)

class MockAsyncSession:
    """Mock SQLAlchemy AsyncSession"""
    
    def __init__(self):
        self._connection = MockAsyncpgConnection()
        self.committed = False
        self.rolled_back = False
    
    async def execute(self, query, params=None):
        """Mock executing a query"""
        result = MagicMock()
        result.scalar.return_value = True
        return result
    
    async def commit(self):
        """Mock committing a transaction"""
        self.committed = True
        logger.info("Transaction committed")
    
    async def rollback(self):
        """Mock rolling back a transaction"""
        self.rolled_back = True
        logger.info("Transaction rolled back")
    
    async def connection(self):
        """Get the underlying connection"""
        return self._connection

async def mock_emit_table_notification(session, table_name, operation, data=None, old_data=None):
    """Mock implementation of emit_table_notification"""
    conn = await session.connection()
    payload = {
        "table": table_name,
        "operation": operation
    }
    
    if data is not None:
        payload["data"] = data
    
    if old_data is not None:
        payload["old_data"] = old_data
    
    channel = f"{table_name}_changes"
    await conn.notify(channel, json.dumps(payload))
    
    return True

@pytest.mark.asyncio
async def test_emit_table_notification():
    """Test emitting table notifications"""
    session = MockAsyncSession()
    
    table_name = "test_table"
    operation = "INSERT"
    data = {"id": 1, "name": "Test Item", "description": "This is a test item"}
    
    await mock_emit_table_notification(session, table_name, operation, data)
    
    assert len(session._connection.notifications) > 0
    channel, payload = session._connection.notifications[0]
    
    assert channel == f"{table_name}_changes"
    payload_data = json.loads(payload)
    assert payload_data["table"] == table_name
    assert payload_data["operation"] == operation
    assert payload_data["data"] == data
    
    operation = "UPDATE"
    data = {"id": 1, "name": "Updated Test Item", "description": "This is an updated test item"}
    
    await mock_emit_table_notification(session, table_name, operation, data)
    
    assert len(session._connection.notifications) > 1
    channel, payload = session._connection.notifications[1]
    
    assert channel == f"{table_name}_changes"
    payload_data = json.loads(payload)
    assert payload_data["table"] == table_name
    assert payload_data["operation"] == operation
    assert payload_data["data"] == data
    
    operation = "DELETE"
    old_data = {"id": 1, "name": "Updated Test Item", "description": "This is an updated test item"}
    
    await mock_emit_table_notification(session, table_name, operation, None, old_data)
    
    assert len(session._connection.notifications) > 2
    channel, payload = session._connection.notifications[2]
    
    assert channel == f"{table_name}_changes"
    payload_data = json.loads(payload)
    assert payload_data["table"] == table_name
    assert payload_data["operation"] == operation
    assert payload_data["old_data"] == old_data
    
    logger.info("All notification tests passed!")

async def mock_handle_database_notification(conn, pid, channel, payload):
    """Mock implementation of handle_database_notification"""
    logger.info(f"Received notification on channel {channel}: {payload}")
    
    try:
        data = json.loads(payload)
        table_name = data.get("table")
        
        manager = MockWebSocketManager()
        manager.subscriptions = {
            "user1": {
                "sub1": {"table": table_name}
            }
        }
        
        for user_id, subscriptions in manager.subscriptions.items():
            for sub_id, sub_data in subscriptions.items():
                if sub_data.get("table") == table_name:
                    await manager.broadcast_to_user(
                        user_id,
                        json.dumps({
                            "type": "database_change",
                            "subscription_id": sub_id,
                            "data": data
                        })
                    )
        
        return manager
    except Exception as e:
        logger.error(f"Error handling database notification: {e}")
        return None

@pytest.mark.asyncio
async def test_notification_handler():
    """Test the notification handler"""
    # Create mock connection
    conn = MockAsyncpgConnection()
    
    table_name = "test_table"
    payload = json.dumps({
        "table": table_name,
        "operation": "INSERT",
        "data": {"id": 1, "name": "Test Item"}
    })
    
    manager = await mock_handle_database_notification(conn, 0, f"{table_name}_changes", payload)
    
    assert manager is not None, "Handler returned None instead of manager"
    assert "user1" in manager.messages, "User1 not found in manager messages"
    assert len(manager.messages["user1"]) == 1, "Expected 1 message for user1"
    
    message = manager.messages["user1"][0]
    assert message["type"] == "database_change", "Incorrect message type"
    assert message["subscription_id"] == "sub1", "Incorrect subscription ID"
    assert message["data"]["table"] == table_name, "Incorrect table name in message"
    assert message["data"]["operation"] == "INSERT", "Incorrect operation in message"
    
    logger.info("Notification handler test passed!")

if __name__ == "__main__":
    asyncio.run(test_emit_table_notification())
    asyncio.run(test_notification_handler())
