import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import glob

class LogManager:
    _instance = None
    LOG_DIR = "logs"
    MAX_LOG_DAYS = 7  # 保留最近7天的日志
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
            cls._instance.__initialized = False
        return cls._instance
    
    def __init__(self):
        if not self.__initialized:
            self.__initialized = True
            self._setup_log_directory()
            self._current_log_file = None
            self._logger = None
            self._setup_logger()
            self._cleanup_old_logs()
    
    def _setup_log_directory(self):
        """确保日志目录存在"""
        try:
            # 首先尝试在应用安装目录创建日志文件夹
            from utils.resource_path import get_resource_path
            base_dir = Path(get_resource_path(""))
            self.log_path = base_dir / self.LOG_DIR
            
            # 如果应用目录不可写，则在用户目录下创建
            if not os.access(base_dir, os.W_OK):
                import tempfile
                self.log_path = Path(tempfile.gettempdir()) / "NeuroFeed" / self.LOG_DIR
            
            self.log_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            # 如果上述都失败，回退到当前目录
            self.log_path = Path(self.LOG_DIR)
            self.log_path.mkdir(exist_ok=True)
    
    def _setup_logger(self):
        """设置日志记录器"""
        current_time = datetime.now()
        log_filename = f"neurofeed_{current_time.strftime('%Y%m%d')}.log"
        self._current_log_file = self.log_path / log_filename
        
        # 获取根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # 移除所有现有的处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 创建文件处理器
        file_handler = logging.FileHandler(self._current_log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # 添加控制台处理器（开发时使用）
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(file_formatter)
        root_logger.addHandler(console_handler)
        
        # 保存处理器引用
        self._logger = root_logger
        self._file_handler = file_handler
    
    def _cleanup_old_logs(self):
        """清理旧日志文件"""
        cutoff_date = datetime.now() - timedelta(days=self.MAX_LOG_DAYS)
        for log_file in self.log_path.glob("neurofeed_*.log"):
            try:
                file_date = datetime.strptime(log_file.stem[10:], "%Y%m%d")
                if file_date < cutoff_date:
                    log_file.unlink()
            except (ValueError, OSError):
                continue
    
    def log_task_event(self, task_state):
        """记录任务相关事件"""
        message = (f"Task: {task_state.name} [{task_state.task_id}] - "
                  f"Status: {task_state.status.value}")
        
        if task_state.progress:
            message += f" - Progress: {task_state.progress}%"
        if task_state.message:
            message += f" - Message: {task_state.message}"
        if task_state.error:
            message += f" - Error: {task_state.error}"
            self._logger.error(message)
        else:
            self._logger.info(message)
    
    def get_latest_log_file(self) -> Optional[Path]:
        """获取最新的日志文件路径"""
        return self._current_log_file if self._current_log_file else None

    def get_logger(self, name: str) -> logging.Logger:
        """获取指定名称的日志记录器"""
        return logging.getLogger(name)
