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
from selenium.webdriver.common.keys import Keys
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

    def close_browser(self) -> None:
        """
        关闭浏览器（stop_browser的别名）
        """
        self.stop_browser()
    
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
                try:
                    # 等待日期输入框可见并可交互
                    date_input = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, date_input_xpath))
                    )
                    
                    # 检查是否为只读控件，如果是则先移除readonly属性
                    readonly_attr = date_input.get_attribute('readonly')
                    if readonly_attr:
                        if self.logger:
                            self.logger.info(f"检测到只读日期控件，移除readonly属性")
                        # 使用JavaScript移除readonly属性
                        self.driver.execute_script("arguments[0].removeAttribute('readonly');", date_input)
                        time.sleep(0.2)  # 短暂等待属性更新
                    
                    # 点击日期输入框以确保获得焦点
                    date_input.click()
                    time.sleep(0.5)  # 短暂等待确保元素状态稳定
                    
                    # 尝试清空输入框，如果失败则使用键盘快捷键
                    try:
                        date_input.clear()
                    except Exception:
                        # 如果clear()失败，使用Ctrl+A选择全部内容然后删除
                        date_input.send_keys(Keys.CONTROL + "a")
                        date_input.send_keys(Keys.DELETE)
                    
                    # 输入日期
                    date_input.send_keys(departure_date)
                    
                    # 验证日期是否正确填写
                    time.sleep(0.5)  # 等待日期控件更新
                    actual_value = date_input.get_attribute('value')
                    
                    if self.logger:
                        if actual_value == departure_date:
                            self.logger.info(f"出发日期填写成功: {departure_date} (验证通过)")
                        else:
                            self.logger.warning(f"出发日期填写异常: 期望={departure_date}, 实际={actual_value}")
                        
                except Exception as date_error:
                    if self.logger:
                        self.logger.warning(f"日期输入遇到问题，尝试备用方法: {str(date_error)}")
                    
                    # 备用方法：使用JavaScript直接设置值
                    try:
                        date_input = self.driver.find_element(By.XPATH, date_input_xpath)
                        
                        # 先移除readonly属性（如果存在）
                        self.driver.execute_script("arguments[0].removeAttribute('readonly');", date_input)
                        
                        # 直接设置值
                        self.driver.execute_script("arguments[0].value = arguments[1];", date_input, departure_date)
                        
                        # 触发多个事件确保日期控件响应
                        self.driver.execute_script("""
                            var element = arguments[0];
                            element.dispatchEvent(new Event('input', { bubbles: true }));
                            element.dispatchEvent(new Event('change', { bubbles: true }));
                            element.dispatchEvent(new Event('blur', { bubbles: true }));
                        """, date_input)
                        
                        # 验证JavaScript方法是否成功
                        time.sleep(0.5)
                        actual_value = date_input.get_attribute('value')
                        
                        if self.logger:
                            if actual_value == departure_date:
                                self.logger.info(f"使用JavaScript方法填写日期成功: {departure_date} (验证通过)")
                            else:
                                self.logger.warning(f"JavaScript方法填写日期异常: 期望={departure_date}, 实际={actual_value}")
                                
                    except Exception as js_error:
                        if self.logger:
                            self.logger.error(f"JavaScript方法也失败: {str(js_error)}")
                        raise date_error  # 抛出原始错误
            
            return True
            
        except Exception as e:
            if self.logger:
                log_exception('web_automation', 'fill_flight_info', e, 
                            {'flight_number': flight_number, 'departure_date': departure_date})
            return False
    
    def handle_captcha_and_submit(self, flight_number: str) -> bool:
        """
        处理验证码并提交查询（带重试机制）
        验证码识别最多6次，查询提交最多5次（验证码错误时）
        
        Args:
            flight_number: 当前处理的航班号（用于日志）
            
        Returns:
            是否处理成功
        """
        max_query_attempts = 5  # 查询最多尝试5次（针对验证码错误）
        
        for query_attempt in range(1, max_query_attempts + 1):
            if self.logger:
                self.logger.info(f"[{flight_number}] 查询尝试 {query_attempt}/{max_query_attempts}")
            
            # 处理验证码（最多6次尝试）
            if not self.handle_captcha(flight_number):
                if self.logger:
                    self.logger.error(f"[{flight_number}] 验证码识别失败，查询尝试 {query_attempt} 终止")
                continue  # 验证码识别失败，尝试下一轮查询
            
            # 提交查询
            if not self.submit_query(flight_number):
                if self.logger:
                    self.logger.error(f"[{flight_number}] 查询提交失败，尝试 {query_attempt}")
                continue  # 查询提交失败，尝试下一轮
            
            # 检查查询结果
            response = self.check_query_response(flight_number)
            
            if response.get('success', False):
                if self.logger:
                    self.logger.info(f"[{flight_number}] 查询成功，尝试 {query_attempt}")
                return True
            elif response.get('captcha_error', False):
                if self.logger:
                    self.logger.warning(f"[{flight_number}] 验证码错误，尝试 {query_attempt}/{max_query_attempts}，系统已自动刷新验证码")
                # 验证码错误，系统已自动刷新，等待页面更新后继续下一轮尝试
                time.sleep(2)  # 等待验证码刷新完成
                continue
            else:
                if self.logger:
                    self.logger.warning(f"[{flight_number}] 查询失败，尝试 {query_attempt}，原因: {response.get('error', '未知错误')}")
                continue
        
        if self.logger:
            self.logger.error(f"[{flight_number}] 查询失败，已尝试 {max_query_attempts} 次")
        return False

    def handle_captcha(self, flight_number: str) -> bool:
        """
        处理验证码（带重试机制）
        最多尝试6次，每次失败后刷新验证码
        
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
                
                if self.logger:
                    self.logger.info(f"验证码图片XPath: {captcha_img_xpath}")
                
                # 等待验证码图片加载完成
                captcha_img = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, captcha_img_xpath))
                )
                
                # 获取初始验证码图片的src属性，用于检测是否刷新
                initial_src = captcha_img.get_attribute('src')
                
                # 额外等待确保验证码图片完全加载
                time.sleep(0.5)
                
                # 重新获取验证码图片元素，确保获取最新的验证码
                captcha_img = self.driver.find_element(By.XPATH, captcha_img_xpath)
                current_src = captcha_img.get_attribute('src')
                
                # 如果验证码图片没有变化，强制等待更长时间
                if initial_src == current_src and self.captcha_retry_count > 1:
                    if self.logger:
                        self.logger.info(f"验证码图片未刷新，等待更长时间...")
                    time.sleep(1.5)
                    captcha_img = self.driver.find_element(By.XPATH, captcha_img_xpath)
                
                # 保存验证码图片到本地
                self._save_captcha_image(captcha_img, flight_number, self.captcha_retry_count)
                
                # OCR识别验证码
                captcha_text = self.ocr_processor.recognize_captcha(
                    captcha_img, max_attempts=1
                )
                
                if not captcha_text:
                    log_flight_process(flight_number, "验证码识别", "失败", "OCR识别失败")
                    
                    # 只有在未达到最大重试次数时才刷新验证码
                    if self.captcha_retry_count < self.max_captcha_retries:
                        if self._refresh_captcha():
                            time.sleep(self.retry_config.get('captcha_delay_seconds', 1))
                            continue
                        else:
                            break
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
                
                # 只有在未达到最大重试次数时才刷新验证码
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
        检查查询响应，判断是否有验证码错误或查询成功
        
        Args:
            flight_number: 航班号
            
        Returns:
            响应状态字典: {
                'success': bool,        # 查询是否成功
                'captcha_error': bool,  # 是否验证码错误
                'error': str           # 错误信息
            }
        """
        try:
            # 等待页面加载
            time.sleep(3)
            
            # 检查是否有验证码错误提示
            captcha_error_indicators = [
                "验证码错误",
                "验证码不正确", 
                "captcha error",
                "验证码输入错误"
            ]
            
            page_source = self.driver.page_source.lower()
            for indicator in captcha_error_indicators:
                if indicator.lower() in page_source:
                    return {
                        'success': False,
                        'captcha_error': True,
                        'error': f'验证码错误: {indicator}'
                    }
            
            # 检查是否有结果数据
            result_list_xpath = self.xpath_config.get('result_list')
            if result_list_xpath:
                try:
                    result_element = self.driver.find_element(By.XPATH, result_list_xpath)
                    if result_element and result_element.is_displayed():
                        # 检查结果列表是否有内容
                        result_items = result_element.find_elements(By.XPATH, ".//div")
                        if len(result_items) > 0:
                            return {
                                'success': True,
                                'captcha_error': False,
                                'error': None
                            }
                        else:
                            return {
                                'success': False,
                                'captcha_error': False,
                                'error': '结果列表为空'
                            }
                except:
                    # 结果列表不存在或不可见
                    pass
            
            # 检查是否有其他错误提示
            error_indicators = [
                "查询失败",
                "没有找到相关信息",
                "暂无数据",
                "系统繁忙"
            ]
            
            for indicator in error_indicators:
                if indicator in page_source:
                    return {
                        'success': False,
                        'captcha_error': False,
                        'error': f'查询错误: {indicator}'
                    }
            
            # 默认认为查询失败
            return {
                'success': False,
                'captcha_error': False,
                'error': '未找到有效结果'
            }
            
        except Exception as e:
            if self.logger:
                log_exception('web_automation', 'check_query_response', e, 
                            {'flight_number': flight_number})
            
            return {
                'success': False,
                'captcha_error': False,
                'error': f'检查响应时发生异常: {str(e)}'
            }
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

    def navigate_to_query_page(self) -> bool:
        """
        导航到查询页面（组合操作）
        
        完成完整的页面导航流程：
        1. 访问航班查询页面
        2. 点击"按航班号"按钮
        
        Returns:
            bool: 是否导航成功
        """
        try:
            if self.logger:
                self.logger.info("开始导航到查询页面")
            
            # 1. 导航到航班查询页面
            if not self.navigate_to_flight_page():
                if self.logger:
                    self.logger.error("导航到航班页面失败")
                return False
            
            # 2. 点击"按航班号"按钮
            if not self.click_flight_number_button():
                if self.logger:
                    self.logger.error("点击航班号按钮失败")
                return False
            
            if self.logger:
                self.logger.info("查询页面导航成功")
            
            return True
            
        except Exception as e:
            if self.logger:
                log_exception('web_automation', 'navigate_to_query_page', e)
            return False

    def fill_query_form(self, flight_number: str, departure_date: str) -> bool:
        """
        填写查询表单（组合操作）
        
        完成完整的表单填写流程：
        1. 填写航班号和出发日期
        2. 处理验证码识别
        3. 点击查询按钮
        
        Args:
            flight_number (str): 航班号
            departure_date (str): 出发日期（YYYY-MM-DD格式）
            
        Returns:
            bool: 是否填写成功
        """
        try:
            if self.logger:
                self.logger.info(f"开始填写查询表单: {flight_number}, {departure_date}")
            
            # 1. 填写航班信息
            if not self.fill_flight_info(flight_number, departure_date):
                if self.logger:
                    self.logger.error("填写航班信息失败")
                return False
            
            # 2. 处理验证码
            if not self.handle_captcha(flight_number):
                if self.logger:
                    self.logger.error("验证码处理失败")
                return False
            
            # 3. 点击查询按钮
            if not self.click_query_button():
                if self.logger:
                    self.logger.error("点击查询按钮失败")
                return False
            
            if self.logger:
                self.logger.info(f"查询表单填写成功: {flight_number}")
            
            return True
            
        except Exception as e:
            if self.logger:
                log_exception('web_automation', 'fill_query_form', e, 
                            {'flight_number': flight_number, 'departure_date': departure_date})
            return False

    def click_query_button(self) -> bool:
        """
        点击查询按钮
        
        等待查询按钮可点击并执行点击操作，然后等待查询结果加载
        
        Returns:
            bool: 是否点击成功
        """
        try:
            xpath = self.xpath_config.get('query_button')
            if not xpath:
                raise ValueError("未配置查询按钮XPath")
            
            if self.logger:
                self.logger.info("正在点击查询按钮")
            
            # 等待按钮可点击
            button = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            button.click()
            
            # 等待查询结果加载
            time.sleep(2)
            
            if self.logger:
                self.logger.info("查询按钮点击成功")
            
            return True
            
        except Exception as e:
            if self.logger:
                log_exception('web_automation', 'click_query_button', e)
            return False

    def _save_captcha_image(self, captcha_element, flight_number: str, attempt: int) -> None:
        """
        保存验证码图片到本地文件
        
        Args:
            captcha_element: 验证码图片元素
            flight_number: 航班号
            attempt: 尝试次数
        """
        try:
            import os
            from datetime import datetime
            
            # 确保captchaimage目录存在
            captcha_dir = os.path.join("output", "captchaimage")
            if not os.path.exists(captcha_dir):
                os.makedirs(captcha_dir)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"captcha_{flight_number}_{timestamp}_attempt{attempt}.png"
            filepath = os.path.join(captcha_dir, filename)
            
            # 获取图片数据并保存
            image_data = captcha_element.screenshot_as_png
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            if self.logger:
                self.logger.info(f"验证码图片已保存: {filepath}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"保存验证码图片失败: {str(e)}")


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