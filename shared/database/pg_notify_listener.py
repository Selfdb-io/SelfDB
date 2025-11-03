"""
PostgreSQL LISTEN/NOTIFY listener for SelfDB realtime system.

Listens to database events and forwards them to Phoenix realtime service.
"""
import asyncio
import asyncpg
import httpx
import logging
from typing import List, Optional, Callable, Any

logger = logging.getLogger(__name__)


class PgNotifyListener:
    """
    PostgreSQL LISTEN/NOTIFY listener that forwards notifications to Phoenix.
    
    This listener maintains a direct connection to PostgreSQL (bypassing PgBouncer)
    to receive NOTIFY events from database triggers and forward them to the
    Phoenix realtime service via HTTP API.
    """
    
    def __init__(
        self, 
        direct_connection_string: str,
        phoenix_url: str = "http://realtime:4000",
        internal_api_key: Optional[str] = None
    ):
        """
        Initialize PG NOTIFY listener.
        
        Args:
            direct_connection_string: Direct PostgreSQL connection (bypass PgBouncer)
            phoenix_url: Phoenix realtime service URL
            internal_api_key: API key for internal service communication
        """
        self.connection_string = direct_connection_string
        self.phoenix_url = phoenix_url
        self.internal_api_key = internal_api_key
        self._conn: Optional[asyncpg.Connection] = None
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None
        
    async def start(self, channels: List[str]) -> None:
        """
        Start listening on specified channels.
        
        Args:
            channels: List of channel names to listen on (e.g., ['users_events', 'files_events'])
        """
        if self._running:
            logger.warning("PG NOTIFY listener already running")
            return
            
        self._running = True
        
        try:
            # Establish direct connection to PostgreSQL
            self._conn = await asyncpg.connect(self.connection_string)
            logger.info(f"PG NOTIFY listener connected to PostgreSQL")
            
            # Register listeners for each channel
            for channel in channels:
                await self._conn.add_listener(channel, self._on_notification)
                logger.info(f"Listening on channel: {channel}")
            
            logger.info(f"PG NOTIFY Listener started on channels: {channels}")
            
            # Start keep-alive loop
            self._listener_task = asyncio.create_task(self._keep_alive_loop())
            
        except Exception as e:
            logger.error(f"Failed to start PG NOTIFY listener: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self._running = False
            raise
    
    async def _keep_alive_loop(self) -> None:
        """Keep-alive loop to maintain connection and handle notifications."""
        while self._running:
            try:
                # Health check query
                await self._conn.fetchval('SELECT 1')
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"PG NOTIFY listener health check failed: {e}")
                if self._running:
                    logger.info("Attempting to reconnect...")
                    await self._reconnect()
                break
    
    async def _reconnect(self) -> None:
        """Reconnect to PostgreSQL after connection loss."""
        try:
            if self._conn:
                await self._conn.close()
            
            self._conn = await asyncpg.connect(self.connection_string)
            logger.info("PG NOTIFY listener reconnected successfully")
            
        except Exception as e:
            logger.error(f"Failed to reconnect PG NOTIFY listener: {e}")
            # Schedule retry
            asyncio.create_task(self._delayed_reconnect())
    
    async def _delayed_reconnect(self) -> None:
        """Delayed reconnection attempt."""
        await asyncio.sleep(5)  # Wait 5 seconds before retry
        if self._running:
            await self._reconnect()
    
    async def _on_notification(self, conn, pid, channel, payload) -> None:
        """
        Handle incoming notification and forward to Phoenix.
        
        Args:
            conn: Database connection
            pid: Process ID that sent the notification
            channel: Channel name
            payload: Notification payload
        """
        try:
            logger.debug(f"Received notification on {channel}: {payload}")
            
            # Forward to Phoenix broadcast API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.phoenix_url}/api/broadcast",
                    json={"channel": channel, "payload": payload},
                    headers={"X-Internal-API-Key": self.internal_api_key or ""},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    logger.debug(f"Successfully forwarded {channel} notification to Phoenix")
                else:
                    logger.warning(f"Phoenix broadcast failed: {response.status_code} - {response.text}")
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout forwarding notification to Phoenix: {channel}")
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Phoenix service: {self.phoenix_url}")
        except Exception as e:
            logger.error(f"Failed to forward notification {channel}: {e}")
    
    async def stop(self) -> None:
        """Stop listener and close connection."""
        logger.info("Stopping PG NOTIFY listener...")
        self._running = False
        
        # Cancel keep-alive task
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        # Close database connection
        if self._conn:
            try:
                await self._conn.close()
                logger.info("PG NOTIFY listener connection closed")
            except Exception as e:
                logger.error(f"Error closing PG NOTIFY listener connection: {e}")
        
        self._conn = None
        logger.info("PG NOTIFY listener stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running and self._conn is not None
    
    @property
    def is_connected(self) -> bool:
        """Check if listener is connected to database."""
        return self._conn is not None and not self._conn.is_closed()
