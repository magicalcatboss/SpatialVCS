from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.dependencies import get_socket_manager

router = APIRouter()


@router.websocket("/ws/dashboard/{client_id}")
async def websocket_dashboard(websocket: WebSocket, client_id: str):
    socket_manager = get_socket_manager()
    await socket_manager.connect_dashboard(websocket, client_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        socket_manager.disconnect_dashboard(client_id)
