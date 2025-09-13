import logging
import os
import sys
from datetime import datetime


DATETIME = datetime.now().strftime('%Y-%m-%d-%H%M%S')
# DATETIME = "debug" # 为了方便，调试的时候输出到 debug.log 文件
LOG_FILE = f'saves/log/project-{DATETIME}.log'

def setup_logger(name, level=logging.DEBUG, console=True):
    os.makedirs("saves/log", exist_ok=True)

    """Function to setup logger with the given name and log file."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 清除已有的 Handler，防止重复添加
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler for logging to a file with UTF-8 encoding
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(level)

    # Formatter for the logs
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler for logging to the console (optional)
    if console:
        # 为Windows控制台创建安全的日志处理器
        if sys.platform == "win32":
            # 创建一个自定义的StreamHandler来处理编码问题
            console_handler = SafeConsoleHandler()
        else:
            console_handler = logging.StreamHandler()
            
        # 控制台输出级别设为INFO，减少输出量
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


class SafeConsoleHandler(logging.StreamHandler):
    """安全的控制台处理器，处理Unicode编码问题"""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # 在Windows上安全地写入，避免Unicode错误
            if hasattr(stream, 'encoding') and stream.encoding:
                # 使用控制台的编码，如果无法编码则忽略错误字符
                msg = msg.encode(stream.encoding, errors='replace').decode(stream.encoding)
            stream.write(msg + self.terminator)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


# Setup the root logger
logger = setup_logger('ThreatRAG')

# If you want to disable logging from external libraries
# logging.getLogger('some_external_library').setLevel(logging.CRITICAL)
