"""
WebSocket proxy to Phoenix Realtime Service.

Phase 3: Proper Phoenix Channel Protocol Implementation
"""
import os
import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, HTTPException
from typing import Dict, Any
from urllib.parse import urlencode
import websockets

logger = logging.getLogger(__name__)
# Increase verbosity for realtime proxy during debugging
if not logger.handlers:
    logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/api/v1/realtime", tags=["realtime"])

# Configuration for the Phoenix Realtime Service
PHOENIX_REALTIME_URL = os.getenv("REALTIME_INTERNAL_URL", "http://realtime:4000")

# Message reference counter for Phoenix protocol
class MessageRefCounter:
    def __init__(self):
        self.counter = 0
    
    def next_ref(self) -> str:
        self.counter += 1
        return str(self.counter)

# Client subscription tracking
class ClientSubscription:
    def __init__(self):
        self.subscriptions = {}  # topic -> {join_ref, msg_ref, status}
        self.ref_counter = MessageRefCounter()
    
    def add_subscription(self, topic: str, join_ref: str, msg_ref: str):
        self.subscriptions[topic] = {
            "join_ref": join_ref,
            "msg_ref": msg_ref,
            "status": "joining"
        }
    
    def update_subscription_status(self, msg_ref: str, status: str):
        for topic, sub in self.subscriptions.items():
            if sub["msg_ref"] == msg_ref:
                sub["status"] = status
                break
    
    def get_subscription_by_ref(self, msg_ref: str):
        for topic, sub in self.subscriptions.items():
            if sub["msg_ref"] == msg_ref:
                return topic, sub
        return None, None

def map_subscription_to_topic(subscription_data: Dict[str, Any]) -> str:
    """Map frontend subscription to Phoenix topic."""
    resource_type = subscription_data.get("resource_type", "")
    resource_id = subscription_data.get("resource_id")
    
    # Map resource types to Phoenix topics
    topic_mapping = {
        "users": "users_events",
        "tables": "tables_events", 
        "buckets": "buckets_events",
        "functions": "functions_events",
        "webhooks": "webhooks_events"
    }
    
    base_topic = topic_mapping.get(resource_type, f"{resource_type}_events")
    
    if resource_id:
        return f"{base_topic}:{resource_id}"
    else:
        return base_topic


@router.get("/status")
async def realtime_status():
    """Health check endpoint."""
    return {
        "service": "realtime",
        "status": "ready",
        "phoenix_enabled": os.getenv('PHOENIX_ENABLED', 'false'),
        "phoenix_url": PHOENIX_REALTIME_URL
    }

@router.websocket("/ws")
async def websocket_proxy_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint that proxies connections to the Phoenix Realtime Service.
    
    Phase 3: Proper Phoenix Channel Protocol Implementation
    """
    logger.info("WebSocket proxy endpoint called")
    
    if not PHOENIX_REALTIME_URL:
        logger.error("PHOENIX_REALTIME_URL is not configured.")
        raise HTTPException(status_code=500, detail="Realtime service not configured.")

    # Extract JWT token from query parameters
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("WebSocket connection attempted without JWT token.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return

    phoenix_ws_url = PHOENIX_REALTIME_URL.replace("http", "ws") + "/socket/websocket"

    # Forward all client query params and ensure Phoenix vsn is present
    params = dict(websocket.query_params)
    params.setdefault("vsn", "2.0.0")
    phoenix_ws_url_with_token = f"{phoenix_ws_url}?{urlencode(params)}"

    try:
        await websocket.accept()
        logger.info(f"Accepted WebSocket connection from client. Proxying to Phoenix")
        logger.info(f"Phoenix WebSocket URL: {phoenix_ws_url_with_token}")

        # Connect to Phoenix WebSocket using websockets library
        logger.info("Attempting to connect to Phoenix WebSocket...")
        async with websockets.connect(phoenix_ws_url_with_token) as phoenix_client:
            logger.info("Connected to Phoenix WebSocket.")

            # Initialize client subscription tracking
            client_sub = ClientSubscription()

            # Create tasks for bidirectional message forwarding
            async def forward_client_to_phoenix():
                """Forward messages from client to Phoenix with proper channel protocol."""
                try:
                    while True:
                        try:
                            incoming = await websocket.receive()
                            if incoming.get("text") is not None:
                                message = incoming["text"]
                                logger.debug(f"Client -> Phoenix TEXT: {message}")
                                
                                # Try to parse as JSON to detect subscription messages
                                try:
                                    data = json.loads(message)
                                    
                                    # Handle frontend subscription messages
                                    if isinstance(data, dict) and data.get("type") == "subscribe":
                                        logger.info(f"Client subscription request: {data}")
                                        
                                        # Map to Phoenix topic
                                        topic = map_subscription_to_topic(data)
                                        
                                        # Generate Phoenix join frame
                                        join_ref = client_sub.ref_counter.next_ref()
                                        msg_ref = client_sub.ref_counter.next_ref()
                                        
                                        # Phoenix join frame: [join_ref, msg_ref, topic, "phx_join", payload]
                                        phoenix_frame = [join_ref, msg_ref, topic, "phx_join", {}]
                                        phoenix_message = json.dumps(phoenix_frame)
                                        
                                        # Track subscription
                                        client_sub.add_subscription(topic, join_ref, msg_ref)
                                        
                                        logger.info(f"Sending Phoenix join frame: {phoenix_message}")
                                        await phoenix_client.send(phoenix_message)
                                        
                                        # Send confirmation to client
                                        confirmation = {
                                            "type": "subscribed",
                                            "resource_type": data.get("resource_type"),
                                            "resource_id": data.get("resource_id"),
                                            "topic": topic,
                                            "status": "joining"
                                        }
                                        await websocket.send_text(json.dumps(confirmation))
                                        
                                    elif isinstance(data, dict) and data.get("type") == "unsubscribe":
                                        logger.info(f"Client unsubscribe request: {data}")
                                        
                                        # Map to Phoenix topic
                                        topic = map_subscription_to_topic(data)
                                        
                                        # Generate Phoenix leave frame
                                        join_ref = client_sub.ref_counter.next_ref()
                                        msg_ref = client_sub.ref_counter.next_ref()
                                        
                                        # Phoenix leave frame: [join_ref, msg_ref, topic, "phx_leave", payload]
                                        phoenix_frame = [join_ref, msg_ref, topic, "phx_leave", {}]
                                        phoenix_message = json.dumps(phoenix_frame)
                                        
                                        logger.info(f"Sending Phoenix leave frame: {phoenix_message}")
                                        await phoenix_client.send(phoenix_message)
                                        
                                        # Remove from tracking
                                        if topic in client_sub.subscriptions:
                                            del client_sub.subscriptions[topic]
                                        
                                        # Send confirmation to client
                                        confirmation = {
                                            "type": "unsubscribed",
                                            "resource_type": data.get("resource_type"),
                                            "resource_id": data.get("resource_id"),
                                            "topic": topic
                                        }
                                        await websocket.send_text(json.dumps(confirmation))
                                        
                                    else:
                                        # Forward other messages as-is (could be Phoenix frames)
                                        await phoenix_client.send(message)
                                        
                                except json.JSONDecodeError:
                                    # Not JSON, forward as-is (could be Phoenix frames)
                                    await phoenix_client.send(message)
                                    
                            elif incoming.get("bytes") is not None:
                                b = incoming["bytes"]
                                logger.debug(f"Client -> Phoenix BYTES: {len(b)} bytes")
                                await phoenix_client.send(b)
                            else:
                                logger.debug("Client -> Phoenix: control/empty frame")
                                
                        except WebSocketDisconnect:
                            logger.info("Client disconnected.")
                            break
                        except Exception as e:
                            logger.error(f"Error forwarding client message: {e}")
                            break
                except Exception as e:
                    logger.error(f"Client forwarding task error: {e}")

            async def forward_phoenix_to_client():
                """Forward messages from Phoenix to client with proper formatting."""
                try:
                    while True:
                        try:
                            message = await phoenix_client.recv()
                            if isinstance(message, (bytes, bytearray)):
                                logger.debug(f"Phoenix -> Client BYTES: {len(message)} bytes")
                                await websocket.send_bytes(message)
                            else:
                                text = str(message)
                                logger.debug(f"Phoenix -> Client TEXT: {text}")
                                
                                # Try to parse as Phoenix frame
                                try:
                                    frame = json.loads(text)
                                    if isinstance(frame, list) and len(frame) >= 5:
                                        # Phoenix frame: [join_ref, ref, topic, event, payload]
                                        join_ref, ref, topic, event, payload = frame[:5]
                                        
                                        if event == "phx_reply":
                                            # Handle Phoenix reply
                                            logger.info(f"Phoenix phx_reply for ref {ref}: {payload}")
                                            
                                            # Update subscription status
                                            status = payload.get("status", "error")
                                            client_sub.update_subscription_status(ref, status)
                                            
                                            # Send status update to client
                                            topic_sub, sub_info = client_sub.get_subscription_by_ref(ref)
                                            if topic_sub:
                                                status_update = {
                                                    "type": "subscription_status",
                                                    "topic": topic_sub,
                                                    "status": status,
                                                    "response": payload
                                                }
                                                await websocket.send_text(json.dumps(status_update))
                                        
                                        elif event in ["broadcast", "event"]:
                                            # Handle broadcasts/events
                                            logger.info(f"Phoenix broadcast on {topic}: {event}")
                                            
                                            # Forward as client-friendly message
                                            client_message = {
                                                "type": "broadcast",
                                                "channel": topic,
                                                "event": event,
                                                "payload": payload
                                            }
                                            await websocket.send_text(json.dumps(client_message))
                                        
                                        else:
                                            # Other Phoenix events, forward as-is
                                            await websocket.send_text(text)
                                    else:
                                        # Not a Phoenix frame, forward as-is
                                        await websocket.send_text(text)
                                        
                                except json.JSONDecodeError:
                                    # Not JSON, forward as-is
                                    await websocket.send_text(text)
                                    
                        except websockets.exceptions.ConnectionClosed:
                            logger.info("Phoenix disconnected.")
                            break
                        except Exception as e:
                            logger.error(f"Error forwarding Phoenix message: {e}")
                            break
                except Exception as e:
                    logger.error(f"Phoenix forwarding task error: {e}")

            # Run both forwarding tasks concurrently
            await asyncio.gather(
                forward_client_to_phoenix(),
                forward_phoenix_to_client(),
                return_exceptions=True
            )

    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"Phoenix WebSocket connection closed: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Realtime service unavailable")
    except websockets.exceptions.InvalidURI as e:
        logger.error(f"Invalid Phoenix WebSocket URL: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Invalid realtime service URL")
    except websockets.exceptions.WebSocketException as e:
        logger.error(f"WebSocket connection error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="WebSocket connection failed")
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected during initial setup.")
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket proxy: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error")
    finally:
        logger.info("WebSocket proxy connection closed.")