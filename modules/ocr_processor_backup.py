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
        self.paddleocr_available = False  # 默认设为False，成功初始化后再设为True
        self.ddddocr_available = False    # 默认设为False，成功初始化后再设为True
        self.paddle_ocr = None
        self.dddd_ocr = None
        
        # 初始化ddddocr引擎
        if self.engine == 'ddddocr' and DDDDOCR_AVAILABLE:
            try:
                self.dddd_ocr = ddddocr.DdddOcr(show_ad=False)
                self.ddddocr_available = True
                if self.logger:
                    self.logger.info("ddddocr引擎初始化成功")
            except Exception as e:
                self.ddddocr_available = False
                self.dddd_ocr = None
                if self.logger:
                    self.logger.warning(f"ddddocr初始化失败，将使用Tesseract: {e}")
                self.engine = 'tesseract'
        
        # 初始化PaddleOCR引擎
        if self.engine == 'paddleocr' and PADDLEOCR_AVAILABLE:
            try:
                # 使用更稳定的初始化参数
                self.paddle_ocr = PaddleOCR(
                    use_angle_cls=True, 
                    lang='en',
                    show_log=False,
                    use_gpu=False,  # 强制使用CPU避免GPU相关问题
                    det_model_dir=None,  # 使用默认模型
                    rec_model_dir=None,  # 使用默认模型
                    cls_model_dir=None   # 使用默认模型
                )
                # 测试PaddleOCR是否可用
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
                    if result1 and len(result1) == 4:
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
                            if result and len(result) == 4:
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
                            result = self._tesseract_recognize_alternative(processed_image)
                            if result:
                                ocr_results.append(result)
                        
                        # 收集有效结果
                        for ocr_result in ocr_results:
                            cleaned = self._clean_captcha_result(ocr_result)
                            if cleaned and len(cleaned) == 4:
                                all_results.append(cleaned)
                                if self.logger:
                                    self.logger.debug(f"预处理方法{i+1}识别结果: {cleaned}")
                                    
                    except Exception as e:
                        if self.logger:
                            self.logger.debug(f"预处理方法{i+1}失败: {e}")
                        continue
                
                # 从所有结果中选择最佳结果
                if all_results:
                    best_result = self._select_best_captcha_result(all_results)
                    if best_result:
                        if self.logger:
                            self.logger.info(f"验证码识别成功: {best_result}")
                        return best_result
                
                if self.logger:
                    self.logger.warning(f"验证码识别失败，尝试 {attempt}/{max_attempts}")
                
                # 重试前等待
                if attempt < max_attempts:
                    time.sleep(1.0)  # 增加等待时间
                    
            except Exception as e:
                if self.logger:
                    log_exception('ocr_processor', 'recognize_captcha', e, 
                                {'attempt': attempt, 'max_attempts': max_attempts})
                
                if attempt < max_attempts:
                    time.sleep(1.0)
        
        if self.logger:
            self.logger.error(f"验证码识别失败，已尝试 {max_attempts} 次")
        return None
    
    def _tesseract_recognize_enhanced(self, image: Image.Image) -> Optional[str]:
        """
        使用增强配置的Tesseract进行验证码识别（针对lxzd类型优化）
        
        Args:
            image: 图片对象
            
        Returns:
            识别结果
        """
        try:
            # 多种PSM模式尝试，针对lxzd类型优化
            configs = [
                '--psm 8 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz',  # 单词模式
                '--psm 7 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz',  # 单行文本
                '--psm 6 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz',  # 统一文本块
                '--psm 13 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz', # 原始行
            ]
            
            results = []
            for config in configs:
                try:
                    result = pytesseract.image_to_string(image, config=config).strip()
                    if result and len(result) >= 3:
                        results.append(result)
                except:
                    continue
            
            # 如果有结果，优先选择4个字符的结果
            if results:
                # 按长度排序，优先选择4个字符的结果
                four_char_results = [r for r in results if len(r) == 4]
                if four_char_results:
                    return four_char_results[0]
                else:
                    # 如果没有4个字符的结果，返回最长的
                    results.sort(key=len, reverse=True)
                    return results[0]
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Tesseract增强配置识别失败: {str(e)}")
            return None
    
    def _tesseract_recognize_alternative(self, image: Image.Image) -> Optional[str]:
        """
        使用备用配置的Tesseract进行验证码识别（混合大小写）
        
        Args:
            image: 图片对象
            
        Returns:
            识别结果
        """
        # 尝试不同的PSM模式和字符集
        configs = [
            '--psm 7 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz',  # 小写字母
            '--psm 13 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', # 混合大小写
            '--psm 6 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz',   # 小写字母
            '--psm 8 --oem 1 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz'    # 使用旧引擎
        ]
        
        for config in configs:
            try:
                result = pytesseract.image_to_string(image, config=config).strip()
                if result and len(result) >= 3:  # 至少识别出3个字符
                    return result
            except:
                continue
        
        return None
    
    def _select_best_captcha_result(self, results: list) -> Optional[str]:
        """
        从多个OCR结果中选择最佳的验证码结果（优化版）
        
        Args:
            results: OCR识别结果列表
            
        Returns:
            最佳结果
        """
        if not results:
            return None
        
        # 清理所有结果
        cleaned_results = []
        for result in results:
            cleaned = self._clean_captcha_result(result)
            if cleaned and len(cleaned) == 4:  # 只接受4位字符的结果
                cleaned_results.append(cleaned)
        
        if not cleaned_results:
            return None
        
        # 如果只有一个有效结果，直接返回
        if len(cleaned_results) == 1:
            return cleaned_results[0]
        
        # 统计每个结果的出现频率
        from collections import Counter
        result_counts = Counter(cleaned_results)
        
        # 如果有结果出现多次，返回最频繁的
        most_common = result_counts.most_common(1)
        if most_common and most_common[0][1] > 1:
            return most_common[0][0]
        
        # 如果所有结果都只出现一次，选择最可能正确的
        # 优先选择全小写字母的结果
        lowercase_results = [r for r in cleaned_results if r.islower()]
        if lowercase_results:
            return lowercase_results[0]
        
        # 否则返回第一个结果
        return cleaned_results[0]
    
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
                
                # 转换为字节数据供OCR识别
                buffer = io.BytesIO()
                processed_image.save(buffer, format='PNG')
                processed_data = buffer.getvalue()
                
                # OCR识别
                result = self._perform_ocr(processed_data, 'time')
                
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
    

    
    def _segment_characters(self, image: Image.Image) -> List[Image.Image]:
        """
        字符分割技术 - 使用垂直投影分析分割字符
        
        Args:
            image: 预处理后的二值化图片
            
        Returns:
            分割后的字符图片列表
        """
        try:
            # 转换为numpy数组
            img_array = np.array(image)
            
            # 确保是二值图像
            if len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # 二值化处理
            _, binary = cv2.threshold(img_array, 127, 255, cv2.THRESH_BINARY)
            
            # 垂直投影分析
            height, width = binary.shape
            vertical_projection = np.sum(binary == 0, axis=0)  # 统计每列的黑色像素数
            
            # 寻找字符边界
            char_boundaries = []
            in_char = False
            start_col = 0
            
            # 设置阈值，过滤噪声
            threshold = max(1, height * 0.1)  # 至少10%的高度有黑色像素才认为是字符
            
            for col in range(width):
                if vertical_projection[col] > threshold:
                    if not in_char:
                        start_col = col
                        in_char = True
                else:
                    if in_char:
                        char_boundaries.append((start_col, col))
                        in_char = False
            
            # 处理最后一个字符
            if in_char:
                char_boundaries.append((start_col, width))
            
            # 分割字符
            char_images = []
            for start, end in char_boundaries:
                # 确保字符宽度合理
                char_width = end - start
                if char_width < 5:  # 过窄的可能是噪声
                    continue
                if char_width > width * 0.8:  # 过宽的可能是整个图片
                    continue
                
                # 提取字符区域
                char_region = binary[:, start:end]
                
                # 垂直方向去除空白
                row_projection = np.sum(char_region == 0, axis=1)
                non_empty_rows = np.where(row_projection > 0)[0]
                
                if len(non_empty_rows) > 0:
                    top = non_empty_rows[0]
                    bottom = non_empty_rows[-1] + 1
                    char_region = char_region[top:bottom, :]
                    
                    # 转换回PIL图像
                    char_image = Image.fromarray(char_region)
                    
                    # 调整字符大小以便识别
                    char_height, char_width = char_region.shape
                    if char_height < 20 or char_width < 10:
                        # 放大小字符
                        scale = max(2, 30 // max(char_height, char_width))
                        new_size = (char_width * scale, char_height * scale)
                        char_image = char_image.resize(new_size, Image.LANCZOS)
                    
                    char_images.append(char_image)
            
            # 如果分割失败，返回原图
            if len(char_images) == 0:
                return [image]
            
            # 限制字符数量（验证码通常是4位）
            if len(char_images) > 6:
                # 选择最大的4个字符
                char_sizes = [(img.width * img.height, img) for img in char_images]
                char_sizes.sort(reverse=True)
                char_images = [img for _, img in char_sizes[:4]]
            
            return char_images
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"字符分割失败: {str(e)}")
            return [image]  # 分割失败时返回原图
    
    def _recognize_single_character(self, char_image: Image.Image) -> str:
        """
        单字符识别 - 针对分割后的单个字符进行识别
        
        Args:
            char_image: 单个字符的图片
            
        Returns:
            识别出的字符
        """
        try:
            # 多种OCR配置尝试
            results = []
            
            if TESSERACT_AVAILABLE:
                # 配置1: 单字符模式
                config1 = '--psm 10 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz'
                result1 = pytesseract.image_to_string(char_image, config=config1).strip()
                if result1 and len(result1) == 1 and result1.isalpha():
                    results.append(result1.lower())
                
                # 配置2: 单词模式
                config2 = '--psm 8 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz'
                result2 = pytesseract.image_to_string(char_image, config=config2).strip()
                if result2 and len(result2) == 1 and result2.isalpha():
                    results.append(result2.lower())
                
                # 配置3: 默认模式
                config3 = '--psm 6 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz'
                result3 = pytesseract.image_to_string(char_image, config=config3).strip()
                if result3 and len(result3) >= 1 and result3[0].isalpha():
                    results.append(result3[0].lower())
            
            # 返回最常见的结果
            if results:
                from collections import Counter
                counter = Counter(results)
                return counter.most_common(1)[0][0]
            
            return '?'  # 识别失败
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"单字符识别失败: {str(e)}")
            return '?'
    
    def _advanced_preprocess_captcha(self, image: Image.Image) -> Image.Image:
        """
        高级验证码预处理 - 使用多种先进的图像处理技术
        
        Args:
            image: 原始图片
            
        Returns:
            处理后的图片
        """
        # 转换为numpy数组进行处理
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image)
        
        # 1. 超分辨率放大 - 使用双三次插值
        height, width = img_array.shape[:2]
        scale_factor = 8  # 大幅放大
        new_height, new_width = height * scale_factor, width * scale_factor
        img_array = cv2.resize(img_array, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # 2. 色彩空间转换 - 使用LAB色彩空间进行更精确的处理
        lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        
        # 3. 自适应直方图均衡化 - 增强对比度
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_channel = clahe.apply(l_channel)
        
        # 4. 高级降噪 - 非局部均值去噪
        l_channel = cv2.fastNlMeansDenoising(l_channel, None, 10, 7, 21)
        
        # 5. 边缘保持滤波 - 双边滤波
        l_channel = cv2.bilateralFilter(l_channel, 9, 75, 75)
        
        # 6. 多阈值二值化组合
        # 方法1: OTSU自动阈值
        _, otsu_binary = cv2.threshold(l_channel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 方法2: 自适应阈值
        adaptive_binary = cv2.adaptiveThreshold(
            l_channel, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 2
        )
        
        # 方法3: 基于均值的动态阈值
        mean_val = np.mean(l_channel)
        dynamic_thresh = int(mean_val * 0.7)
        _, dynamic_binary = cv2.threshold(l_channel, dynamic_thresh, 255, cv2.THRESH_BINARY)
        
        # 7. 多阈值结果融合
        # 使用投票机制选择最佳像素值
        combined = np.zeros_like(otsu_binary)
        vote_sum = otsu_binary.astype(np.int32) + adaptive_binary.astype(np.int32) + dynamic_binary.astype(np.int32)
        combined[vote_sum >= 2 * 255] = 255  # 至少两种方法认为是白色
        
        # 8. 形态学操作 - 精细调整
        # 使用椭圆形核，更适合字符形状
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_close)
        
        # 去除小噪点
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 1))
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_open)
        
        return Image.fromarray(combined)
    
    def _preprocess_captcha_image_method1(self, image_data: bytes) -> Image.Image:
        """
        验证码预处理方法1 - 针对lxzd类型优化
        
        Args:
            image_data: 原始图片数据
            
        Returns:
            处理后的图片
        """
        # 加载图片
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为灰度图
        if image.mode != 'L':
            image = image.convert('L')
        
        # 转换为numpy数组进行处理
        img_array = np.array(image)
        
        # 1. 大幅放大图片（12倍）以增强细节
        height, width = img_array.shape
        img_array = cv2.resize(img_array, (width * 12, height * 12), interpolation=cv2.INTER_CUBIC)
        
        # 2. 高斯模糊去噪
        img_array = cv2.GaussianBlur(img_array, (3, 3), 0)
        
        # 3. 对比度增强
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        img_array = clahe.apply(img_array)
        
        # 4. 多种阈值方法组合
        # OTSU阈值
        _, otsu_thresh = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 自适应阈值
        adaptive_thresh = cv2.adaptiveThreshold(img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                               cv2.THRESH_BINARY, 11, 2)
        
        # 固定阈值（针对lxzd类型调整）
        _, fixed_thresh = cv2.threshold(img_array, 140, 255, cv2.THRESH_BINARY)
        
        # 选择最佳阈值结果（基于黑色像素比例）
        otsu_ratio = np.sum(otsu_thresh == 0) / otsu_thresh.size
        adaptive_ratio = np.sum(adaptive_thresh == 0) / adaptive_thresh.size
        fixed_ratio = np.sum(fixed_thresh == 0) / fixed_thresh.size
        
        # 选择黑色像素比例在合理范围内的结果
        if 0.15 <= otsu_ratio <= 0.35:
            img_array = otsu_thresh
        elif 0.15 <= adaptive_ratio <= 0.35:
            img_array = adaptive_thresh
        elif 0.15 <= fixed_ratio <= 0.35:
            img_array = fixed_thresh
        else:
            # 如果都不在理想范围，选择最接近0.25的
            ratios = [otsu_ratio, adaptive_ratio, fixed_ratio]
            methods = [otsu_thresh, adaptive_thresh, fixed_thresh]
            best_idx = min(range(len(ratios)), key=lambda i: abs(ratios[i] - 0.25))
            img_array = methods[best_idx]
        
        # 5. 形态学操作优化字符形状
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        img_array = cv2.morphologyEx(img_array, cv2.MORPH_CLOSE, kernel)  # 连接断裂
        img_array = cv2.morphologyEx(img_array, cv2.MORPH_OPEN, kernel)   # 去除噪声
        
        # 转换回PIL图片
        return Image.fromarray(img_array)
    
    def _template_matching_recognize(self, image: Image.Image) -> Optional[str]:
        """
        模板匹配识别 - 基于预定义字符模板进行匹配
        
        Args:
            image: 原始验证码图片
            
        Returns:
            匹配结果
        """
        try:
            # 简单的基于形状特征的字符识别
            # 预处理图片
            img_array = np.array(image.convert('L'))
            
            # 二值化
            _, binary = cv2.threshold(img_array, 127, 255, cv2.THRESH_BINARY)
            
            # 寻找轮廓
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if len(contours) < 3:  # 至少需要3个字符轮廓
                return None
            
            # 按x坐标排序轮廓（从左到右）
            contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])
            
            # 简单的字符识别逻辑（基于轮廓特征）
            recognized_chars = []
            for contour in contours[:4]:  # 最多4个字符
                # 计算轮廓特征
                area = cv2.contourArea(contour)
                if area < 50:  # 过滤小轮廓
                    continue
                
                # 获取边界矩形
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                
                # 基于简单特征进行字符推测（这里只是示例）
                if aspect_ratio > 0.8:
                    recognized_chars.append('o')  # 宽字符可能是o
                elif aspect_ratio < 0.4:
                    recognized_chars.append('i')  # 窄字符可能是i
                else:
                    recognized_chars.append('a')  # 默认字符
            
            if len(recognized_chars) >= 3:
                result = ''.join(recognized_chars[:4])
                return result.lower()
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"模板匹配识别失败: {str(e)}")
            return None
    
    def _segment_characters(self, image: Image.Image) -> List[Image.Image]:
        img_array = np.array(image)
        
        # 1. 垂直投影分析
        vertical_projection = np.sum(img_array == 0, axis=0)  # 黑色像素投影
        
        # 2. 寻找字符边界
        char_boundaries = []
        in_char = False
        start_pos = 0
        
        # 设置阈值，避免噪声干扰
        threshold = max(3, np.max(vertical_projection) * 0.1)
        
        for i, projection in enumerate(vertical_projection):
            if projection > threshold and not in_char:
                # 字符开始
                start_pos = i
                in_char = True
            elif projection <= threshold and in_char:
                # 字符结束
                char_boundaries.append((start_pos, i))
                in_char = False
        
        # 处理最后一个字符
        if in_char:
            char_boundaries.append((start_pos, len(vertical_projection)))
        
        # 3. 提取字符
        characters = []
        for start, end in char_boundaries:
            # 添加一些边距
            margin = 2
            start = max(0, start - margin)
            end = min(img_array.shape[1], end + margin)
            
            char_img = img_array[:, start:end]
            
            # 过滤太小的片段（可能是噪声）
            if char_img.shape[1] > 5:
                characters.append(Image.fromarray(char_img))
        
        return characters
    
    def _recognize_single_character(self, char_image: Image.Image) -> str:
        """
        识别单个字符
        
        Args:
            char_image: 单个字符图片
            
        Returns:
            识别结果
        """
        # 配置专门用于单字符识别
        config = '--psm 10 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz'
        
        try:
            result = pytesseract.image_to_string(char_image, config=config).strip()
            # 清理结果
            cleaned = re.sub(r'[^a-zA-Z]', '', result.lower())
            return cleaned[0] if cleaned else ''
        except:
            return ''
    
    def _template_matching_recognize(self, image: Image.Image) -> Optional[str]:
        """
        模板匹配识别 - 作为OCR的补充方案
        
        Args:
            image: 预处理后的验证码图片
            
        Returns:
            识别结果
        """
        # 这里可以实现基于模板匹配的识别
        # 由于需要预先准备字符模板，暂时返回None
        # 在实际应用中，可以收集常见字符的模板进行匹配
        return None
    
    def _enhanced_captcha_recognize(self, image_data: bytes) -> Optional[str]:
        """
        增强版验证码识别 - 综合多种技术
        
        Args:
            image_data: 图片数据
            
        Returns:
            识别结果
        """
        try:
            # 加载图片
            image = Image.open(io.BytesIO(image_data))
            
            # 方法1: 高级预处理 + 整体识别
            processed_img1 = self._advanced_preprocess_captcha(image)
            result1 = self._tesseract_recognize_enhanced(processed_img1)
            
            # 方法2: 字符分割 + 单字符识别
            processed_img2 = self._advanced_preprocess_captcha(image)
            characters = self._segment_characters(processed_img2)
            
            if len(characters) == 4:  # 期望4个字符
                char_results = []
                for char_img in characters:
                    char_result = self._recognize_single_character(char_img)
                    char_results.append(char_result)
                
                result2 = ''.join(char_results) if all(char_results) else None
            else:
                result2 = None
            
            # 方法3: 模板匹配（如果实现了）
            result3 = self._template_matching_recognize(processed_img1)
            
            # 收集所有有效结果
            results = []
            for result in [result1, result2, result3]:
                if result and len(result) == 4 and result.isalpha():
                    results.append(result.lower())
            
            # 选择最佳结果
            if results:
                # 如果有多个结果，选择最常见的
                from collections import Counter
                counter = Counter(results)
                return counter.most_common(1)[0][0]
            
            return None
            
        except Exception as e:
            if self.logger:
                log_exception('ocr_processor', '_enhanced_captcha_recognize', e)
            return None
    
    def _preprocess_captcha_image_method2(self, image_data: bytes) -> Image.Image:
        """
        验证码预处理方法2 - 激进处理
        
        Args:
            image_data: 原始图片数据
            
        Returns:
            处理后的图片
        """
        # 加载图片
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为灰度图
        if image.mode != 'L':
            image = image.convert('L')
        
        # 大幅放大图片
        scale_factor = 8
        new_size = (image.width * scale_factor, image.height * scale_factor)
        image = image.resize(new_size, Image.LANCZOS)
        
        # 转换为numpy数组进行OpenCV处理
        img_array = np.array(image)
        
        # 高斯模糊
        img_array = cv2.GaussianBlur(img_array, (3, 3), 0)
        
        # 自适应阈值二值化
        img_array = cv2.adaptiveThreshold(img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY, 11, 2)
        
        # 形态学操作 - 开运算去噪
        kernel = np.ones((2, 2), np.uint8)
        img_array = cv2.morphologyEx(img_array, cv2.MORPH_OPEN, kernel)
        
        # 转换回PIL图片
        return Image.fromarray(img_array)
    
    def _preprocess_captcha_image_method3(self, image_data: bytes) -> Image.Image:
        """
        验证码预处理方法3 - 保守处理
        
        Args:
            image_data: 原始图片数据
            
        Returns:
            处理后的图片
        """
        # 加载图片
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为灰度图
        if image.mode != 'L':
            image = image.convert('L')
        
        # 适度放大
        scale_factor = 4
        new_size = (image.width * scale_factor, image.height * scale_factor)
        image = image.resize(new_size, Image.LANCZOS)
        
        # 增强对比度
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # 转换为numpy数组
        img_array = np.array(image)
        
        # OTSU阈值二值化
        _, img_array = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 转换回PIL图片
        return Image.fromarray(img_array)
    
    def _preprocess_captcha_image(self, image_data: bytes) -> Image.Image:
        """
        预处理验证码图片（针对4位字母验证码优化）
        
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
        scale_factor = max(4, 120 // min(width, height))  # 动态缩放，确保最小尺寸至少120px
        image = image.resize((width * scale_factor, height * scale_factor), Image.LANCZOS)
        
        # 转换为numpy数组进行高级处理
        img_array = np.array(image)
        
        # 使用OpenCV进行颜色空间转换和预处理
        # 转换为HSV色彩空间，更好地分离颜色和亮度
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        
        # 提取亮度通道
        gray = hsv[:, :, 2]
        
        # 使用自适应直方图均衡化增强对比度
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # 使用多种阈值方法进行二值化
        # 方法1: OTSU自动阈值
        _, binary1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 方法2: 自适应阈值
        binary2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)
        
        # 方法3: 固定阈值
        _, binary3 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # 选择最佳二值化结果（选择前景像素数量适中的）
        binary_options = [binary1, binary2, binary3]
        foreground_counts = [np.sum(b == 0) for b in binary_options]  # 黑色像素数量
        total_pixels = gray.shape[0] * gray.shape[1]
        
        # 选择前景像素占比在10%-40%之间的结果
        best_binary = binary1
        for i, count in enumerate(foreground_counts):
            ratio = count / total_pixels
            if 0.1 <= ratio <= 0.4:
                best_binary = binary_options[i]
                break
        
        # 形态学操作去除噪声
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        best_binary = cv2.morphologyEx(best_binary, cv2.MORPH_CLOSE, kernel)
        best_binary = cv2.morphologyEx(best_binary, cv2.MORPH_OPEN, kernel)
        
        # 转换回PIL图像
        image = Image.fromarray(best_binary)
        
        return image
    
    def _preprocess_captcha_image(self, image_data: bytes) -> Image.Image:
        """
        预处理验证码图片（针对4位字母验证码优化）
        
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
        scale_factor = max(4, 120 // min(width, height))  # 动态缩放，确保最小尺寸至少120px
        image = image.resize((width * scale_factor, height * scale_factor), Image.LANCZOS)
        
        # 转换为numpy数组进行高级处理
        img_array = np.array(image)
        
        # 使用OpenCV进行颜色空间转换和预处理
        # 转换为HSV色彩空间，更好地分离颜色和亮度
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        
        # 提取亮度通道
        gray = hsv[:, :, 2]
        
        # 使用自适应直方图均衡化增强对比度
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # 使用多种阈值方法进行二值化
        # 方法1: OTSU自动阈值
        _, binary1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 方法2: 自适应阈值
        binary2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)
        
        # 方法3: 固定阈值
        _, binary3 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # 选择最佳二值化结果（选择前景像素数量适中的）
        binary_options = [binary1, binary2, binary3]
        foreground_counts = [np.sum(b == 0) for b in binary_options]  # 黑色像素数量
        total_pixels = gray.shape[0] * gray.shape[1]
        
        # 选择前景像素占比在10%-40%之间的结果
        best_binary = binary1
        for i, count in enumerate(foreground_counts):
            ratio = count / total_pixels
            if 0.1 <= ratio <= 0.4:
                best_binary = binary_options[i]
                break
        
        # 形态学操作去除噪声
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        best_binary = cv2.morphologyEx(best_binary, cv2.MORPH_CLOSE, kernel)
        best_binary = cv2.morphologyEx(best_binary, cv2.MORPH_OPEN, kernel)
        
        # 转换回PIL图像
        image = Image.fromarray(best_binary)
        
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
        
        # 放大图片（提高识别精度）
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
    
    def _perform_ocr(self, image_data: bytes, image_type: str) -> Optional[str]:
        """
        执行OCR识别（优先使用ddddocr）
        
        Args:
            image_data: 图片二进制数据
            image_type: 图片类型（'captcha' 或 'time'）
            
        Returns:
            识别结果字符串
        """
        results = []
        
        try:
            # 优先使用ddddocr引擎
            if self.engine == 'ddddocr' and self.ddddocr_available:
                result = self._ddddocr_recognize(image_data, image_type)
                if result:
                    return result
            
            # 如果ddddocr失败或不可用，使用其他引擎作为备用
            # 转换为PIL Image对象供其他引擎使用
            image = Image.open(io.BytesIO(image_data))
            
            if image_type == 'captcha':
                # 验证码识别：尝试多种方法
                
                # 方法1: Tesseract增强配置
                if TESSERACT_AVAILABLE:
                    result1 = self._tesseract_recognize_enhanced(image)
                    if result1:
                        results.append(result1)
                
                # 方法2: PaddleOCR
                if self.paddleocr_available and self.paddle_ocr:
                    result2 = self._paddleocr_recognize(image)
                    if result2:
                        results.append(result2)
                
                # 方法3: Tesseract备用配置
                if TESSERACT_AVAILABLE:
                    result3 = self._tesseract_recognize_alternative(image)
                    if result3:
                        results.append(result3)
                        
            else:
                # 时间识别：按引擎优先级
                if self.engine == 'paddleocr' and self.paddleocr_available:
                    return self._paddleocr_recognize(image)
                elif self.engine == 'tesseract' and TESSERACT_AVAILABLE:
                    return self._tesseract_recognize(image, image_type)
                elif TESSERACT_AVAILABLE:
                    return self._tesseract_recognize(image, image_type)
            
            # 对于验证码，选择最可能正确的结果
            if results and image_type == 'captcha':
                return self._select_best_captcha_result(results)
            
            return results[0] if results else None
                
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
        if not self.paddleocr_available or self.paddle_ocr is None:
            return None
            
        try:
            # 转换PIL图片为numpy数组
            img_array = np.array(image)
            
            # 确保图片是RGB格式
            if len(img_array.shape) == 2:  # 灰度图
                img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
            elif img_array.shape[2] == 4:  # RGBA
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
            
            # 执行OCR
            results = self.paddle_ocr.ocr(img_array, cls=True)
            
            if results and results[0]:
                # 提取文本内容
                texts = []
                for line in results[0]:
                    if line and len(line) > 1:
                        text = line[1][0]  # 获取识别的文字
                        confidence = line[1][1]  # 获取置信度
                        if confidence > 0.5:  # 只保留置信度较高的结果
                            texts.append(text)
                
                return ' '.join(texts).strip() if texts else None
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"PaddleOCR识别失败: {str(e)}")
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
                # 验证码使用小写+大写英文字母
                self.dddd_ocr.set_ranges(3)
            elif image_type == 'time':
                # 时间识别使用数字
                self.dddd_ocr.set_ranges(0)
            else:
                # 默认使用小写+大写英文字母
                self.dddd_ocr.set_ranges(3)
            
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
            # 提取所有有意义的字符
            chars = []
            for i, prob_list in enumerate(probabilities):
                if prob_list:
                    max_prob = max(prob_list)
                    max_idx = prob_list.index(max_prob)
                    char = charsets[max_idx]
                    if char.strip() and max_prob > 0.01:  # 非空字符且置信度足够
                        chars.append(char)
            
            result = ''.join(chars)
            
            # 验证时间格式
            if re.match(r'^\d{1,2}:\d{2}$', result):
                return result
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"时间字符提取失败: {str(e)}")
            return None
    
    def _clean_captcha_result(self, result: str) -> Optional[str]:
        """
        清理验证码识别结果（针对lxzd类型优化）
        
        Args:
            result: 原始识别结果
            
        Returns:
            清理后的结果
        """
        if not result:
            return None
        
        # 保持原始大小写，只移除空格和特殊字符
        cleaned = re.sub(r'[^A-Za-z0-9]', '', result)
        
        # 针对lxzd类型的字符混淆修正
        char_corrections = {
            # 数字到字母的转换
            '0': 'o', '1': 'l', '2': 'z', '3': 'e', '4': 'a', 
            '5': 's', '6': 'g', '7': 't', '8': 'b', '9': 'g',
            # 大写到小写
            'O': 'o', 'I': 'l', 'S': 's', 'G': 'g', 'B': 'b',
            'U': 'u', 'C': 'c', 'Z': 'z', 'V': 'v', 'D': 'd',
            'F': 'f', 'P': 'p', 'R': 'r', 'E': 'e', 'X': 'x',
            'L': 'l', 'J': 'j', 'Y': 'y', 'A': 'a', 'T': 't',
            'H': 'h', 'K': 'k', 'M': 'm', 'N': 'n', 'Q': 'q',
            'W': 'w',
            # 特殊混淆修正
            'i': 'l',  # i容易被误识别为l
            'q': 'g',  # q容易被误识别为g
            'cl': 'd', # cl组合容易被误识别为d
            'rn': 'm', # rn组合容易被误识别为m
            'vv': 'w', # vv组合容易被误识别为w
        }
        
        # 先处理组合字符
        for old_combo, new_char in [('cl', 'd'), ('rn', 'm'), ('vv', 'w')]:
            cleaned = cleaned.replace(old_combo, new_char)
        
        # 应用单字符修正
        corrected = ''
        for char in cleaned:
            corrected += char_corrections.get(char, char.lower())
        
        # 验证格式（4位字母）
        if len(corrected) == 4 and corrected.isalpha():
            return corrected
        
        # 如果长度不对，尝试提取4个字母
        letters_only = re.sub(r'[^a-zA-Z]', '', corrected)
        if len(letters_only) >= 4:
            return letters_only[:4].lower()
        elif len(letters_only) == 3:
            # 如果只有3个字母，可能是识别遗漏，不补充
            return None
        
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