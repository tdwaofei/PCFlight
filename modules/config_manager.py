# -*- coding: utf-8 -*-
"""
航班数据爬虫系统 - 配置管理模块

本模块提供系统配置的读取、验证和管理功能：
- JSON配置文件读取
- 配置参数验证
- 默认配置提供
- 配置更新和保存
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """
    配置管理器
    
    负责系统配置的加载、验证和管理
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = {}
        self._default_config = self._get_default_config()
        self.load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        
        Returns:
            默认配置字典
        """
        return {
            "browser": {
                "headless": False,
                "window_size": "1920,1080",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "timeout": 30,
                "implicit_wait": 10,
                "page_load_timeout": 60
            },
            "ocr": {
                "engine": "tesseract",
                "language": "eng",
                "config": "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                "time_image_config": "--psm 8 -c tessedit_char_whitelist=0123456789:"
            },
            "retry": {
                "captcha_max_attempts": 6,
                "time_image_max_attempts": 3,
                "delay_seconds": 2,
                "captcha_delay_seconds": 1
            },
            "output": {
                "file_prefix": "flight_data_",
                "timestamp_format": "%Y%m%d_%H%M%S",
                "output_dir": "output",
                "save_images": True,
                "image_format": "base64"
            },
            "logging": {
                "level": "INFO",
                "log_dir": "logs",
                "file_prefix": "flight_crawler_",
                "max_file_size": "10MB",
                "backup_count": 30,
                "format": "%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
                "console_output": True,
                "file_rotation": "daily"
            },
            "website": {
                "base_url": "https://tool.133.cn/flight/",
                "api_url": "https://api.133.cn/tool/flight",
                "identity": "pybLekv4D0g6mPr0"
            },
            "xpath": {
                "flight_number_button": "/html/body/div[1]/div[2]/div[1]/div[1]/div/div/div[1]/span[2]",
                "flight_number_input": "/html/body/div[1]/div[2]/div[1]/div[1]/div/div/div[4]/div/input",
                "departure_date_input": "/html/body/div[1]/div[2]/div[1]/div[1]/div/div/div[5]/div/input",
                "captcha_input": "/html/body/div[1]/div[2]/div[1]/div[1]/div/div/div[6]/div/input",
                "captcha_image": "/html/body/div[1]/div[2]/div[1]/div[1]/div/div/div[6]/img",
                "query_button": "/html/body/div[1]/div[2]/div[1]/div[1]/div/div/button",
                "result_list": "/html/body/div[1]/div[2]/div[1]/div/div[2]/div[3]",
                "segment_base": "/html/body/div[1]/div[2]/div[1]/div/div[2]/div[3]/div[{}]",
                "departure_airport": "/html/body/div[1]/div[2]/div[1]/div/div[2]/div[3]/div[{}]/div[2]/span",
                "arrival_airport": "/html/body/div[1]/div[2]/div[1]/div/div[2]/div[3]/div[{}]/div[3]/span",
                "scheduled_departure": "/html/body/div[1]/div[2]/div[1]/div/div[2]/div[3]/div[{}]/div[4]/span",
                "scheduled_arrival": "/html/body/div[1]/div[2]/div[1]/div/div[2]/div[3]/div[{}]/div[5]/span[1]",
                "actual_departure_img": "/html/body/div[1]/div[2]/div[1]/div/div[2]/div[3]/div[{}]/div[6]/img",
                "actual_arrival_img": "/html/body/div[1]/div[2]/div[1]/div/div[2]/div[3]/div[{}]/div[7]/img",
                "flight_status": "/html/body/div[1]/div[2]/div[1]/div/div[2]/div[3]/div[{}]/div[10]/span"
            }
        }
    
    def load_config(self) -> None:
        """
        加载配置文件
        
        如果配置文件不存在，则使用默认配置并创建配置文件
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # 合并默认配置和加载的配置
                self.config = self._merge_config(self._default_config, loaded_config)
                
                # 验证配置
                self._validate_config()
                
                print(f"配置文件加载成功: {self.config_path}")
            else:
                print(f"配置文件不存在，使用默认配置: {self.config_path}")
                self.config = self._default_config.copy()
                self.save_config()
                
        except json.JSONDecodeError as e:
            print(f"配置文件格式错误: {e}")
            print("使用默认配置")
            self.config = self._default_config.copy()
        except Exception as e:
            print(f"加载配置文件时发生错误: {e}")
            print("使用默认配置")
            self.config = self._default_config.copy()
    
    def _merge_config(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并默认配置和加载的配置
        
        Args:
            default: 默认配置
            loaded: 加载的配置
            
        Returns:
            合并后的配置
        """
        merged = default.copy()
        
        for key, value in loaded.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_config(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _validate_config(self) -> None:
        """
        验证配置参数的有效性
        
        Raises:
            ValueError: 配置参数无效时抛出异常
        """
        # 验证浏览器配置
        browser_config = self.config.get('browser', {})
        if browser_config.get('timeout', 0) <= 0:
            raise ValueError("浏览器超时时间必须大于0")
        
        # 验证重试配置
        retry_config = self.config.get('retry', {})
        if retry_config.get('captcha_max_attempts', 0) <= 0:
            raise ValueError("验证码最大重试次数必须大于0")
        if retry_config.get('time_image_max_attempts', 0) <= 0:
            raise ValueError("时间图片最大重试次数必须大于0")
        
        # 验证日志配置
        logging_config = self.config.get('logging', {})
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if logging_config.get('level') not in valid_levels:
            raise ValueError(f"日志级别必须是以下之一: {valid_levels}")
        
        # 验证目录配置
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """
        确保必要的目录存在
        """
        directories = [
            self.config['logging']['log_dir'],
            self.config['output']['output_dir'],
            'input'  # 输入目录
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"创建目录: {directory}")
    
    def save_config(self) -> None:
        """
        保存配置到文件
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"配置文件保存成功: {self.config_path}")
        except Exception as e:
            print(f"保存配置文件时发生错误: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键，如"browser.timeout"
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        # 导航到最后一级的父级
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
    
    def get_browser_config(self) -> Dict[str, Any]:
        """
        获取浏览器配置
        
        Returns:
            浏览器配置字典
        """
        return self.config.get('browser', {})
    
    def get_ocr_config(self) -> Dict[str, Any]:
        """
        获取OCR配置
        
        Returns:
            OCR配置字典
        """
        return self.config.get('ocr', {})
    
    def get_retry_config(self) -> Dict[str, Any]:
        """
        获取重试配置
        
        Returns:
            重试配置字典
        """
        return self.config.get('retry', {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """
        获取输出配置
        
        Returns:
            输出配置字典
        """
        return self.config.get('output', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        获取日志配置
        
        Returns:
            日志配置字典
        """
        return self.config.get('logging', {})
    
    def get_website_config(self) -> Dict[str, Any]:
        """
        获取网站配置
        
        Returns:
            网站配置字典
        """
        return self.config.get('website', {})
    
    def get_xpath_config(self) -> Dict[str, Any]:
        """
        获取XPath配置
        
        Returns:
            XPath配置字典
        """
        return self.config.get('xpath', {})
    
    def get_xpath(self, element_name: str, segment_index: Optional[int] = None) -> str:
        """
        获取指定元素的XPath
        
        Args:
            element_name: 元素名称
            segment_index: 航段索引（用于动态XPath）
            
        Returns:
            XPath字符串
        """
        xpath_config = self.get_xpath_config()
        xpath = xpath_config.get(element_name, "")
        
        # 如果XPath包含占位符且提供了航段索引，则格式化
        if segment_index is not None and '{}' in xpath:
            xpath = xpath.format(segment_index)
        
        return xpath
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        批量更新配置
        
        Args:
            updates: 更新的配置字典
        """
        for key, value in updates.items():
            self.set(key, value)
        
        # 重新验证配置
        self._validate_config()
    
    def reset_to_default(self) -> None:
        """
        重置为默认配置
        """
        self.config = self._default_config.copy()
        self.save_config()
        print("配置已重置为默认值")
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            完整的配置字典
        """
        return self.config.copy()
    
    def print_config(self) -> None:
        """
        打印当前配置（用于调试）
        """
        print("当前配置:")
        print(json.dumps(self.config, indent=2, ensure_ascii=False))


# 全局配置管理器实例
_config_manager = None


def get_config_manager(config_path: str = "config.json") -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager


def get_config(key: str, default: Any = None) -> Any:
    """
    获取配置值的便捷函数
    
    Args:
        key: 配置键
        default: 默认值
        
    Returns:
        配置值
    """
    config_manager = get_config_manager()
    return config_manager.get(key, default)