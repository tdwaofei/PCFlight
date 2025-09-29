# -*- coding: utf-8 -*-
"""
航班数据爬虫系统 - OCR识别模块

本模块提供OCR图像识别功能：
- 验证码识别（4位字母）
- 时间图片识别（HH:MM格式）
- 图像预处理和优化
- 识别重试机制
- 多OCR引擎支持（Tesseract、PaddleOCR、ddddocr）
"""

import base64
import io
import re
import time
from typing import Optional, Tuple, Dict, Any, List
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

try:
    import ddddocr
    DDDDOCR_AVAILABLE = True
except ImportError:
    DDDDOCR_AVAILABLE = False
    ddddocr = None

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
        self.engine = config.get('engine', 'ddddocr')  # 默认使用ddddocr
        
        # 初始化OCR引擎
        self._init_ocr_engines()
        
        # 验证码识别配置
        self.captcha_pattern = re.compile(r'^[a-z]{4}$')  # 4位小写字母
        
        # 时间识别配置
        self.time_pattern = re.compile(r'^\d{1,2}:\d{2}$')  # HH:MM格式
    
    def _init_ocr_engines(self) -> None:
        """
        初始化OCR引擎
        """
        self.tesseract_available = TESSERACT_AVAILABLE
        self.paddleocr_available = False
        self.ddddocr_available = False
        self.paddle_ocr = None
        self.dddd_ocr = None
        
        # 初始化ddddocr引擎
        if DDDDOCR_AVAILABLE:
            try:
                self.dddd_ocr = ddddocr.DdddOcr(show_ad=False)
                self.ddddocr_available = True
                if self.logger:
                    self.logger.info("ddddocr引擎初始化成功")
            except Exception as e:
                self.ddddocr_available = False
                self.dddd_ocr = None
                if self.logger:
                    self.logger.warning(f"ddddocr初始化失败: {e}")
        
        # 如果ddddocr可用，优先使用ddddocr
        if self.ddddocr_available:
            self.engine = 'ddddocr'
        
        # 初始化PaddleOCR引擎
        if self.engine == 'paddleocr' and PADDLEOCR_AVAILABLE:
            try:
                self.paddle_ocr = PaddleOCR(
                    use_angle_cls=True, 
                    lang='en',
                    show_log=False,
                    use_gpu=False
                )
                test_image = np.ones((30, 100, 3), dtype=np.uint8) * 255
                result = self.paddle_ocr.ocr(test_image, cls=True)
                self.paddleocr_available = True
                if self.logger:
                    self.logger.info("PaddleOCR引擎初始化成功")
            except Exception as e:
                self.paddleocr_available = False
                self.paddle_ocr = None
                if self.logger:
                    self.logger.warning(f"PaddleOCR初始化失败，将使用Tesseract: {e}")
                self.engine = 'tesseract'
        
        if self.engine == 'tesseract' and not TESSERACT_AVAILABLE:
            if self.logger:
                self.logger.error("Tesseract不可用，请安装pytesseract")
            raise RuntimeError("OCR引擎不可用")
        
        if self.logger:
            self.logger.info(f"使用OCR引擎: {self.engine}")
            self.logger.info(f"ddddocr可用: {self.ddddocr_available}")
            self.logger.info(f"PaddleOCR可用: {self.paddleocr_available}")
            self.logger.info(f"Tesseract可用: {self.tesseract_available}")

    def recognize_captcha(self, image_element: WebElement, max_attempts: int = 3) -> Optional[str]:
        """
        识别验证码图片（使用ddddocr优先，保留预处理优化）
        
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
                
                # 方法1: 直接使用ddddocr识别原始图片
                if self.ddddocr_available:
                    result1 = self._ddddocr_recognize(image_data, 'captcha')
                    if result1 and len(result1) >= 3 and len(result1) <= 6:  # 接受3-6位验证码
                        if self.logger:
                            self.logger.info(f"ddddocr直接识别成功: {result1}")
                        return result1
                
                # 方法2: 使用预处理后的图片进行ddddocr识别
                if self.ddddocr_available:
                    preprocessing_methods = [
                        ("灰度放大锐化", self._preprocess_captcha_image_method1),
                        ("保守预处理", self._preprocess_captcha_image_method2),
                        ("激进预处理", self._preprocess_captcha_image_method3)
                    ]
                    
                    for method_name, preprocess_method in preprocessing_methods:
                        try:
                            # 预处理图片
                            processed_image = preprocess_method(image_data)
                            
                            # 转换为字节数据
                            buffer = io.BytesIO()
                            processed_image.save(buffer, format='PNG')
                            processed_data = buffer.getvalue()
                            
                            # 使用ddddocr识别
                            result = self._ddddocr_recognize(processed_data, 'captcha')
                            if result and len(result) >= 3 and len(result) <= 6:  # 接受3-6位验证码
                                if self.logger:
                                    self.logger.info(f"ddddocr {method_name} 识别成功: {result}")
                                return result
                                
                        except Exception as e:
                            if self.logger:
                                self.logger.warning(f"ddddocr {method_name} 识别失败: {str(e)}")
                            continue
                
                # 方法3: 如果ddddocr不可用，使用传统OCR方法作为备用
                if not self.ddddocr_available:
                    # 使用增强版识别（综合多种技术）
                    result3 = self._enhanced_captcha_recognize(image_data)
                    if result3 and len(result3) == 4:
                        if self.logger:
                            self.logger.info(f"传统OCR识别成功: {result3}")
                        return result3
                
                # 等待一段时间后重试
                if attempt < max_attempts:
                    time.sleep(0.5)
                    
            except Exception as e:
                if self.logger:
                    log_exception('ocr_processor', 'recognize_captcha', e, 
                                {'attempt': attempt, 'max_attempts': max_attempts})
                if attempt < max_attempts:
                    time.sleep(1)
                continue
        
        if self.logger:
            self.logger.error(f"验证码识别失败，已尝试 {max_attempts} 次")
        return None

    def _ddddocr_recognize(self, image_data: bytes, image_type: str = 'captcha') -> Optional[str]:
        """
        使用ddddocr进行识别
        
        Args:
            image_data: 图片二进制数据
            image_type: 图片类型 ('captcha' 或 'time')
            
        Returns:
            识别结果
        """
        if not self.ddddocr_available or self.dddd_ocr is None:
            return None
            
        try:
            # 根据图片类型设置字符范围
            if image_type == 'captcha':
                # 验证码使用小写英文a-z + 大写英文A-Z + 整数0-9
                self.dddd_ocr.set_ranges(3)
            elif image_type == 'time':
                # 时间识别使用数字+冒号
                self.dddd_ocr.set_ranges(5)
            else:
                # 默认使用小写英文a-z + 大写英文A-Z + 整数0-9
                self.dddd_ocr.set_ranges(6)
            
            # 使用概率模式进行识别
            result = self.dddd_ocr.classification(image_data, probability=True)
            
            if 'probability' in result and 'charsets' in result:
                probabilities = result['probability']
                charsets = result['charsets']
                
                # 智能提取字符
                if image_type == 'captcha':
                    # 验证码模式：提取4个最可能的字符
                    return self._extract_captcha_from_probability(probabilities, charsets)
                elif image_type == 'time':
                    # 时间模式：提取时间格式
                    return self._extract_time_from_probability(probabilities, charsets)
                else:
                    # 默认模式
                    return self._extract_captcha_from_probability(probabilities, charsets)
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"ddddocr识别失败: {str(e)}")
            return None
    
    def _extract_captcha_from_probability(self, probabilities: List, charsets: List) -> Optional[str]:
        """
        从概率结果中提取验证码字符
        
        Args:
            probabilities: 概率列表
            charsets: 字符集
            
        Returns:
            提取的验证码字符串
        """
        try:
            # 找出置信度最高的字符位置
            char_candidates = []
            for i, prob_list in enumerate(probabilities):
                if prob_list:
                    max_prob = max(prob_list)
                    max_idx = prob_list.index(max_prob)
                    char = charsets[max_idx]
                    if char.strip() and max_prob > 0.005:  # 非空字符且置信度足够
                        char_candidates.append((i, char, max_prob))
            
            # 按置信度排序，取前4个
            char_candidates.sort(key=lambda x: x[2], reverse=True)
            top4 = char_candidates[:4]
            
            # 按位置排序
            top4.sort(key=lambda x: x[0])
            
            result = ''.join([char for _, char, _ in top4])
            
            # 如果结果长度为4且都是字母，返回小写形式
            if len(result) == 4 and result.isalpha():
                return result.lower()
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"验证码字符提取失败: {str(e)}")
            return None
    
    def _extract_time_from_probability(self, probabilities: List, charsets: List) -> Optional[str]:
        """
        从概率结果中提取时间字符
        
        Args:
            probabilities: 概率列表
            charsets: 字符集
            
        Returns:
            提取的时间字符串
        """
        try:
            if self.logger:
                self.logger.info(f"开始从概率结果提取时间字符，概率位置数: {len(probabilities)}")
                self.logger.info(f"字符集: {charsets}")
            
            # 提取所有有意义的字符
            chars = []
            for i, prob_list in enumerate(probabilities):
                if prob_list:
                    max_prob = max(prob_list)
                    max_idx = prob_list.index(max_prob)
                    char = charsets[max_idx]
                    
                    if self.logger:
                        self.logger.info(f"位置{i+1}: 字符='{char}', 置信度={max_prob:.3f}")
                    
                    if char.strip() and max_prob > 0.01:  # 非空字符且置信度足够
                        chars.append(char)
                        if self.logger:
                            self.logger.info(f"位置{i+1}: 字符'{char}'被接受（置信度: {max_prob:.3f}）")
                    else:
                        if self.logger:
                            self.logger.warning(f"位置{i+1}: 字符'{char}'被拒绝（置信度: {max_prob:.3f}，阈值: 0.01）")
            
            result = ''.join(chars)
            
            if self.logger:
                self.logger.info(f"提取的字符序列: '{result}'")
            
            # 直接返回提取的字符序列，不进行格式验证
            if result:
                if self.logger:
                    self.logger.info(f"时间字符提取成功: '{result}'")
                return result
            else:
                if self.logger:
                    self.logger.warning(f"时间字符提取为空")
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"时间字符提取异常: {str(e)}")
                log_exception('ocr_processor', '_extract_time_from_probability', e, 
                            {'probabilities_count': len(probabilities) if probabilities else 0})
            return None

    def _preprocess_captcha_image_method1(self, image_data: bytes) -> Image.Image:
        """
        验证码预处理方法1：灰度+放大+锐化（针对lxzd类型优化）
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            预处理后的PIL图片对象
        """
        try:
            # 加载图片
            image = Image.open(io.BytesIO(image_data))
            
            # 转换为灰度图
            if image.mode != 'L':
                image = image.convert('L')
            
            # 大幅放大图片（提高到12倍）
            scale_factor = 12
            new_size = (image.width * scale_factor, image.height * scale_factor)
            image = image.resize(new_size, Image.LANCZOS)
            
            # 高斯模糊去噪
            image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
            
            # CLAHE对比度增强
            img_array = np.array(image)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            img_array = clahe.apply(img_array)
            image = Image.fromarray(img_array)
            
            # 多种阈值方法，选择最佳结果
            # OTSU阈值
            img_array = np.array(image)
            _, otsu_thresh = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 自适应阈值
            adaptive_thresh = cv2.adaptiveThreshold(img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # 固定阈值
            _, fixed_thresh = cv2.threshold(img_array, 127, 255, cv2.THRESH_BINARY)
            
            # 根据黑色像素比例选择最佳阈值方法
            otsu_black_ratio = np.sum(otsu_thresh == 0) / otsu_thresh.size
            adaptive_black_ratio = np.sum(adaptive_thresh == 0) / adaptive_thresh.size
            fixed_black_ratio = np.sum(fixed_thresh == 0) / fixed_thresh.size
            
            # 选择黑色像素比例在0.1-0.4之间的方法
            if 0.1 <= otsu_black_ratio <= 0.4:
                final_thresh = otsu_thresh
            elif 0.1 <= adaptive_black_ratio <= 0.4:
                final_thresh = adaptive_thresh
            elif 0.1 <= fixed_black_ratio <= 0.4:
                final_thresh = fixed_thresh
            else:
                # 如果都不理想，选择最接近0.25的
                ratios = [otsu_black_ratio, adaptive_black_ratio, fixed_black_ratio]
                thresholds = [otsu_thresh, adaptive_thresh, fixed_thresh]
                best_idx = min(range(len(ratios)), key=lambda i: abs(ratios[i] - 0.25))
                final_thresh = thresholds[best_idx]
            
            image = Image.fromarray(final_thresh)
            
            # 形态学操作优化字符形状
            img_array = np.array(image)
            kernel = np.ones((2,2), np.uint8)
            
            # 闭运算：填充字符内部的小洞
            img_array = cv2.morphologyEx(img_array, cv2.MORPH_CLOSE, kernel)
            
            # 开运算：去除小噪点
            img_array = cv2.morphologyEx(img_array, cv2.MORPH_OPEN, kernel)
            
            image = Image.fromarray(img_array)
            
            return image
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"验证码预处理方法1失败: {str(e)}")
            # 返回原始图片
            return Image.open(io.BytesIO(image_data))

    def _preprocess_captcha_image_method2(self, image_data: bytes) -> Image.Image:
        """
        验证码预处理方法2：保守预处理
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            if image.mode != 'L':
                image = image.convert('L')
            
            # 适度放大
            scale_factor = 3
            new_size = (image.width * scale_factor, image.height * scale_factor)
            image = image.resize(new_size, Image.LANCZOS)
            
            # 简单二值化
            img_array = np.array(image)
            _, thresh = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return Image.fromarray(thresh)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"验证码预处理方法2失败: {str(e)}")
            return Image.open(io.BytesIO(image_data))

    def _preprocess_captcha_image_method3(self, image_data: bytes) -> Image.Image:
        """
        验证码预处理方法3：激进预处理
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            if image.mode != 'L':
                image = image.convert('L')
            
            # 大幅放大
            scale_factor = 8
            new_size = (image.width * scale_factor, image.height * scale_factor)
            image = image.resize(new_size, Image.LANCZOS)
            
            # 强化对比度
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # 锐化
            image = image.filter(ImageFilter.SHARPEN)
            
            # 二值化
            img_array = np.array(image)
            _, thresh = cv2.threshold(img_array, 127, 255, cv2.THRESH_BINARY)
            
            return Image.fromarray(thresh)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"验证码预处理方法3失败: {str(e)}")
            return Image.open(io.BytesIO(image_data))

    def _enhanced_captcha_recognize(self, image_data: bytes) -> Optional[str]:
        """
        增强版验证码识别（传统OCR方法的备用方案）
        """
        if not TESSERACT_AVAILABLE:
            return None
            
        try:
            # 使用方法1预处理
            processed_image = self._preprocess_captcha_image_method1(image_data)
            
            # Tesseract识别
            config = '--psm 8 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz'
            result = pytesseract.image_to_string(processed_image, config=config).strip()
            
            if result and len(result) >= 3:
                return result.lower()
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"增强版验证码识别失败: {str(e)}")
            return None

    def _get_image_data(self, image_element: WebElement) -> Optional[bytes]:
        """
        从WebElement获取图片数据
        
        Args:
            image_element: Selenium图片元素
            
        Returns:
            图片二进制数据
        """
        try:
            # 获取图片的base64数据
            screenshot = image_element.screenshot_as_base64
            
            # 解码base64数据
            image_data = base64.b64decode(screenshot)
            
            return image_data
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"获取图片数据失败: {str(e)}")
            return None


    def recognize_time_image(self, image_element: WebElement, max_attempts: int = 3, flight_number: str = "", segment_index: int = 0, time_type: str = "time") -> Optional[str]:
        """
        识别时间图片（带重试机制）
        
        Args:
            image_element: Selenium获取的时间图片元素
            max_attempts: 最大重试次数
            flight_number: 航班号
            segment_index: 航段索引
            time_type: 时间类型 (departure/arrival)
            
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
                    if self.logger:
                        self.logger.error(f"获取时间图片数据失败，尝试 {attempt}/{max_attempts}")
                    continue
                
                # 保存时间图片到本地（无论识别成功与否）
                self._save_time_image_to_file(image_data, attempt, flight_number, segment_index, time_type)
                
                if self.logger:
                    self.logger.info(f"时间图片数据获取成功，大小: {len(image_data)} 字节")
                
                # 使用ddddocr识别时间图片
                if self.ddddocr_available:
                    if self.logger:
                        self.logger.info("开始使用ddddocr识别时间图片")
                    
                    result = self._ddddocr_recognize(image_data, 'time')
                    
                    if self.logger:
                        self.logger.info(f"ddddocr原始识别结果: '{result}'")
                    
                    if result:
                        # 清理和验证结果
                        cleaned_result = self._clean_time_result(result)
                        
                        if self.logger:
                            self.logger.info(f"时间结果清理: 原始='{result}' -> 清理后='{cleaned_result}'")
                        
                        if cleaned_result:
                            if self.logger:
                                self.logger.info(f"时间图片识别成功: {cleaned_result}")
                            return cleaned_result
                        else:
                            if self.logger:
                                self.logger.warning(f"时间结果清理失败，原始结果: '{result}'")
                    else:
                        if self.logger:
                            self.logger.warning("ddddocr识别返回空结果")
                
                # 如果ddddocr不可用，使用传统OCR方法
                if not self.ddddocr_available and TESSERACT_AVAILABLE:
                    if self.logger:
                        self.logger.info("ddddocr不可用，尝试使用Tesseract识别")
                    
                    # 预处理图片
                    processed_image = self._preprocess_time_image(image_data)
                    
                    # Tesseract识别
                    config = '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789:'
                    result = pytesseract.image_to_string(processed_image, config=config).strip()
                    
                    if self.logger:
                        self.logger.info(f"Tesseract识别结果: '{result}'")
                    
                    if result:
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

    def _save_time_image_to_file(self, image_data: bytes, attempt: int, flight_number: str = "", segment_index: int = 0, time_type: str = "time") -> None:
        """
        保存时间图片到本地文件
        
        Args:
            image_data: 图片二进制数据
            attempt: 尝试次数
            flight_number: 航班号
            segment_index: 航段索引
            time_type: 时间类型 (departure/arrival)
        """
        try:
            import os
            from datetime import datetime
            
            # 确保timeimage目录存在
            time_dir = os.path.join("output", "timeimage")
            if not os.path.exists(time_dir):
                os.makedirs(time_dir)
            
            # 生成文件名，包含航班号、航段索引、时间类型等信息
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 包含毫秒
            if flight_number and segment_index > 0:
                filename = f"{time_type}_{flight_number}_seg{segment_index}_{timestamp}_attempt{attempt}.png"
            else:
                filename = f"{time_type}_image_{timestamp}_attempt{attempt}.png"
            filepath = os.path.join(time_dir, filename)
            
            # 保存图片
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            if self.logger:
                self.logger.info(f"时间图片已保存: {filepath}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"保存时间图片失败: {str(e)}")

    def _preprocess_time_image(self, image_data: bytes) -> Image.Image:
        """
        时间图片预处理
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            预处理后的PIL图片对象
        """
        try:
            # 加载图片
            image = Image.open(io.BytesIO(image_data))
            
            # 转换为灰度图
            if image.mode != 'L':
                image = image.convert('L')
            
            # 放大图片
            scale_factor = 3
            new_size = (image.width * scale_factor, image.height * scale_factor)
            image = image.resize(new_size, Image.LANCZOS)
            
            # 增强对比度
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # 二值化
            img_array = np.array(image)
            _, thresh = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return Image.fromarray(thresh)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"时间图片预处理失败: {str(e)}")
            # 返回原始图片
            return Image.open(io.BytesIO(image_data))

    def _clean_time_result(self, result: str) -> Optional[str]:
        """
        清理时间识别结果
        
        Args:
            result: 原始识别结果
            
        Returns:
            清理后的时间字符串（HH:MM格式）
        """
        if self.logger:
            self.logger.info(f"开始清理时间识别结果: '{result}'")
        
        if not result:
            if self.logger:
                self.logger.warning("时间识别结果为空")
            return None
        
        # 移除空白字符
        cleaned = result.strip()
        
        if self.logger:
            self.logger.info(f"移除空白字符后: '{cleaned}'")
        
        # 首先尝试匹配标准时间格式 HH:MM 或 H:MM
        time_pattern = re.compile(r'(\d{1,2}):(\d{2})')
        match = time_pattern.search(cleaned)
        
        if match:
            hour, minute = match.groups()
            # 确保小时是两位数
            hour = hour.zfill(2)
            final_result = f"{hour}:{minute}"
            
            if self.logger:
                self.logger.info(f"标准时间格式匹配成功: 小时='{hour}', 分钟='{minute}', 最终结果='{final_result}'")
            
            return final_result
        
        # 如果没有冒号，尝试匹配4位数字格式 HHMM
        four_digit_pattern = re.compile(r'^(\d{4})$')
        match = four_digit_pattern.search(cleaned)
        
        if match:
            digits = match.group(1)
            hour = digits[:2]
            minute = digits[2:]
            final_result = f"{hour}:{minute}"
            
            if self.logger:
                self.logger.info(f"4位数字格式匹配成功: 原始='{digits}', 小时='{hour}', 分钟='{minute}', 最终结果='{final_result}'")
            
            return final_result
        
        # 如果都不匹配，记录警告
        if self.logger:
            self.logger.warning(f"时间格式匹配失败: '{cleaned}' (支持格式: HH:MM 或 HHMM)")
        
        return None


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


# 便捷函数
def recognize_captcha(image_element: WebElement, max_attempts: int = 3) -> Optional[str]:
    """
    识别验证码图片的便捷函数
    
    Args:
        image_element: Selenium获取的图片元素
        max_attempts: 最大重试次数
        
    Returns:
        识别出的验证码，失败返回None
    """
    processor = OCRProcessor()
    return processor.recognize_captcha(image_element, max_attempts)


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


def recognize_time_image(image_element: WebElement, max_attempts: int = 3) -> Optional[str]:
    """
    识别时间图片的便捷函数
    
    Args:
        image_element: Selenium获取的时间图片元素
        max_attempts: 最大重试次数
        
    Returns:
        HH:MM格式的时间字符串，失败返回None
    """
    processor = OCRProcessor()
    return processor.recognize_time_image(image_element, max_attempts)