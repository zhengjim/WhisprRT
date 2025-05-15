"""
配置模块，包含应用的所有配置参数
"""

# 音频配置
SAMPLE_RATE = 16000
BLOCK_SIZE = 4000
BUFFER_SECONDS = 5

# 模型配置
AVAILABLE_MODELS = {
    "tiny": "最小模型，速度最快，精度最低",
    "base": "基础模型，速度快，精度一般",
    "small": "小型模型，速度和精度平衡",
    "large-v3-turbo": "大型模型，精度高，接近tiny的速度"
}
DEFAULT_MODEL = "large-v3-turbo"
DEFAULT_LANGUAGE = "zh"

# 服务器配置
HOST = "0.0.0.0"
PORT = 5444