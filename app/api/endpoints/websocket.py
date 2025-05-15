"""
WebSocket相关的API端点
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.transcription import transcription_service
from app.services.whisper import whisper_service
from app.core.logging import logger

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    处理WebSocket连接
    
    Args:
        websocket: WebSocket连接对象
    """
    await websocket.accept()
    transcription_service.connected_websockets.add(websocket)
    
    try:
        await websocket.send_json({
            "event": "status",
            "data": {
                'status': 'connected',
                'model': whisper_service.model_name,
                'language': transcription_service.current_language
            }
        })  
        # 保持连接
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("客户端已断开连接")
    finally:
        transcription_service.connected_websockets.remove(websocket)