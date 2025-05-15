"""
语音转写服务
"""
import time
import queue
import threading
import asyncio
import numpy as np
from app.core.logging import logger
from app.config import SAMPLE_RATE, BLOCK_SIZE, BUFFER_SECONDS, DEFAULT_LANGUAGE
from app.services.whisper import whisper_service
from app.services.audio import audio_service

class TranscriptionService:
    """语音转写服务类"""
    
    def __init__(self):
        """初始化转写服务"""
        self.q = queue.Queue()
        self.buffer = np.empty((0, 1), dtype='float32')
        self.transcript = []
        self.last_time = time.time()
        self.running = False
        self.current_language = DEFAULT_LANGUAGE
        self.connected_websockets = set()
    
    def audio_callback(self, indata, frames, time_info, status):
        """
        音频数据回调函数，将捕获的音频数据放入队列
        
        Args:
            indata: 输入的音频数据
            frames: 帧数
            time_info: 时间信息
            status: 状态信息
        """
        if status:
            logger.warning(f"音频状态异常: {status}")
        self.q.put(indata.copy())
    
    async def broadcast_to_websockets(self, event_type, data):
        """
        向所有连接的WebSocket客户端广播消息
        
        Args:
            event_type: 事件类型
            data: 要发送的数据
        """
        for websocket in self.connected_websockets:
            try:
                await websocket.send_json({"event": event_type, "data": data})
            except Exception as e:
                logger.error(f"WebSocket发送消息失败: {str(e)}")
    
    def listen_loop(self):
        """语音转写主循环，从队列获取音频数据并进行转写"""
        logger.info("开始语音转写线程")
        with audio_service.create_input_stream(
            samplerate=SAMPLE_RATE, 
            channels=1, 
            dtype='float32',
            callback=self.audio_callback, 
            blocksize=BLOCK_SIZE
        ):
            while self.running:
                try:
                    data = self.q.get(timeout=1)
                    self.buffer = np.append(self.buffer, data, axis=0)

                    if time.time() - self.last_time > BUFFER_SECONDS:
                        if len(self.buffer) >= SAMPLE_RATE:
                            samples = self.buffer[:, 0]
                            try:
                                segments, _ = whisper_service.transcribe(samples, self.current_language)
                                
                                for seg in segments:
                                    text = seg.text.strip()
                                    if text:  # 只发送非空文本
                                        timestamp = time.strftime("%H:%M:%S", time.localtime())
                                        # 使用异步事件循环发送WebSocket消息
                                        asyncio.run(self.broadcast_to_websockets('transcription', {
                                            'text': text, 
                                            'timestamp': timestamp,
                                            'show_timestamp': True  # 默认显示时间戳
                                        }))
                                        self.transcript.append({"text": text, "timestamp": timestamp})
                                        logger.debug(f"转写文本: {text}")
                            except Exception as e:
                                logger.error(f"转写过程出错: {str(e)}")
                                asyncio.run(self.broadcast_to_websockets('error', {'message': f'转写错误: {str(e)}'}))

                        self.buffer = np.empty((0, 1), dtype='float32')
                        self.last_time = time.time()
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"转写线程异常: {str(e)}")
                    asyncio.run(self.broadcast_to_websockets('error', {'message': f'系统错误: {str(e)}'}))
                    
        logger.info("语音转写线程已停止")
    
    def start(self):
        """
        开始语音转写
        
        Returns:
            dict: 操作状态
        """
        if not self.running:
            self.running = True
            self.transcript = []  # 清空之前的转写记录
            # 启动后台线程
            thread = threading.Thread(target=self.listen_loop)
            thread.daemon = True
            thread.start()
            logger.info("开始语音转写")
            return {"status": "started"}
        return {"status": "already_started"}
    
    def stop(self):
        """
        停止语音转写
        
        Returns:
            dict: 操作状态
        """
        if self.running:
            self.running = False
            logger.info("停止语音转写")
            return {"status": "stopped"}
        return {"status": "already_stopped"}
    
    def clear(self):
        """
        清空转写记录
        
        Returns:
            dict: 操作状态
        """
        self.transcript = []
        logger.info("清空转写记录")
        return {"status": "cleared"}
    
    def save(self, file_path='transcript_output.txt'):
        """
        保存转写结果为文本文件
        
        Args:
            file_path: 保存的文件路径
            
        Returns:
            str: 文件路径或错误信息
        """
        if self.transcript:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for item in self.transcript:
                        if isinstance(item, dict):
                            f.write(f"[{item['timestamp']}] {item['text']}\n")
                        else:
                            f.write(f"{item}\n")
                logger.info(f"转写结果已保存到: {file_path}")
                return file_path
            except Exception as e:
                logger.error(f"保存文件失败: {str(e)}")
                return {"status": "error", "message": f"保存失败: {str(e)}"}
        return {"status": "no_text"}
    
    def set_language(self, language):
        """
        设置转写语言
        
        Args:
            language: 语言代码
            
        Returns:
            dict: 操作状态和消息
        """
        self.current_language = language
        return {"status": "success", "message": f"已切换到语言: {language}"}

# 创建全局转写服务实例
transcription_service = TranscriptionService()