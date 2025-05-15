"""
音频处理服务
"""
import sounddevice as sd
from app.core.logging import logger

class AudioService:
    """音频服务类"""
    
    def __init__(self):
        """初始化音频服务"""
        self.current_device = None
    
    def get_devices(self):
        """
        获取系统上所有可用的音频输入设备
        
        Returns:
            dict: 包含所有可用音频设备的信息
        """
        try:
            devices = sd.query_devices()
            input_devices = []
            
            for i, device in enumerate(devices):
                # 只添加输入设备或双向设备
                if device['max_input_channels'] > 0:
                    input_devices.append({
                        'id': i,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'default': device.get('default_input', False)
                    })
            
            # 找出默认设备
            default_device = None
            try:
                default_device = sd.query_devices(kind='input')
                default_id = default_device['index'] if 'index' in default_device else None
            except:
                default_id = None
                
            return {
                "devices": input_devices,
                "default": default_id
            }
        except Exception as e:
            logger.error(f"获取音频设备失败: {str(e)}")
            return {"status": "error", "message": f"获取音频设备失败: {str(e)}"}
    
    def select_device(self, device_id):
        """
        选择要使用的音频输入设备
        
        Args:
            device_id: 设备ID
        
        Returns:
            dict: 操作状态和消息
        """
        try:
            # 如果设备ID为"default"或空，则使用系统默认设备
            if device_id == "default" or not device_id:
                self.current_device = None
                logger.info("已选择系统默认音频设备")
                return {"status": "success", "message": "已选择系统默认音频设备"}
            
            # 否则尝试使用指定的设备ID
            device_id = int(device_id)
            devices = sd.query_devices()
            
            if device_id >= len(devices) or device_id < 0:
                return {"status": "error", "message": f"无效的设备ID: {device_id}"}
            
            device = devices[device_id]
            if device['max_input_channels'] <= 0:
                return {"status": "error", "message": f"选择的设备不支持音频输入: {device['name']}"}
            
            self.current_device = device_id
            logger.info(f"已选择音频设备: {device['name']} (ID: {device_id})")
            return {"status": "success", "message": f"已选择音频设备: {device['name']}"}
        except Exception as e:
            logger.error(f"选择音频设备失败: {str(e)}")
            return {"status": "error", "message": f"选择音频设备失败: {str(e)}"}
    
    def create_input_stream(self, samplerate, channels, dtype, callback, blocksize):
        """
        创建音频输入流
        
        Args:
            samplerate: 采样率
            channels: 通道数
            dtype: 数据类型
            callback: 回调函数
            blocksize: 块大小
            
        Returns:
            InputStream: 音频输入流
        """
        return sd.InputStream(
            samplerate=samplerate, 
            channels=channels, 
            dtype=dtype,
            callback=callback, 
            blocksize=blocksize, 
            device=self.current_device
        )

# 创建全局音频服务实例
audio_service = AudioService()