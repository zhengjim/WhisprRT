"""
音频设备相关的API端点
"""
from fastapi import APIRouter
from app.models.schemas import DeviceRequest
from app.services.audio import audio_service
from app.services.transcription import transcription_service

router = APIRouter()

@router.get('/audio_devices')
def get_audio_devices():
    """
    获取系统上所有可用的音频输入设备
    
    Returns:
        包含所有可用音频设备的列表
    """
    return audio_service.get_devices()

@router.post('/select_device')
def select_audio_device(request: DeviceRequest):
    """
    选择要使用的音频输入设备
    
    Args:
        request: 包含设备ID的请求对象
    
    Returns:
        操作状态和消息
    """
    if transcription_service.running:
        return {"status": "error", "message": "请先停止转写再切换音频设备"}
    
    return audio_service.select_device(request.device_id)