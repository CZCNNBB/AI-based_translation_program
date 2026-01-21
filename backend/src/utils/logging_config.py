import sys
import logging

def setup_logging():
    """
    配置统一的日志格式
    """
    # 定义日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 获取根记录器
    root_logger = logging.getLogger()
    
    # 如果已经有 handler，先清除（避免重复打印）
    if root_logger.handlers:
        root_logger.handlers = []

    # 配置根记录器
    logging.basicConfig(
        level=logging.INFO, # 默认级别
        format=log_format,  # 日志格式
        datefmt=date_format,    # 日期格式
        handlers=[  # 日志处理器
            logging.StreamHandler(sys.stdout)
        ],
        force=True # 强制重新配置（Python 3.8+）
    )
    
    # 抑制一些嘈杂的第三方库日志
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
