"""
日志配置模块
"""
import logging

def setup_logging():
    """
    配置应用日志
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("whisper_live")
    return logger

# 创建全局日志记录器
logger = setup_logging()