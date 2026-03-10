import asyncio
import logging
from typing import Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # tenant_id -> set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.loop = None # Initialized during FastAPI startup

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    async def connect(self, websocket: WebSocket, tenant_id: str):
        await websocket.accept()
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = set()
        self.active_connections[tenant_id].add(websocket)
        logger.info(f"WebSocket connected for tenant {tenant_id}. Total connections for tenant: {len(self.active_connections[tenant_id])}")
        
        # Send initial confirmation message to trigger Flutter's isConnected state
        await websocket.send_json({"type": "CONNECTION_ESTABLISHED", "status": "success"})

    def disconnect(self, websocket: WebSocket, tenant_id: str):
        if tenant_id in self.active_connections:
            self.active_connections[tenant_id].discard(websocket)
            if not self.active_connections[tenant_id]:
                del self.active_connections[tenant_id]
        logger.info(f"WebSocket disconnected for tenant {tenant_id}")

    async def broadcast_to_tenant(self, tenant_id: str, message: dict):
        if tenant_id not in self.active_connections:
            return

        disconnected_sockets = []
        for connection in self.active_connections[tenant_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected_sockets.append(connection)

        # Cleanup failed connections
        for socket in disconnected_sockets:
            self.disconnect(socket, tenant_id)

    def broadcast_to_tenant_threadsafe(self, tenant_id: str, message: dict):
        """
        Thread-safe broadcast that can be called from sync code or background threads.
        Bridges to the main event loop using loop.call_soon_threadsafe.
        """
        if not self.loop:
            # Fallback if loop wasn't set, try to get the running loop
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.error("No event loop available for thread-safe broadcast.")
                return

        def _broadcast():
            asyncio.create_task(self.broadcast_to_tenant(tenant_id, message))

        self.loop.call_soon_threadsafe(_broadcast)

manager = ConnectionManager()
