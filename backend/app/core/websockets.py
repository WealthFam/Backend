import logging
from typing import Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # tenant_id -> set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

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

manager = ConnectionManager()
