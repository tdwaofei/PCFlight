# -*- coding: utf-8 -*-
"""
航班数据爬虫系统 - 网页自动化模块

本模块提供网页自动化操作功能：
- 浏览器启动和管理
- 页面导航和元素定位
- 表单填写和提交
- 验证码处理（带重试机制）
- 页面等待和状态检查
"""

import time
import json
from typing import Dict, Any, Optional, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    ElementClickInterceptedException, ElementNotInteractableException
)
from webdriver_manager.chrome import ChromeDriverManager

from .logger import get_logger, log_exception, log_flight_process
from .config_manager import get_config_manager
from .ocr_processor import OCRProcessor


class WebAutomation:
    """
    网页自动化控制器
    
    提供完整的网页自动化操作功能
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化网页自动化控制器
        
        Args:
            config: 浏览器配置字典
        """
        self.logger = get_logger()
        
        if config is None:
            config_manager = get_config_manager()
            self.browser_config = config_manager.get_browser_config()
            self.website_config = config_manager.get_website_config()
            self.xpath_config = config_manager.get_xpath_config()
            self.retry_config = config_manager.get_retry_config()
        else:
            self.browser_config = config.get('browser', {})
            self.website_config = config.get('website', {})
            self.xpath_config = config.get('xpath', {})
            self.retry_config = config.get('retry', {})
        
        self.driver = None
        self.wait = None
        self.ocr_processor = OCRProcessor()
        
        # 验证码重试统计
        self.captcha_retry_count = 0
        self.max_captcha_retries = self.retry_config.get('captcha_max_attempts', 6)
    
    def start_browser(self) -> bool:
        """
        启动浏览器
        
        Returns:
            是否启动成功
        """
        try:
            if self.logger:
                self.logger.info("正在启动Chrome浏览器...")
            
            # 配置Chrome选项
            chrome_options = Options()
            
            if self.browser_config.get('headless', False):
                chrome_options.add_argument('--headless')
            
            # 设置窗口大小
            window_size = self.browser_config.get('window_size', '1920,1080')
            chrome_options.add_argument(f'--window-size={window_size}')
            
            # 设置用户代理
            user_agent = self.browser_config.get('user_agent')
            if user_agent:
                chrome_options.add_argument(f'--user-agent={user_agent}')
            
            # 其他Chrome选项
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--ignore-certificate-errors')
            
            # 自动下载ChromeDriver
            service = Service(ChromeDriverManager().install())
            
            # 创建WebDriver实例
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 设置超时时间
            timeout = self.browser_config.get('timeout', 30)
            self.driver.set_page_load_timeout(self.browser_config.get('page_load_timeout', 60))
            self.driver.implicitly_wait(self.browser_config.get('implicit_wait', 10))
            
            # 创建WebDriverWait实例
            self.wait = WebDriverWait(self.driver, timeout)
            
            if self.logger:
                self.logger.info("Chrome浏览器启动成功")
            
            return True
            
        except Exception as e:
            if self.logger:
                log_exception('web_automation', 'start_browser', e)
            return False
    
    def stop_browser(self) -> None:
        """
        关闭浏览器
        """
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                self.wait = None
                
                if self.logger:
                    self.logger.info("浏览器已关闭")
                    
        except Exception as e:
            if self.logger:
                log_exception('web_automation', 'stop_browser', e)
    
    def navigate_to_flight_page(self) -> bool:
        """
        导航到航班查询页面
        
        Returns:
            是否导航成功
        """
        try:
            if not self.driver:
                raise RuntimeError("浏览器未启动")
            
            base_url = self.website_config.get('base_url', 'https://tool.133.cn/flight/')
            
            if self.logger:
                self.logger.info(f"正在访问航班查询页面: {base_url}")
            
            self.driver.get(base_url)
            
            # 等待页面加载完成
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            
            if self.logger:
                self.logger.info("航班查询页面加载成功")
            
            return True
            
        except Exception as e:
            if self.logger:
                log_exception('web_automation', 'navigate_to_flight_page', e)
            return False
    
    def click_flight_number_button(self) -> bool:
        """
        点击"按航班号"按钮
        
        Returns:
            是否点击成功
        """
        try:
            xpath = self.xpath_config.get('flight_number_button')
            if not xpath:
                raise ValueError("未配置航班号按钮XPath")
            
            if self.logger:
                self.logger.info("正在点击'按航班号'按钮")
            
            # 等待按钮可点击
            button = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            button.click()
            
            # 等待一下确保页面状态更新
            time.sleep(1)
            
            if self.logger:
                self.logger.info("'按航班号'按钮点击成功")
            
            return True
            
        except Exception as e:
            if self.logger:
                log_exception('web_automation', 'click_flight_number_button', e)
            return False
    
    def fill_flight_info(self, flight_number: str, departure_date: str) -> bool:
        """
        填写航班号和出发日期
        
        Args:
            flight_number: 航班号
            departure_date: 出发日期（YYYY-MM-DD格式）
            
        Returns:
            是否填写成功
        """
        try:
            if self.logger:
                self.logger.info(f"正在填写航班信息: {flight_number}, {departure_date}")
            
            # 填写航班号
            flight_input_xpath = self.xpath_config.get('flight_number_input')
            if flight_input_xpath:
                flight_input = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, flight_input_xpath))
                )
                flight_input.clear()
                flight_input.send_keys(flight_number)
                
                if self.logger:
                    self.logger.info(f"航班号填写成功: {flight_number}")
            
            # 填写出发日期
            date_input_xpath = self.xpath_config.get('departure_date_input')
            if date_input_xpath:
                date_input = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, date_input_xpath))
                )
                date_input.clear()
                date_input.send_keys(departure_date)
                
                if self.logger:
                    self.logger.info(f"出发日期填写成功: {departure_date}")
            
            return True
            
        except Exception as e:
            if self.logger:
                log_exception('web_automation', 'fill_flight_info', e, 
                            {'flight_number': flight_number, 'departure_date': departure_date})
            return False
    
    def handle_captcha(self, flight_number: str) -> bool:
        """
        处理验证码（带重试机制）
        
        Args:
            flight_number: 当前处理的航班号（用于日志）
            
        Returns:
            是否处理成功
        """
        self.captcha_retry_count = 0
        
        while self.captcha_retry_count < self.max_captcha_retries:
            try:
                self.captcha_retry_count += 1
                
                log_flight_process(flight_number, "验证码识别", "开始", 
                                 f"尝试 {self.captcha_retry_count}/{self.max_captcha_retries}")
                
                # 获取验证码图片元素
                captcha_img_xpath = self.xpath_config.get('captcha_image')
                if not captcha_img_xpath:
                    raise ValueError("未配置验证码图片XPath")
                
                captcha_img = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, captcha_img_xpath))
                )
                
                # OCR识别验证码
                captcha_text = self.ocr_processor.recognize_captcha(
                    captcha_img, max_attempts=1
                )
                
                if not captcha_text:
                    log_flight_process(flight_number, "验证码识别", "失败", "OCR识别失败")
                    
                    # 点击验证码刷新
                    if self._refresh_captcha():
                        time.sleep(self.retry_config.get('captcha_delay_seconds', 1))
                        continue
                    else:
                        break
                
                # 填写验证码
                captcha_input_xpath = self.xpath_config.get('captcha_input')
                if captcha_input_xpath:
                    captcha_input = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, captcha_input_xpath))
                    )
                    captcha_input.clear()
                    captcha_input.send_keys(captcha_text)
                    
                    log_flight_process(flight_number, "验证码识别", "成功", f"识别结果: {captcha_text}")
                    return True
                
            except Exception as e:
                log_flight_process(flight_number, "验证码识别", "异常", str(e))
                
                if self.logger:
                    log_exception('web_automation', 'handle_captcha', e, 
                                {'flight_number': flight_number, 'attempt': self.captcha_retry_count})
                
                # 尝试刷新验证码
                if self.captcha_retry_count < self.max_captcha_retries:
                    self._refresh_captcha()
                    time.sleep(self.retry_config.get('captcha_delay_seconds', 1))
        
        log_flight_process(flight_number, "验证码识别", "失败", 
                         f"已达到最大重试次数 {self.max_captcha_retries}")
        return False
    
    def _refresh_captcha(self) -> bool:
        """
        刷新验证码图片
        
        Returns:
            是否刷新成功
        """
        try:
            captcha_img_xpath = self.xpath_config.get('captcha_image')
            if captcha_img_xpath:
                captcha_img = self.driver.find_element(By.XPATH, captcha_img_xpath)
                captcha_img.click()
                
                # 等待图片刷新
                time.sleep(1)
                
                if self.logger:
                    self.logger.info("验证码图片已刷新")
                
                return True
                
        except Exception as e:
            if self.logger:
                log_exception('web_automation', '_refresh_captcha', e)
        
        return False
    
    def submit_query(self, flight_number: str) -> bool:
        """
        提交查询请求
        
        Args:
            flight_number: 航班号（用于日志）
            
        Returns:
            是否提交成功
        """
        try:
            query_button_xpath = self.xpath_config.get('query_button')
            if not query_button_xpath:
                raise ValueError("未配置查询按钮XPath")
            
            log_flight_process(flight_number, "提交查询", "开始")
            
            # 点击查询按钮
            query_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, query_button_xpath))
            )
            query_button.click()
            
            # 等待页面响应
            time.sleep(2)
            
            log_flight_process(flight_number, "提交查询", "成功")
            return True
            
        except Exception as e:
            log_flight_process(flight_number, "提交查询", "失败", str(e))
            
            if self.logger:
                log_exception('web_automation', 'submit_query', e, 
                            {'flight_number': flight_number})
            return False
    
    def check_query_response(self, flight_number: str) -> Dict[str, Any]:
        """
        检查查询响应，判断是否有验证码错误
        
        Args:
            flight_number: 航班号
            
        Returns:
            响应状态字典
        """
        try:
            # 等待页面加载
            time.sleep(3)
            
            # 检查是否有错误提示（验证码错误等）
            # 这里可以根据实际页面结构添加错误检测逻辑
            
            # 检查是否有结果数据
            result_list_xpath = self.xpath_config.get('result_list')
            if result_list_xpath:
                try:
                    result_list = self.driver.find_element(By.XPATH, result_list_xpath)
                    if result_list and result_list.text.strip():
                        log_flight_process(flight_number, "查询响应", "成功", "找到结果数据")
                        return {'status': 'success', 'has_data': True}
                except NoSuchElementException:
                    pass
            
            # 检查页面源码中是否包含验证码错误信息
            page_source = self.driver.page_source
            if '验证码错误' in page_source or 'status":1008' in page_source:
                log_flight_process(flight_number, "查询响应", "验证码错误")
                return {'status': 'captcha_error', 'has_data': False}
            
            # 检查是否没有找到航班信息
            if '没有找到' in page_source or '无航班信息' in page_source:
                log_flight_process(flight_number, "查询响应", "无数据")
                return {'status': 'no_data', 'has_data': False}
            
            log_flight_process(flight_number, "查询响应", "成功")
            return {'status': 'success', 'has_data': True}
            
        except Exception as e:
            log_flight_process(flight_number, "查询响应", "异常", str(e))
            
            if self.logger:
                log_exception('web_automation', 'check_query_response', e, 
                            {'flight_number': flight_number})
            
            return {'status': 'error', 'has_data': False, 'error': str(e)}
    
    def query_flight_info(self, flight_number: str, departure_date: str) -> Dict[str, Any]:
        """
        查询单个航班的详细信息（完整流程）
        
        Args:
            flight_number: 航班号，如"MU5100"
            departure_date: 出发日期，格式"YYYY-MM-DD"
            
        Returns:
            包含查询结果的字典
        """
        try:
            log_flight_process(flight_number, "航班查询", "开始", f"日期: {departure_date}")
            
            # 导航到查询页面
            if not self.navigate_to_flight_page():
                return {'status': 'error', 'error': '页面导航失败'}
            
            # 点击按航班号按钮
            if not self.click_flight_number_button():
                return {'status': 'error', 'error': '按航班号按钮点击失败'}
            
            # 填写航班信息
            if not self.fill_flight_info(flight_number, departure_date):
                return {'status': 'error', 'error': '航班信息填写失败'}
            
            # 处理验证码（带重试机制）
            while self.captcha_retry_count < self.max_captcha_retries:
                # 处理验证码
                if not self.handle_captcha(flight_number):
                    return {'status': 'captcha_failed', 'error': '验证码处理失败'}
                
                # 提交查询
                if not self.submit_query(flight_number):
                    return {'status': 'error', 'error': '查询提交失败'}
                
                # 检查响应
                response = self.check_query_response(flight_number)
                
                if response['status'] == 'captcha_error':
                    # 验证码错误，需要重试
                    log_flight_process(flight_number, "验证码验证", "错误", "服务器返回验证码错误")
                    continue
                elif response['status'] == 'success':
                    log_flight_process(flight_number, "航班查询", "成功")
                    return response
                else:
                    return response
            
            # 达到最大重试次数
            log_flight_process(flight_number, "航班查询", "失败", "验证码重试次数已达上限")
            return {'status': 'max_retries_exceeded', 'error': '验证码重试次数已达上限'}
            
        except Exception as e:
            log_flight_process(flight_number, "航班查询", "异常", str(e))
            
            if self.logger:
                log_exception('web_automation', 'query_flight_info', e, 
                            {'flight_number': flight_number, 'departure_date': departure_date})
            
            return {'status': 'error', 'error': str(e)}
    
    def wait_for_element(self, xpath: str, timeout: int = 10) -> Optional[Any]:
        """
        等待元素出现
        
        Args:
            xpath: 元素XPath
            timeout: 超时时间（秒）
            
        Returns:
            元素对象，超时返回None
        """
        try:
            wait = WebDriverWait(self.driver, timeout)
            return wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        except TimeoutException:
            return None
    
    def is_element_present(self, xpath: str) -> bool:
        """
        检查元素是否存在
        
        Args:
            xpath: 元素XPath
            
        Returns:
            是否存在
        """
        try:
            self.driver.find_element(By.XPATH, xpath)
            return True
        except NoSuchElementException:
            return False
    
    def get_page_title(self) -> str:
        """
        获取页面标题
        
        Returns:
            页面标题
        """
        try:
            return self.driver.title if self.driver else ""
        except Exception:
            return ""
    
    def get_current_url(self) -> str:
        """
        获取当前URL
        
        Returns:
            当前URL
        """
        try:
            return self.driver.current_url if self.driver else ""
        except Exception:
            return ""
    
    def take_screenshot(self, filename: str) -> bool:
        """
        截取屏幕截图
        
        Args:
            filename: 文件名
            
        Returns:
            是否截图成功
        """
        try:
            if self.driver:
                self.driver.save_screenshot(filename)
                return True
        except Exception as e:
            if self.logger:
                log_exception('web_automation', 'take_screenshot', e)
        return False


# 便捷函数
def create_web_automation(config: Optional[Dict[str, Any]] = None) -> WebAutomation:
    """
    创建网页自动化实例的便捷函数
    
    Args:
        config: 配置字典
        
    Returns:
        WebAutomation实例
    """
    return WebAutomation(config)