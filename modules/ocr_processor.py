# -*- coding: utf-8 -*-
"""
航班数据爬虫系统 - OCR识别模块

本模块提供OCR图像识别功能：
- 验证码识别（4位字母）
- 时间图片识别（HH:MM格式）
- 图像预处理和优化
- 识别重试机制
- 多OCR引擎支持
"""

import base64
import io
import re
import time
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
from selenium.webdriver.remote.webelement import WebElement

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    PaddleOCR = None

from .logger import get_logger, log_exception
from .config_manager import get_config_manager


class OCRProcessor:
    """
    OCR识别处理器
    
    提供验证码和时间图片的OCR识别功能
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化OCR处理器
        
        Args:
            config: OCR配置字典
        """
        self.logger = get_logger()
        
        if config is None:
            config_manager = get_config_manager()
            config = config_manager.get_ocr_config()
        
        self.config = config
        self.engine = config.get('engine', 'tesseract')
        
        # 初始化OCR引擎
        self._init_ocr_engines()
        
        # 验证码识别配置
        self.captcha_pattern = re.compile(r'^[A-Z]{4}$')  # 4位大写字母
        
        # 时间识别配置
        self.time_pattern = re.compile(r'^\d{1,2}:\d{2}$')  # HH:MM格式
    
    def _init_ocr_engines(self) -> None:
        """
        初始化OCR引擎
        """
        self.tesseract_available = TESSERACT_AVAILABLE
        self.paddleocr_available = PADDLEOCR_AVAILABLE
        self.paddle_ocr = None
        
        if self.engine == 'paddleocr' and PADDLEOCR_AVAILABLE:
            try:
                self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
                if self.logger:
                    self.logger.info("PaddleOCR引擎初始化成功")
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"PaddleOCR初始化失败，将使用Tesseract: {e}")
                self.engine = 'tesseract'
        
        if self.engine == 'tesseract' and not TESSERACT_AVAILABLE:
            if self.logger:
                self.logger.error("Tesseract不可用，请安装pytesseract")
            raise RuntimeError("OCR引擎不可用")
        
        if self.logger:
            self.logger.info(f"使用OCR引擎: {self.engine}")
    
    def recognize_captcha(self, image_element: WebElement, max_attempts: int = 3) -> Optional[str]:
        """
        识别验证码图片（带重试机制）
        
        Args:
            image_element: Selenium获取的图片元素
            max_attempts: 最大重试次数
            
        Returns:
            识别出的4位字母验证码，失败返回None
        """
        for attempt in range(1, max_attempts + 1):
            try:
                if self.logger:
                    self.logger.info(f"验证码识别尝试 {attempt}/{max_attempts}")
                
                # 获取图片数据
                image_data = self._get_image_data(image_element)
                if not image_data:
                    continue
                
                # 预处理图片
                processed_image = self._preprocess_captcha_image(image_data)
                
                # OCR识别
                result = self._perform_ocr(processed_image, 'captcha')
                
                if result:
                    # 清理和验证结果
                    cleaned_result = self._clean_captcha_result(result)
                    if cleaned_result:
                        if self.logger:
                            self.logger.info(f"验证码识别成功: {cleaned_result}")
                        return cleaned_result
                
                if self.logger:
                    self.logger.warning(f"验证码识别失败，尝试 {attempt}/{max_attempts}")
                
                # 重试前等待
                if attempt < max_attempts:
                    time.sleep(0.5)
                    
            except Exception as e:
                if self.logger:
                    log_exception('ocr_processor', 'recognize_captcha', e, 
                                {'attempt': attempt, 'max_attempts': max_attempts})
                
                if attempt < max_attempts:
                    time.sleep(0.5)
        
        if self.logger:
            self.logger.error(f"验证码识别失败，已尝试 {max_attempts} 次")
        return None
    
    def recognize_time_image(self, image_element: WebElement, max_attempts: int = 3) -> Optional[str]:
        """
        识别时间图片（带重试机制）
        
        Args:
            image_element: Selenium获取的时间图片元素
            max_attempts: 最大重试次数
            
        Returns:
            HH:MM格式的时间字符串，失败返回None
        """
        for attempt in range(1, max_attempts + 1):
            try:
                if self.logger:
                    self.logger.info(f"时间图片识别尝试 {attempt}/{max_attempts}")
                
                # 获取图片数据
                image_data = self._get_image_data(image_element)
                if not image_data:
                    continue
                
                # 预处理图片
                processed_image = self._preprocess_time_image(image_data)
                
                # OCR识别
                result = self._perform_ocr(processed_image, 'time')
                
                if result:
                    # 清理和验证结果
                    cleaned_result = self._clean_time_result(result)
                    if cleaned_result:
                        if self.logger:
                            self.logger.info(f"时间图片识别成功: {cleaned_result}")
                        return cleaned_result
                
                if self.logger:
                    self.logger.warning(f"时间图片识别失败，尝试 {attempt}/{max_attempts}")
                
                # 重试前等待
                if attempt < max_attempts:
                    time.sleep(0.5)
                    
            except Exception as e:
                if self.logger:
                    log_exception('ocr_processor', 'recognize_time_image', e, 
                                {'attempt': attempt, 'max_attempts': max_attempts})
                
                if attempt < max_attempts:
                    time.sleep(0.5)
        
        if self.logger:
            self.logger.error(f"时间图片识别失败，已尝试 {max_attempts} 次")
        return None
    
    def _get_image_data(self, image_element: WebElement) -> Optional[bytes]:
        """
        从WebElement获取图片数据
        
        Args:
            image_element: 图片元素
            
        Returns:
            图片二进制数据
        """
        try:
            # 获取图片的base64数据
            image_base64 = image_element.screenshot_as_base64
            if image_base64:
                return base64.b64decode(image_base64)
            
            # 备用方法：获取图片的PNG数据
            return image_element.screenshot_as_png
            
        except Exception as e:
            if self.logger:
                log_exception('ocr_processor', '_get_image_data', e)
            return None
    
    def _preprocess_captcha_image(self, image_data: bytes) -> Image.Image:
        """
        预处理验证码图片
        
        Args:
            image_data: 原始图片数据
            
        Returns:
            预处理后的PIL图片对象
        """
        # 加载图片
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为RGB模式
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 放大图片（提高识别精度）
        width, height = image.size
        image = image.resize((width * 3, height * 3), Image.LANCZOS)
        
        # 转换为灰度图
        image = image.convert('L')
        
        # 增强对比度
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # 二值化处理
        image = image.point(lambda x: 0 if x < 128 else 255, '1')
        
        # 降噪处理
        image = image.filter(ImageFilter.MedianFilter())
        
        return image
    
    def _preprocess_time_image(self, image_data: bytes) -> Image.Image:
        """
        预处理时间图片
        
        Args:
            image_data: 原始图片数据
            
        Returns:
            预处理后的PIL图片对象
        """
        # 加载图片
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为RGB模式
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 放大图片
        width, height = image.size
        image = image.resize((width * 4, height * 4), Image.LANCZOS)
        
        # 转换为灰度图
        image = image.convert('L')
        
        # 增强锐度
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # 增强对比度
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # 二值化处理（使用自适应阈值）
        img_array = np.array(image)
        binary = cv2.adaptiveThreshold(img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
        image = Image.fromarray(binary)
        
        return image
    
    def _perform_ocr(self, image: Image.Image, image_type: str) -> Optional[str]:
        """
        执行OCR识别
        
        Args:
            image: 预处理后的图片
            image_type: 图片类型（'captcha' 或 'time'）
            
        Returns:
            识别结果字符串
        """
        try:
            if self.engine == 'paddleocr' and self.paddle_ocr:
                return self._paddleocr_recognize(image)
            elif self.engine == 'tesseract' and TESSERACT_AVAILABLE:
                return self._tesseract_recognize(image, image_type)
            else:
                if self.logger:
                    self.logger.error(f"OCR引擎不可用: {self.engine}")
                return None
                
        except Exception as e:
            if self.logger:
                log_exception('ocr_processor', '_perform_ocr', e, 
                            {'engine': self.engine, 'image_type': image_type})
            return None
    
    def _tesseract_recognize(self, image: Image.Image, image_type: str) -> Optional[str]:
        """
        使用Tesseract进行OCR识别
        
        Args:
            image: 图片对象
            image_type: 图片类型
            
        Returns:
            识别结果
        """
        if image_type == 'captcha':
            config = self.config.get('config', '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        else:  # time
            config = self.config.get('time_image_config', '--psm 8 -c tessedit_char_whitelist=0123456789:')
        
        result = pytesseract.image_to_string(image, config=config).strip()
        return result if result else None
    
    def _paddleocr_recognize(self, image: Image.Image) -> Optional[str]:
        """
        使用PaddleOCR进行识别
        
        Args:
            image: 图片对象
            
        Returns:
            识别结果
        """
        # 转换PIL图片为numpy数组
        img_array = np.array(image)
        
        # 执行OCR
        results = self.paddle_ocr.ocr(img_array, cls=True)
        
        if results and results[0]:
            # 提取文本内容
            texts = []
            for line in results[0]:
                if line and len(line) > 1:
                    texts.append(line[1][0])
            
            return ' '.join(texts).strip() if texts else None
        
        return None
    
    def _clean_captcha_result(self, result: str) -> Optional[str]:
        """
        清理验证码识别结果
        
        Args:
            result: 原始识别结果
            
        Returns:
            清理后的结果
        """
        if not result:
            return None
        
        # 转换为大写并移除空格和特殊字符
        cleaned = re.sub(r'[^A-Z]', '', result.upper())
        
        # 验证格式（4位字母）
        if self.captcha_pattern.match(cleaned):
            return cleaned
        
        # 尝试修复常见识别错误
        if len(cleaned) == 4 and cleaned.isalpha():
            return cleaned
        
        return None
    
    def _clean_time_result(self, result: str) -> Optional[str]:
        """
        清理时间识别结果
        
        Args:
            result: 原始识别结果
            
        Returns:
            清理后的HH:MM格式时间
        """
        if not result:
            return None
        
        # 移除空格和其他字符，只保留数字和冒号
        cleaned = re.sub(r'[^0-9:]', '', result)
        
        # 验证基本格式
        if ':' not in cleaned:
            return None
        
        # 尝试解析时间
        parts = cleaned.split(':')
        if len(parts) != 2:
            return None
        
        try:
            hour = int(parts[0])
            minute = int(parts[1])
            
            # 验证时间范围
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}"
        except ValueError:
            pass
        
        return None
    
    def save_image_for_debug(self, image_data: bytes, filename: str) -> None:
        """
        保存图片用于调试
        
        Args:
            image_data: 图片数据
            filename: 文件名
        """
        try:
            import os
            debug_dir = 'debug_images'
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            
            with open(os.path.join(debug_dir, filename), 'wb') as f:
                f.write(image_data)
                
            if self.logger:
                self.logger.debug(f"调试图片已保存: {filename}")
                
        except Exception as e:
            if self.logger:
                log_exception('ocr_processor', 'save_image_for_debug', e)
    
    def get_image_as_base64(self, image_element: WebElement) -> Optional[str]:
        """
        获取图片的base64编码（用于保存到Excel）
        
        Args:
            image_element: 图片元素
            
        Returns:
            base64编码的图片字符串
        """
        try:
            image_data = self._get_image_data(image_element)
            if image_data:
                return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            if self.logger:
                log_exception('ocr_processor', 'get_image_as_base64', e)
        
        return None
    
    def test_ocr_engines(self) -> Dict[str, bool]:
        """
        测试OCR引擎可用性
        
        Returns:
            引擎可用性字典
        """
        results = {
            'tesseract': TESSERACT_AVAILABLE,
            'paddleocr': PADDLEOCR_AVAILABLE and self.paddle_ocr is not None
        }
        
        if self.logger:
            self.logger.info(f"OCR引擎可用性: {results}")
        
        return results


# 便捷函数
def recognize_captcha(image_element: WebElement, max_attempts: int = 3) -> Optional[str]:
    """
    识别验证码的便捷函数
    
    Args:
        image_element: 图片元素
        max_attempts: 最大重试次数
        
    Returns:
        识别结果
    """
    processor = OCRProcessor()
    return processor.recognize_captcha(image_element, max_attempts)


def recognize_time_image(image_element: WebElement, max_attempts: int = 3) -> Optional[str]:
    """
    识别时间图片的便捷函数
    
    Args:
        image_element: 图片元素
        max_attempts: 最大重试次数
        
    Returns:
        识别结果
    """
    processor = OCRProcessor()
    return processor.recognize_time_image(image_element, max_attempts)


def get_image_as_base64(image_element: WebElement) -> Optional[str]:
    """
    获取图片base64编码的便捷函数
    
    Args:
        image_element: 图片元素
        
    Returns:
        base64编码字符串
    """
    processor = OCRProcessor()
    return processor.get_image_as_base64(image_element)