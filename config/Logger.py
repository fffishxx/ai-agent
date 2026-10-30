# ---------------- 导入库 ----------------
import logging  # Python 内置日志库
import os       # 用于路径操作
from config import config_manager  # 全局配置管理器

# ---------------- 获取项目路径 ----------------
current_file_path = os.path.abspath(__file__)           # 当前文件绝对路径
current_dir_path = os.path.dirname(current_file_path)   # 当前文件所在目录
project_root = os.path.dirname(current_dir_path)        # 项目根目录

# 从配置中获取日志文件路径（相对于项目根目录）
log_file_path = None
logger_file = config_manager.get("server.logger.file")
if logger_file:
    log_file_path = os.path.join(project_root, logger_file)

# ---------------- 日志器初始化函数 ----------------
def setup_logging(log_file: str = log_file_path):
    """
    初始化日志器。

    功能：
    1. 支持控制台输出
    2. 支持文件输出（可配置路径）
    3. 使用统一日志格式：时间 - 名称 - 级别 - 消息
    4. 避免重复添加处理器
    5. 日志级别根据配置自动设置
    """
    # 创建日志器，指定名称
    logger = logging.getLogger("AgentCenter")

    # 从配置获取日志级别，例如 "INFO"、"DEBUG"
    level = logging.getLevelName(config_manager.get("server.logger.level"))
    logger.setLevel(level)  # 设置日志器级别

    # 避免重复添加处理器
    if not logger.handlers:
        # 日志输出格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # ---------------- 文件日志处理器 ----------------
        if logger_file:
            # 确保日志目录存在
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            # 创建文件处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)       # 文件日志级别
            file_handler.setFormatter(formatter)  # 设置格式
            logger.addHandler(file_handler)     # 添加到日志器

        # ---------------- 控制台日志处理器 ----------------
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)       # 控制台日志级别
        console_handler.setFormatter(formatter)  # 设置格式
        logger.addHandler(console_handler)    # 添加到日志器

    return logger

# ---------------- 初始化全局日志器 ----------------
logger = setup_logging()
