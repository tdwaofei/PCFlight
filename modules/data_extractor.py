# -*- coding: utf-8 -*-
"""
航班数据爬虫系统 - 数据提取模块

本模块提供航班数据的提取和解析功能：
- 航段数据识别和循环处理
- 文本信息提取
- 时间图片识别（带重试机制）
- 数据结构化和验证
- 图片保存功能
"""

import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from .logger import get_logger, log_exception, log_flight_process
from .config_manager import get_config_manager
from .ocr_processor import OCRProcessor, get_image_as_base64


class DataExtractor:
    """
    数据提取器
    
    负责从查询结果页面提取航班数据
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据提取器
        
        Args:
            config: 配置字典
        """
        self.logger = get_logger()
        
        if config is None:
            config_manager = get_config_manager()
            self.xpath_config = config_manager.get_xpath_config()
            self.retry_config = config_manager.get_retry_config()
            self.output_config = config_manager.get_output_config()
        else:
            self.xpath_config = config.get('xpath', {})
            self.retry_config = config.get('retry', {})
            self.output_config = config.get('output', {})
        
        self.ocr_processor = OCRProcessor()
        self.max_time_image_retries = self.retry_config.get('time_image_max_attempts', 3)
    
    def extract_flight_segments(self, driver: WebDriver, flight_number: str, departure_date: str) -> List[Dict[str, Any]]:
        """
        提取页面中的所有航段数据
        
        Args:
            driver: Selenium WebDriver实例
            flight_number: 航班号
            departure_date: 出发日期
            
        Returns:
            航段信息列表，每个元素包含出发机场、到达机场等字段
        """
        try:
            log_flight_process(flight_number, "数据提取", "开始")
            
            # 检查是否有结果数据
            result_list_xpath = self.xpath_config.get('result_list')
            if not result_list_xpath:
                raise ValueError("未配置结果列表XPath")
            
            try:
                result_list = driver.find_element(By.XPATH, result_list_xpath)
            except NoSuchElementException:
                log_flight_process(flight_number, "数据提取", "失败", "未找到结果列表")
                return []
            
            # 检测航段数量
            segment_count = self._detect_segment_count(driver)
            
            if segment_count == 0:
                log_flight_process(flight_number, "数据提取", "失败", "未找到航段数据")
                return []
            
            log_flight_process(flight_number, "数据提取", "进行中", f"发现 {segment_count} 个航段")
            
            # 循环提取每个航段的数据
            segments = []
            for segment_index in range(1, segment_count + 1):
                segment_data = self._extract_single_segment(
                    driver, flight_number, departure_date, segment_index
                )
                
                if segment_data:
                    segments.append(segment_data)
                    log_flight_process(flight_number, "航段提取", "成功", 
                                     f"航段 {segment_index}: {segment_data.get('departure_airport', '')} -> {segment_data.get('arrival_airport', '')}")
                else:
                    log_flight_process(flight_number, "航段提取", "失败", f"航段 {segment_index}")
            
            log_flight_process(flight_number, "数据提取", "完成", f"成功提取 {len(segments)} 个航段")
            return segments
            
        except Exception as e:
            log_flight_process(flight_number, "数据提取", "异常", str(e))
            
            if self.logger:
                log_exception('data_extractor', 'extract_flight_segments', e, 
                            {'flight_number': flight_number, 'departure_date': departure_date})
            
            return []
    
    def _detect_segment_count(self, driver: WebDriver) -> int:
        """
        检测航段数量
        
        Args:
            driver: WebDriver实例
            
        Returns:
            航段数量
        """
        try:
            segment_base_xpath = self.xpath_config.get('segment_base', '')
            if not segment_base_xpath or '{}' not in segment_base_xpath:
                # 如果没有配置动态XPath，尝试检测
                result_list_xpath = self.xpath_config.get('result_list')
                result_list = driver.find_element(By.XPATH, result_list_xpath)
                
                # 查找所有可能的航段div
                segment_divs = result_list.find_elements(By.XPATH, './div')
                return len([div for div in segment_divs if div.text.strip()])
            
            # 使用动态XPath检测
            count = 0
            max_check = 10  # 最多检查10个航段
            
            for i in range(1, max_check + 1):
                xpath = segment_base_xpath.format(i)
                try:
                    element = driver.find_element(By.XPATH, xpath)
                    if element and element.text.strip():
                        count = i
                    else:
                        break
                except NoSuchElementException:
                    break
            
            return count
            
        except Exception as e:
            if self.logger:
                log_exception('data_extractor', '_detect_segment_count', e)
            return 0
    
    def _extract_single_segment(self, driver: WebDriver, flight_number: str, 
                               departure_date: str, segment_index: int) -> Optional[Dict[str, Any]]:
        """
        提取单个航段的数据
        
        Args:
            driver: WebDriver实例
            flight_number: 航班号
            departure_date: 出发日期
            segment_index: 航段索引（从1开始）
            
        Returns:
            航段数据字典
        """
        try:
            segment_data = {
                'flight_number': flight_number,
                'departure_date': departure_date,
                'segment_index': segment_index,
                'departure_airport': '',
                'arrival_airport': '',
                'scheduled_departure': '',
                'scheduled_arrival': '',
                'actual_departure': '',
                'actual_arrival': '',
                'flight_status': '',
                'created_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 提取出发机场
            departure_airport = self._extract_text_field(
                driver, 'departure_airport', segment_index
            )
            if departure_airport:
                segment_data['departure_airport'] = departure_airport
            
            # 提取到达机场
            arrival_airport = self._extract_text_field(
                driver, 'arrival_airport', segment_index
            )
            if arrival_airport:
                segment_data['arrival_airport'] = arrival_airport
            
            # 提取计划起飞时间
            scheduled_departure = self._extract_text_field(
                driver, 'scheduled_departure', segment_index
            )
            if scheduled_departure:
                segment_data['scheduled_departure'] = scheduled_departure
            
            # 提取计划到达时间
            scheduled_arrival = self._extract_text_field(
                driver, 'scheduled_arrival', segment_index
            )
            if scheduled_arrival:
                segment_data['scheduled_arrival'] = scheduled_arrival
            
            # 提取航班状态
            flight_status = self._extract_text_field(
                driver, 'flight_status', segment_index
            )
            if flight_status:
                segment_data['flight_status'] = flight_status
            
            # 提取实际起飞时间（图片识别）
            actual_departure = self._extract_time_image(
                driver, 'actual_departure_img', segment_index, '实际起飞时间'
            )
            segment_data['actual_departure'] = actual_departure
            
            # 提取实际到达时间（图片识别）
            actual_arrival = self._extract_time_image(
                driver, 'actual_arrival_img', segment_index, '实际到达时间'
            )
            segment_data['actual_arrival'] = actual_arrival
            
            return segment_data
            
        except Exception as e:
            if self.logger:
                log_exception('data_extractor', '_extract_single_segment', e, 
                            {'flight_number': flight_number, 'segment_index': segment_index})
            return None
    
    def _extract_text_field(self, driver: WebDriver, field_name: str, segment_index: int) -> str:
        """
        提取文本字段
        
        Args:
            driver: WebDriver实例
            field_name: 字段名称
            segment_index: 航段索引
            
        Returns:
            提取的文本内容
        """
        try:
            xpath_template = self.xpath_config.get(field_name, '')
            if not xpath_template:
                return ''
            
            # 如果XPath包含占位符，则格式化
            if '{}' in xpath_template:
                xpath = xpath_template.format(segment_index)
            else:
                xpath = xpath_template
            
            element = driver.find_element(By.XPATH, xpath)
            text = element.text.strip() if element else ''
            
            return text
            
        except NoSuchElementException:
            if self.logger:
                self.logger.warning(f"未找到字段 {field_name} 的元素，航段 {segment_index}")
            return ''
        except Exception as e:
            if self.logger:
                log_exception('data_extractor', '_extract_text_field', e, 
                            {'field_name': field_name, 'segment_index': segment_index})
            return ''
    
    def _extract_time_image(self, driver: WebDriver, field_name: str, 
                           segment_index: int, field_description: str) -> str:
        """
        提取时间图片并进行OCR识别（带重试机制）
        
        Args:
            driver: WebDriver实例
            field_name: 字段名称
            segment_index: 航段索引
            field_description: 字段描述（用于日志）
            
        Returns:
            识别的时间字符串或图片base64编码
        """
        try:
            xpath_template = self.xpath_config.get(field_name, '')
            if not xpath_template:
                return '识别失败'
            
            # 格式化XPath
            if '{}' in xpath_template:
                xpath = xpath_template.format(segment_index)
            else:
                xpath = xpath_template
            
            # 查找图片元素
            try:
                img_element = driver.find_element(By.XPATH, xpath)
            except NoSuchElementException:
                if self.logger:
                    self.logger.warning(f"未找到{field_description}图片元素，航段 {segment_index}")
                return '元素未找到'
            
            # 尝试OCR识别（带重试机制）
            for attempt in range(1, self.max_time_image_retries + 1):
                try:
                    if self.logger:
                        self.logger.info(f"{field_description}识别尝试 {attempt}/{self.max_time_image_retries}，航段 {segment_index}")
                    
                    # OCR识别
                    time_result = self.ocr_processor.recognize_time_image(
                        img_element, max_attempts=1
                    )
                    
                    if time_result:
                        if self.logger:
                            self.logger.info(f"{field_description}识别成功: {time_result}，航段 {segment_index}")
                        return time_result
                    
                    if self.logger:
                        self.logger.warning(f"{field_description}识别失败，尝试 {attempt}/{self.max_time_image_retries}，航段 {segment_index}")
                    
                    # 重试前等待
                    if attempt < self.max_time_image_retries:
                        time.sleep(0.5)
                        
                except Exception as e:
                    if self.logger:
                        log_exception('data_extractor', '_extract_time_image', e, 
                                    {'field_name': field_name, 'segment_index': segment_index, 'attempt': attempt})
                    
                    if attempt < self.max_time_image_retries:
                        time.sleep(0.5)
            
            # 所有重试都失败，保存原始图片
            if self.logger:
                self.logger.error(f"{field_description}识别失败，已尝试 {self.max_time_image_retries} 次，航段 {segment_index}")
            
            # 根据配置决定是否保存图片
            if self.output_config.get('save_images', True):
                return self._save_failed_image(img_element, field_description, segment_index)
            else:
                return '识别失败'
                
        except Exception as e:
            if self.logger:
                log_exception('data_extractor', '_extract_time_image', e, 
                            {'field_name': field_name, 'segment_index': segment_index})
            return '提取异常'
    
    def _save_failed_image(self, img_element, field_description: str, segment_index: int) -> str:
        """
        保存识别失败的图片
        
        Args:
            img_element: 图片元素
            field_description: 字段描述
            segment_index: 航段索引
            
        Returns:
            图片的base64编码或错误信息
        """
        try:
            image_format = self.output_config.get('image_format', 'base64')
            
            if image_format == 'base64':
                # 保存为base64编码
                base64_data = get_image_as_base64(img_element)
                if base64_data:
                    if self.logger:
                        self.logger.info(f"{field_description}图片已保存为base64，航段 {segment_index}")
                    return f"data:image/png;base64,{base64_data}"
                else:
                    return '图片保存失败'
            else:
                # 保存为文件（可以在这里实现文件保存逻辑）
                return '图片文件保存功能待实现'
                
        except Exception as e:
            if self.logger:
                log_exception('data_extractor', '_save_failed_image', e, 
                            {'field_description': field_description, 'segment_index': segment_index})
            return '图片保存异常'
    
    def validate_segment_data(self, segment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证航段数据的完整性
        
        Args:
            segment_data: 航段数据
            
        Returns:
            验证结果字典
        """
        validation_result = {
            'is_valid': True,
            'missing_fields': [],
            'warnings': []
        }
        
        # 必需字段检查
        required_fields = ['flight_number', 'departure_date', 'departure_airport', 'arrival_airport']
        for field in required_fields:
            if not segment_data.get(field):
                validation_result['missing_fields'].append(field)
                validation_result['is_valid'] = False
        
        # 可选字段检查（生成警告）
        optional_fields = ['scheduled_departure', 'scheduled_arrival', 'actual_departure', 'actual_arrival', 'flight_status']
        for field in optional_fields:
            if not segment_data.get(field) or segment_data.get(field) in ['识别失败', '元素未找到', '提取异常']:
                validation_result['warnings'].append(f"{field}字段缺失或识别失败")
        
        return validation_result
    
    def get_extraction_statistics(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取数据提取统计信息
        
        Args:
            segments: 航段数据列表
            
        Returns:
            统计信息字典
        """
        if not segments:
            return {
                'total_segments': 0,
                'valid_segments': 0,
                'success_rate': 0.0,
                'field_success_rates': {}
            }
        
        total_segments = len(segments)
        valid_segments = 0
        field_counts = {}
        field_success_counts = {}
        
        # 统计字段
        fields_to_check = ['departure_airport', 'arrival_airport', 'scheduled_departure', 
                          'scheduled_arrival', 'actual_departure', 'actual_arrival', 'flight_status']
        
        for field in fields_to_check:
            field_counts[field] = 0
            field_success_counts[field] = 0
        
        # 遍历所有航段
        for segment in segments:
            validation = self.validate_segment_data(segment)
            if validation['is_valid']:
                valid_segments += 1
            
            # 统计各字段成功率
            for field in fields_to_check:
                field_counts[field] += 1
                value = segment.get(field, '')
                if value and value not in ['识别失败', '元素未找到', '提取异常', '图片保存失败']:
                    field_success_counts[field] += 1
        
        # 计算成功率
        success_rate = (valid_segments / total_segments * 100) if total_segments > 0 else 0
        
        field_success_rates = {}
        for field in fields_to_check:
            if field_counts[field] > 0:
                field_success_rates[field] = field_success_counts[field] / field_counts[field] * 100
            else:
                field_success_rates[field] = 0
        
        return {
            'total_segments': total_segments,
            'valid_segments': valid_segments,
            'success_rate': round(success_rate, 2),
            'field_success_rates': {k: round(v, 2) for k, v in field_success_rates.items()}
        }


# 便捷函数
def extract_flight_segments(driver: WebDriver, flight_number: str, departure_date: str) -> List[Dict[str, Any]]:
    """
    提取航段数据的便捷函数
    
    Args:
        driver: WebDriver实例
        flight_number: 航班号
        departure_date: 出发日期
        
    Returns:
        航段数据列表
    """
    extractor = DataExtractor()
    return extractor.extract_flight_segments(driver, flight_number, departure_date)


def validate_segment_data(segment_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证航段数据的便捷函数
    
    Args:
        segment_data: 航段数据
        
    Returns:
        验证结果
    """
    extractor = DataExtractor()
    return extractor.validate_segment_data(segment_data)