"""
Whisper 模型服务
"""
from faster_whisper import WhisperModel
from app.core.logging import logger
from app.config import DEFAULT_MODEL, ANTI_HALLUCINATION_CONFIG

class WhisperService:
    """Whisper 模型服务类"""
    
    def __init__(self):
        """初始化 Whisper 服务"""
        self.model = None
        self.model_name = DEFAULT_MODEL
        self.load_model(DEFAULT_MODEL)
    
    def load_model(self, model_name):
        """
        加载指定的 Whisper 模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            WhisperModel: 加载的模型实例
        """
        try:
            logger.info(f"正在加载模型: {model_name} ")
            self.model = WhisperModel(
                model_name, 
                device="cpu",           
                compute_type="int8",   
                cpu_threads=8,             
                num_workers=1 
            )
            self.model_name = model_name
            logger.info(f"模型 {model_name} 加载成功")
            return self.model
        except Exception as e:
            logger.error(f"模型加载失败: {str(e)}")
            # 如果加载失败，尝试加载默认模型
            if model_name != DEFAULT_MODEL:
                logger.info(f"尝试加载默认模型: {DEFAULT_MODEL}")
                self.model = WhisperModel(
                    DEFAULT_MODEL, 
                    device="cpu", 
                    compute_type="int8", 
                    cpu_threads=8, 
                    num_workers=1
                )
                self.model_name = DEFAULT_MODEL
                return self.model
            raise
    
    def transcribe(self, audio_samples, language):
        """
        转写音频
        
        Args:
            audio_samples: 音频样本数据
            language: 语言代码
            
        Returns:
            tuple: (segments, info) 转写结果和信息
        """
        # 使用速度优化的推理参数
        config = ANTI_HALLUCINATION_CONFIG
        return self.model.transcribe(
            audio_samples, 
            language=language,
            beam_size=1,                          # 从默认5降到1，大幅提升速度
            best_of=1,                           # 从默认5降到1，提升速度
            temperature=config["temperature"],
            no_speech_threshold=config["no_speech_threshold"],
            condition_on_previous_text=config["condition_on_previous_text"],
            compression_ratio_threshold=config["compression_ratio_threshold"],
            log_prob_threshold=config["log_prob_threshold"],
            initial_prompt=config["initial_prompt"],
            word_timestamps=False,                # 不生成词级时间戳，提升速度
            vad_filter=True,                     # 启用 VAD 过滤，减少无效推理
            vad_parameters=dict(
                min_silence_duration_ms=500,      # 最小静音持续时间
                speech_pad_ms=400                 # 语音填充时间
            )
        )

# 创建全局 Whisper 服务实例
whisper_service = WhisperService()