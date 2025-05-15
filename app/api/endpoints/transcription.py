"""
转写相关的API端点
"""
from fastapi import APIRouter
from fastapi.responses import FileResponse
from app.models.schemas import ModelRequest, LanguageRequest, TimestampRequest
from app.services.transcription import transcription_service
from app.services.whisper import whisper_service
from app.config import AVAILABLE_MODELS

router = APIRouter()

@router.get('/models')
def get_models():
    """返回可用的模型列表"""
    return {
        "models": AVAILABLE_MODELS,
        "current": whisper_service.model_name
    }

@router.post('/change_model')
def change_model(request: ModelRequest):
    """
    切换Whisper模型
    
    Args:
        request: 包含模型名称的请求对象
    
    Returns:
        操作状态和消息
    """
    model_name = request.model
    
    if model_name not in AVAILABLE_MODELS:
        return {"status": "error", "message": f"不支持的模型: {model_name}"}
    
    if transcription_service.running:
        return {"status": "error", "message": "请先停止转写再切换模型"}
    
    try:
        whisper_service.load_model(model_name)
        return {"status": "success", "message": f"已切换到模型: {model_name}"}
    except Exception as e:
        return {"status": "error", "message": f"切换模型失败: {str(e)}"}

@router.post('/change_language')
def change_language(request: LanguageRequest):
    """
    切换转写语言
    
    Args:
        request: 包含语言代码的请求对象
    
    Returns:
        操作状态和消息
    """
    return transcription_service.set_language(request.language)

@router.get('/start')
def start_listening():
    """
    开始语音转写
    
    Returns:
        操作状态
    """
    return transcription_service.start()

@router.get('/stop')
def stop_listening():
    """
    停止语音转写
    
    Returns:
        操作状态
    """
    return transcription_service.stop()

@router.get('/clear')
def clear_transcript():
    """
    清空转写记录
    
    Returns:
        操作状态
    """
    return transcription_service.clear()

@router.get('/save')
def save_text():
    """
    保存转写结果为文本文件
    
    Returns:
        文本文件或错误信息
    """
    result = transcription_service.save()
    if isinstance(result, str):
        return FileResponse(result, filename="transcript_output.txt")
    return result

@router.post('/toggle_timestamp')
async def toggle_timestamp(request: TimestampRequest):
    """
    切换是否显示时间戳
    
    Args:
        request: 包含时间戳显示设置的请求对象
    
    Returns:
        操作状态和设置
    """
    show_timestamp = request.show_timestamp
    
    await transcription_service.broadcast_to_websockets('timestamp_setting', {'show_timestamp': show_timestamp})
    return {"status": "success", "show_timestamp": show_timestamp}