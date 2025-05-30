"""
语音转写服务
"""
import time
import queue
import threading
import asyncio
import numpy as np
import re
from app.core.logging import logger
from app.config import (
    SAMPLE_RATE, BLOCK_SIZE, BUFFER_SECONDS, DEFAULT_LANGUAGE,
    ANTI_HALLUCINATION_CONFIG, HALLUCINATION_PATTERNS
)
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
        self.start_time = None  # 新增：记录录音开始时间
        self.display_mode = "segments"  # 显示模式
        self.continuous_text = ""  # 新增：用于存储连续显示的文本
        
        # 从配置文件加载反幻觉参数
        config = ANTI_HALLUCINATION_CONFIG
        self.energy_threshold = config["energy_threshold"]
        self.confidence_threshold = config["confidence_threshold"]
        self.silence_threshold = config["silence_threshold"]
        self.zcr_threshold = config["zcr_threshold"]
        self.hallucination_patterns = HALLUCINATION_PATTERNS
    
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
    
    def preprocess_audio(self, audio_data):
        """
        音频预处理：去噪和归一化
        
        Args:
            audio_data: 原始音频数据
            
        Returns:
            numpy.ndarray: 预处理后的音频数据 (float32)
        """
        # 确保输入是 float32 类型
        audio_data = audio_data.astype(np.float32)
        
        # 归一化音频
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = audio_data / max_val
        
        # 简单的高通滤波器去除低频噪音
        # 使用差分近似高通滤波
        if len(audio_data) > 1:
            filtered = np.diff(audio_data)
            # 补齐长度
            filtered = np.append(filtered, 0)
            result = filtered * 0.5 + audio_data * 0.5
        else:
            result = audio_data
        
        # 确保返回 float32 类型
        return result.astype(np.float32)

    def is_silence(self, audio_data):
        """
        增强的静音检测：结合能量和零交叉率
        
        Args:
            audio_data: 音频数据
            
        Returns:
            bool: 是否为静音
        """
        if len(audio_data) == 0:
            return True
            
        # 计算音频能量
        energy = np.mean(np.abs(audio_data))
        
        # 计算零交叉率 (Zero Crossing Rate)
        zero_crossings = np.sum(np.abs(np.diff(audio_data > 0)))
        zcr = zero_crossings / max(len(audio_data) - 1, 1)
        
        # 计算频谱中心（简化版）
        fft = np.fft.fft(audio_data)
        magnitude = np.abs(fft)
        freqs = np.fft.fftfreq(len(audio_data), 1/SAMPLE_RATE)
        
        # 避免除零错误
        magnitude_sum = np.sum(magnitude[:len(magnitude)//2])
        if magnitude_sum > 0:
            spectral_centroid = np.sum(freqs[:len(freqs)//2] * magnitude[:len(magnitude)//2]) / magnitude_sum
        else:
            spectral_centroid = 0
        
        # 综合判断：低能量、低零交叉率且频谱中心异常
        is_silent = (energy < self.silence_threshold and 
                    zcr < self.zcr_threshold) or \
                   (energy < self.energy_threshold and spectral_centroid < 100)
        
        if is_silent:
            logger.debug(f"检测到静音: energy={energy:.4f}, zcr={zcr:.4f}, spectral_centroid={spectral_centroid:.2f}")
        
        return is_silent

    def contains_hallucination(self, text):
        """
        检测文本是否包含已知的幻觉内容
        
        Args:
            text: 要检测的文本
            
        Returns:
            bool: 是否包含幻觉内容
        """
        if not text or len(text.strip()) == 0:
            return False
            
        text_clean = text.strip()
        
        # 检查是否包含幻觉关键词模式
        for pattern in self.hallucination_patterns:
            if re.search(pattern, text_clean, re.IGNORECASE):
                logger.warning(f"检测到幻觉内容: '{text_clean}' 匹配模式: '{pattern}'")
                return True
        
        # 检查重复内容（连续重复的字符或词组）
        if len(text_clean) > 10:
            # 检查字符重复
            for i in range(len(text_clean) - 5):
                substr = text_clean[i:i+3]
                if text_clean.count(substr) > 3:
                    logger.warning(f"检测到重复内容: '{text_clean}' 重复片段: '{substr}'")
                    return True
        
        # 检查是否全是标点符号或特殊字符
        if re.match(r'^[^\w\s]*$', text_clean):
            logger.warning(f"检测到非语言内容: '{text_clean}'")
            return True
            
        return False

    def validate_transcription_quality(self, text, confidence):
        """
        验证转写结果的质量
        
        Args:
            text: 转写文本
            confidence: 置信度
            
        Returns:
            bool: 是否为高质量转写结果
        """
        if not text or len(text.strip()) == 0:
            return False
            
        # 置信度过低
        if confidence < self.confidence_threshold:
            logger.debug(f"置信度过低: {confidence:.3f} < {self.confidence_threshold}")
            return False
            
        # 包含幻觉内容
        if self.contains_hallucination(text):
            return False
            
        # 文本过短且置信度不是很高
        if len(text.strip()) < 3 and confidence < 0.8:
            logger.debug(f"文本过短且置信度不高: '{text}' confidence={confidence:.3f}")
            return False
            
        return True

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
                            
                            # 音频预处理 - 确保数据类型正确
                            samples = self.preprocess_audio(samples)
                            # 再次确保是 float32 类型
                            samples = samples.astype(np.float32)
                            
                            # 检查是否为静音
                            if not self.is_silence(samples):
                                try:
                                    segments, _ = whisper_service.transcribe(samples, self.current_language)
                                    segments_list = list(segments)
                                    
                                    for seg in segments_list:
                                        confidence = np.exp(seg.avg_logprob)
                                        text = seg.text.strip()
                                        
                                        # 验证转写质量
                                        if self.validate_transcription_quality(text, confidence):
                                            elapsed = int(time.time() - self.start_time)
                                            hours = elapsed // 3600
                                            minutes = (elapsed % 3600) // 60
                                            seconds = elapsed % 60
                                            timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                                            
                                            # 只推送高质量的分段内容
                                            asyncio.run(self.broadcast_to_websockets('transcription', {
                                                'text': text,
                                                'timestamp': timestamp,
                                                'show_timestamp': True,
                                                'confidence': confidence,
                                                'mode': 'segments'
                                            }))
                                            self.transcript.append({
                                                "text": text,
                                                "timestamp": timestamp,
                                                "confidence": confidence
                                            })
                                            logger.info(f"转写成功: '{text}' (confidence: {confidence:.3f})")
                                        else:
                                            logger.debug(f"过滤低质量转写: '{text}' (confidence: {confidence:.3f})")
                                            
                                except Exception as e:
                                    logger.error(f"转写过程出错: {str(e)}")
                                    asyncio.run(self.broadcast_to_websockets('error', {'message': f'转写错误: {str(e)}'}))
                            else:
                                logger.debug("检测到静音，跳过转写")

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
            self.start_time = time.time()  # 新增：记录开始时间
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
        self.continuous_text = ""  # 清空连续文本
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
                            # 只保存时间戳和文本，不保存置信度
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

    def set_display_mode(self, mode):
        """
        设置显示模式
        
        Args:
            mode: 显示模式 ("segments" 或 "transcript")
            
        Returns:
            dict: 操作状态和消息
        """
        if mode not in ["segments", "transcript"]:
            return {"status": "error", "message": "不支持的显示模式"}
        
        self.display_mode = mode
        return {"status": "success", "message": f"已切换到{self.display_mode}模式"}

# 创建全局转写服务实例
transcription_service = TranscriptionService()