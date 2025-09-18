# -*- coding: utf-8 -*-
"""
航班数据爬虫系统 - 日志系统模块

本模块提供完整的日志记录功能，支持：
- 按天分割的日志文件管理
- 多级别日志记录
- 异常信息详细记录
- 航班处理过程跟踪
- 系统状态统计
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import traceback


class FlightCrawlerLogger:
    """
    航班爬虫系统日志管理器
    
    提供完整的日志记录功能，包括文件日志和控制台日志
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化日志系统
        
        Args:
            config: 日志配置字典
        """
        self.config = config
        self.logger = None
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """
        设置日志系统配置
        
        配置文件日志和控制台日志，支持按天轮转
        """
        # 创建日志目录
        log_dir = self.config.get('log_dir', 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 创建logger
        self.logger = logging.getLogger('FlightCrawler')
        self.logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        
        # 清除已有的处理器
        self.logger.handlers.clear()
        
        # 创建格式化器
        formatter = logging.Formatter(
            fmt=self.config.get('format', 
                '%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s'),
            datefmt=self.config.get('date_format', '%Y-%m-%d %H:%M:%S')
        )
        
        # 设置文件处理器（按天轮转）
        if self.config.get('file_rotation', 'daily') == 'daily':
            log_filename = os.path.join(
                log_dir, 
                f"{self.config.get('file_prefix', 'flight_crawler_')}{datetime.now().strftime('%Y-%m-%d')}.log"
            )
            file_handler = logging.handlers.TimedRotatingFileHandler(
                filename=log_filename,
                when='midnight',
                interval=1,
                backupCount=self.config.get('backup_count', 30),
                encoding='utf-8'
            )
        else:
            # 按大小轮转
            log_filename = os.path.join(
                log_dir,
                f"{self.config.get('file_prefix', 'flight_crawler_')}.log"
            )
            max_bytes = self._parse_size(self.config.get('max_file_size', '10MB'))
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_filename,
                maxBytes=max_bytes,
                backupCount=self.config.get('backup_count', 30),
                encoding='utf-8'
            )
        
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 设置控制台处理器
        if self.config.get('console_output', True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def _parse_size(self, size_str: str) -> int:
        """
        解析文件大小字符串
        
        Args:
            size_str: 大小字符串，如"10MB", "1GB"
            
        Returns:
            字节数
        """
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def debug(self, message: str) -> None:
        """
        记录调试信息
        
        Args:
            message: 调试消息
        """
        if self.logger:
            self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """
        记录一般信息
        
        Args:
            message: 信息消息
        """
        if self.logger:
            self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """
        记录警告信息
        
        Args:
            message: 警告消息
        """
        if self.logger:
            self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """
        记录错误信息
        
        Args:
            message: 错误消息
        """
        if self.logger:
            self.logger.error(message)
    
    def critical(self, message: str) -> None:
        """
        记录严重错误信息
        
        Args:
            message: 严重错误消息
        """
        if self.logger:
            self.logger.critical(message)
    
    def log_flight_process(self, flight_number: str, operation: str, status: str, details: str = "") -> None:
        """
        记录航班处理过程日志
        
        Args:
            flight_number: 航班号
            operation: 操作类型，如"验证码识别", "数据提取", "Excel保存"
            status: 操作状态，如"开始", "成功", "失败", "重试"
            details: 详细信息或错误描述
        """
        message = f"航班 {flight_number} - {operation} - {status}"
        if details:
            message += f" - {details}"
        
        if status in ["成功", "开始"]:
            self.info(message)
        elif status == "重试":
            self.warning(message)
        elif status == "失败":
            self.error(message)
        else:
            self.info(message)
    
    def log_exception(self, module_name: str, function_name: str, exception: Exception, 
                     context: Optional[Dict[str, Any]] = None) -> None:
        """
        记录异常信息，包含详细的上下文信息
        
        Args:
            module_name: 发生异常的模块名称
            function_name: 发生异常的函数名称
            exception: 异常对象
            context: 异常发生时的上下文信息
        """
        error_msg = f"异常发生在 {module_name}.{function_name}: {type(exception).__name__}: {str(exception)}"
        
        if context:
            context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
            error_msg += f" | 上下文: {context_str}"
        
        # 记录异常信息
        self.error(error_msg)
        
        # 记录堆栈跟踪
        stack_trace = traceback.format_exc()
        self.error(f"堆栈跟踪:\n{stack_trace}")
    
    def log_system_status(self, total_flights: int, processed: int, success: int, failed: int) -> None:
        """
        记录系统运行状态统计信息
        
        Args:
            total_flights: 总航班数
            processed: 已处理数量
            success: 成功数量
            failed: 失败数量
        """
        success_rate = (success / processed * 100) if processed > 0 else 0
        message = (f"系统状态统计 - 总数: {total_flights}, 已处理: {processed}, "
                  f"成功: {success}, 失败: {failed}, 成功率: {success_rate:.1f}%")
        self.info(message)
    
    def log_retry_attempt(self, operation: str, attempt: int, max_attempts: int, 
                         reason: str = "") -> None:
        """
        记录重试尝试信息
        
        Args:
            operation: 操作名称
            attempt: 当前尝试次数
            max_attempts: 最大尝试次数
            reason: 重试原因
        """
        message = f"{operation} 重试 {attempt}/{max_attempts}"
        if reason:
            message += f" - 原因: {reason}"
        self.warning(message)
    
    def log_system_start(self, config_info: Dict[str, Any]) -> None:
        """
        记录系统启动信息
        
        Args:
            config_info: 配置信息
        """
        self.info("=" * 50)
        self.info("航班数据爬虫系统启动")
        self.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.info(f"Python版本: {sys.version}")
        
        # 记录关键配置信息
        if 'browser' in config_info:
            browser_config = config_info['browser']
            self.info(f"浏览器配置: headless={browser_config.get('headless')}, "
                     f"timeout={browser_config.get('timeout')}s")
        
        if 'retry' in config_info:
            retry_config = config_info['retry']
            self.info(f"重试配置: 验证码最大重试={retry_config.get('captcha_max_attempts')}, "
                     f"时间图片最大重试={retry_config.get('time_image_max_attempts')}")
        
        self.info("=" * 50)
    
    def log_system_end(self, total_time: float, final_stats: Dict[str, int]) -> None:
        """
        记录系统结束信息
        
        Args:
            total_time: 总运行时间（秒）
            final_stats: 最终统计信息
        """
        self.info("=" * 50)
        self.info("航班数据爬虫系统结束")
        self.info(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.info(f"总运行时间: {total_time:.2f}秒")
        
        if final_stats:
            self.log_system_status(
                final_stats.get('total', 0),
                final_stats.get('processed', 0),
                final_stats.get('success', 0),
                final_stats.get('failed', 0)
            )
        
        self.info("=" * 50)


# 全局日志实例
_logger_instance = None


def setup_logger(config: Dict[str, Any]) -> FlightCrawlerLogger:
    """
    初始化日志系统，配置按天分割的日志文件
    
    Args:
        config: 日志配置字典
        
    Returns:
        配置好的Logger实例
    """
    global _logger_instance
    _logger_instance = FlightCrawlerLogger(config)
    return _logger_instance


def get_logger() -> Optional[FlightCrawlerLogger]:
    """
    获取全局日志实例
    
    Returns:
        日志实例，如果未初始化则自动初始化
    """
    global _logger_instance
    if _logger_instance is None:
        # 使用默认配置初始化
        default_config = {
            'level': 'INFO',
            'directory': 'logs',
            'max_file_size': 10,
            'backup_count': 7,
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
        _logger_instance = FlightCrawlerLogger(default_config)
    return _logger_instance


# 便捷函数
def log_flight_process(flight_number: str, process: str, status: str, details: str = ''):
    """
    记录航班处理过程的便捷函数
    
    Args:
        flight_number: 航班号
        process: 处理过程
        status: 状态
        details: 详细信息
    """
    logger = get_logger()
    if logger:
        message = f"[{flight_number}] {process} - {status}"
        if details:
            message += f" | {details}"
        
        if status in ['失败', '异常', '错误']:
            logger.error(message)
        elif status in ['警告', '重试']:
            logger.warning(message)
        else:
            logger.info(message)


def log_system_info(message: str):
    """
    记录系统信息的便捷函数
    
    Args:
        message: 系统信息消息
    """
    logger = get_logger()
    if logger:
        logger.info(f"[SYSTEM] {message}")


def log_exception(module_name: str, function_name: str, exception: Exception, 
                 context: Optional[Dict[str, Any]] = None) -> None:
    """
    记录异常信息的便捷函数
    
    Args:
        module_name: 模块名称
        function_name: 函数名称
        exception: 异常对象
        context: 上下文信息
    """
    if _logger_instance:
        _logger_instance.log_exception(module_name, function_name, exception, context)


def log_system_status(total_flights: int, processed: int, success: int, failed: int) -> None:
    """
    记录系统运行状态统计信息的便捷函数
    
    Args:
        total_flights: 总航班数
        processed: 已处理数量
        success: 成功数量
        failed: 失败数量
    """
    if _logger_instance:
        _logger_instance.log_system_status(total_flights, processed, success, failed)