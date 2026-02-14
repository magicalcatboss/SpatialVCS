from fastapi import WebSocket
from typing import List, Dict
import json

class ConnectionManager:
    """
    Manages WebSocket connections for SpatialVCS.
    Distinguishes between 'Probe' (Data Senders) and 'Dashboard' (Data Receivers).
    """
    def __init__(self):
        # Active connections: client_id -> WebSocket
        self.probes: Dict[str, WebSocket] = {}
        self.dashboards: Dict[str, WebSocket] = {}

    async def connect_probe(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.probes[client_id] = websocket
        print(f"📱 Probe connected: {client_id}")

    async def connect_dashboard(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.dashboards[client_id] = websocket
        print(f"💻 Dashboard connected: {client_id}")

    def disconnect_probe(self, client_id: str):
        if client_id in self.probes:
            del self.probes[client_id]
            print(f"📱 Probe disconnected: {client_id}")

    def disconnect_dashboard(self, client_id: str):
        if client_id in self.dashboards:
            del self.dashboards[client_id]
            print(f"💻 Dashboard disconnected: {client_id}")

    async def broadcast_to_dashboards(self, message: dict):
        """Send a JSON message to ALL connected dashboards."""
        if not self.dashboards:
            return
            
        json_str = json.dumps(message)
        to_remove = []
        
        for client_id, ws in self.dashboards.items():
            try:
                await ws.send_text(json_str)
            except Exception as e:
                print(f"Error broadcasting to {client_id}: {e}")
                to_remove.append(client_id)
        
        # Cleanup dead connections
        for client_id in to_remove:
            self.disconnect_dashboard(client_id)

    async def send_to_probe(self, client_id: str, message: dict):
        """Send message back to a specific probe (e.g. 'Scan Started')."""
        if client_id in self.probes:
            try:
                await self.probes[client_id].send_json(message)
            except:
                self.disconnect_probe(client_id)
