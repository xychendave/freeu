import logging
import sys
from pathlib import Path
from datetime import datetime
from src.utils.config import config

def setup_logging() -> logging.Logger:
    """设置日志系统"""
    # 创建logs目录
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # 配置日志格式
    log_format = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 设置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level))
    
    # 清除现有的处理器
    root_logger.handlers.clear()
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 创建文件处理器
    log_file = log_dir / f'freeu_{datetime.now().strftime("%Y%m%d")}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(log_format, date_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 创建专门的FreeU日志记录器
    logger = logging.getLogger('freeu')
    logger.info("FreeU日志系统初始化完成")
    logger.info(f"日志文件: {log_file}")
    
    return logger

def log_operation_start(operation: str, details: dict = None) -> None:
    """记录操作开始"""
    logger = logging.getLogger('freeu')
    details_str = f" - {details}" if details else ""
    logger.info(f"[开始] {operation}{details_str}")

def log_operation_complete(operation: str, result: str = None) -> None:
    """记录操作完成"""
    logger = logging.getLogger('freeu')
    result_str = f" - {result}" if result else ""
    logger.info(f"[完成] {operation}{result_str}")

def log_operation_error(operation: str, error: str) -> None:
    """记录操作错误"""
    logger = logging.getLogger('freeu')
    logger.error(f"[错误] {operation} - {error}")

def log_operation_warning(operation: str, warning: str) -> None:
    """记录操作警告"""
    logger = logging.getLogger('freeu')
    logger.warning(f"[警告] {operation} - {warning}")

def log_progress(current: int, total: int, operation: str = "处理进度") -> None:
    """记录进度信息"""
    logger = logging.getLogger('freeu')
    percentage = (current / total * 100) if total > 0 else 0
    logger.info(f"[进度] {operation}: {current}/{total} ({percentage:.1f}%)")