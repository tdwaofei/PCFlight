#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
航班数据爬虫系统 - 主程序

本程序实现完整的航班数据爬取流程：
1. 读取Excel输入文件中的航班信息
2. 启动浏览器并访问查询网站
3. 自动填写查询表单并处理验证码
4. 提取航班数据（支持多航段）
5. 保存结果到Excel文件
6. 生成统计报告

作者: 航班数据爬虫系统
版本: 1.0.0
日期: 2025
"""

import os
import sys
import time
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.logger import get_logger, log_flight_process, log_system_info
from modules.config_manager import get_config_manager
from modules.input_handler import InputHandler, read_flight_data
from modules.web_automation import WebAutomation, create_web_automation
from modules.data_extractor import DataExtractor, extract_flight_segments
from modules.output_handler import OutputHandler, save_flight_data, create_summary_report


class FlightCrawler:
    """
    航班数据爬虫主类
    
    整合所有功能模块，实现完整的数据爬取流程
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化爬虫系统
        
        Args:
            config_file: 配置文件路径
        """
        # 初始化日志系统
        self.logger = get_logger()
        
        # 初始化配置管理器
        self.config_manager = get_config_manager(config_file)
        
        # 获取配置
        self.browser_config = self.config_manager.get_browser_config()
        self.retry_config = self.config_manager.get_retry_config()
        self.output_config = self.config_manager.get_output_config()
        
        # 初始化各功能模块
        self.input_handler = InputHandler()
        self.web_automation = None
        self.data_extractor = DataExtractor()
        self.output_handler = OutputHandler()
        
        # 运行统计
        self.start_time = None
        self.total_flights = 0
        self.successful_flights = 0
        self.total_segments = 0
        self.successful_segments = 0
        
        if self.logger:
            log_system_info("航班数据爬虫系统初始化完成")
    
    def run(self, input_file: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        运行完整的爬取流程
        
        Args:
            input_file: 输入Excel文件路径
            output_file: 输出Excel文件路径（可选）
            
        Returns:
            运行结果字典
        """
        self.start_time = datetime.now()
        
        try:
            if self.logger:
                log_system_info(f"开始运行航班数据爬取，输入文件: {input_file}")
            
            # 步骤1: 读取输入数据
            flight_list = self._load_input_data(input_file)
            if not flight_list:
                return self._create_result(False, "输入数据为空或读取失败")
            
            self.total_flights = len(flight_list)
            
            # 步骤2: 初始化浏览器
            if not self._initialize_browser():
                return self._create_result(False, "浏览器初始化失败")
            
            # 步骤3: 处理每个航班查询
            all_segments = []
            
            try:
                for index, flight_info in enumerate(flight_list, 1):
                    if self.logger:
                        log_flight_process(
                            flight_info.get('flight_number', ''),
                            "航班处理",
                            "开始",
                            f"进度: {index}/{self.total_flights}"
                        )
                    
                    # 处理单个航班
                    segments = self._process_single_flight(flight_info, index)
                    
                    if segments:
                        all_segments.extend(segments)
                        self.successful_flights += 1
                        self.successful_segments += len(segments)
                        
                        if self.logger:
                            log_flight_process(
                                flight_info.get('flight_number', ''),
                                "航班处理",
                                "成功",
                                f"提取到 {len(segments)} 个航段"
                            )
                    else:
                        if self.logger:
                            log_flight_process(
                                flight_info.get('flight_number', ''),
                                "航班处理",
                                "失败",
                                "未提取到有效数据"
                            )
                    
                    self.total_segments += len(segments) if segments else 0
                    
                    # 航班间延迟
                    if index < len(flight_list):
                        delay = self.retry_config.get('flight_delay', 2)
                        if delay > 0:
                            time.sleep(delay)
            
            finally:
                # 步骤4: 关闭浏览器
                self._cleanup_browser()
            
            # 步骤5: 保存结果
            if all_segments:
                save_result = self._save_results(all_segments, output_file)
                if not save_result['success']:
                    return self._create_result(False, f"保存结果失败: {save_result['message']}")
                
                # 生成统计报告
                self._generate_summary_report(save_result.get('statistics', {}))
                
                return self._create_result(True, "爬取完成", {
                    'output_file': save_result['file_path'],
                    'statistics': save_result['statistics']
                })
            else:
                return self._create_result(False, "未提取到任何有效数据")
                
        except Exception as e:
            error_msg = f"运行过程中发生异常: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            return self._create_result(False, error_msg)
        
        finally:
            # 记录运行统计
            self._log_final_statistics()
    
    def _load_input_data(self, input_file: str) -> List[Dict[str, Any]]:
        """
        加载输入数据
        
        Args:
            input_file: 输入文件路径
            
        Returns:
            航班信息列表
        """
        try:
            if not os.path.exists(input_file):
                if self.logger:
                    self.logger.error(f"输入文件不存在: {input_file}")
                return []
            
            flight_list = read_flight_data(input_file)
            
            if self.logger:
                self.logger.info(f"成功读取 {len(flight_list)} 条航班信息")
            
            return flight_list
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"读取输入文件失败: {str(e)}")
            return []
    
    def _initialize_browser(self) -> bool:
        """
        初始化浏览器
        
        Returns:
            是否成功
        """
        try:
            self.web_automation = create_web_automation()
            
            if not self.web_automation.start_browser():
                if self.logger:
                    self.logger.error("浏览器启动失败")
                return False
            
            if self.logger:
                log_system_info("浏览器初始化成功")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"浏览器初始化异常: {str(e)}")
            return False
    
    def _process_single_flight(self, flight_info: Dict[str, Any], index: int) -> List[Dict[str, Any]]:
        """
        处理单个航班查询
        
        Args:
            flight_info: 航班信息
            index: 航班索引
            
        Returns:
            航段数据列表
        """
        flight_number = flight_info.get('flight_number', '')
        departure_date = flight_info.get('departure_date', '')
        
        try:
            # 导航到查询页面
            if not self.web_automation.navigate_to_query_page():
                if self.logger:
                    log_flight_process(flight_number, "页面导航", "失败")
                return []
            
            # 填写查询表单
            if not self.web_automation.fill_query_form(flight_number, departure_date):
                if self.logger:
                    log_flight_process(flight_number, "表单填写", "失败")
                return []
            
            # 处理验证码并提交查询
            if not self.web_automation.handle_captcha_and_submit(flight_number):
                if self.logger:
                    log_flight_process(flight_number, "验证码处理", "失败")
                return []
            
            # 等待结果页面加载
            time.sleep(self.retry_config.get('page_load_delay', 3))
            
            # 提取航段数据
            segments = extract_flight_segments(
                self.web_automation.driver, flight_number, departure_date
            )
            
            return segments
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"处理航班 {flight_number} 时发生异常: {str(e)}")
            return []
    
    def _cleanup_browser(self):
        """
        清理浏览器资源
        """
        try:
            if self.web_automation:
                self.web_automation.close_browser()
                if self.logger:
                    log_system_info("浏览器已关闭")
        except Exception as e:
            if self.logger:
                self.logger.error(f"关闭浏览器时发生异常: {str(e)}")
    
    def _save_results(self, segments: List[Dict[str, Any]], output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        保存结果数据
        
        Args:
            segments: 航段数据列表
            output_file: 输出文件名
            
        Returns:
            保存结果
        """
        try:
            result = save_flight_data(segments, output_file)
            
            if result['success'] and self.logger:
                self.logger.info(f"结果保存成功: {result['file_path']}")
                self.logger.info(f"共保存 {len(segments)} 条航段数据")
            
            return result
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"保存结果时发生异常: {str(e)}")
            return {
                'success': False,
                'message': f'保存异常: {str(e)}',
                'file_path': None,
                'statistics': None
            }
    
    def _generate_summary_report(self, statistics: Dict[str, Any]):
        """
        生成汇总报告
        
        Args:
            statistics: 统计信息
        """
        try:
            if self.output_config.get('generate_summary', True):
                result = create_summary_report(statistics)
                
                if result['success'] and self.logger:
                    self.logger.info(f"汇总报告生成成功: {result['file_path']}")
                elif self.logger:
                    self.logger.warning(f"汇总报告生成失败: {result['message']}")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f"生成汇总报告时发生异常: {str(e)}")
    
    def _create_result(self, success: bool, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建结果字典
        
        Args:
            success: 是否成功
            message: 结果消息
            data: 附加数据
            
        Returns:
            结果字典
        """
        result = {
            'success': success,
            'message': message,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else '',
            'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_flights': self.total_flights,
            'successful_flights': self.successful_flights,
            'total_segments': self.total_segments,
            'successful_segments': self.successful_segments
        }
        
        if data:
            result.update(data)
        
        return result
    
    def _log_final_statistics(self):
        """
        记录最终统计信息
        """
        if not self.logger or not self.start_time:
            return
        
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        self.logger.info("=" * 50)
        self.logger.info("航班数据爬取完成 - 最终统计")
        self.logger.info(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"总耗时: {duration}")
        self.logger.info(f"总航班数: {self.total_flights}")
        self.logger.info(f"成功航班数: {self.successful_flights}")
        self.logger.info(f"航班成功率: {(self.successful_flights/self.total_flights*100):.2f}%" if self.total_flights > 0 else "航班成功率: 0%")
        self.logger.info(f"总航段数: {self.total_segments}")
        self.logger.info(f"成功航段数: {self.successful_segments}")
        self.logger.info(f"航段成功率: {(self.successful_segments/self.total_segments*100):.2f}%" if self.total_segments > 0 else "航段成功率: 0%")
        self.logger.info("=" * 50)


def create_sample_input():
    """
    创建示例输入文件
    """
    try:
        from modules.input_handler import create_sample_input_file
        
        input_dir = 'input'
        os.makedirs(input_dir, exist_ok=True)
        
        sample_file = os.path.join(input_dir, 'sample_flights.xlsx')
        
        if create_sample_input_file(sample_file):
            print(f"示例输入文件创建成功: {sample_file}")
            print("请编辑此文件，填入要查询的航班信息，然后运行主程序。")
        else:
            print("示例输入文件创建失败")
            
    except Exception as e:
        print(f"创建示例输入文件时发生异常: {str(e)}")


def main():
    """
    主函数 - 命令行入口
    """
    parser = argparse.ArgumentParser(
        description='航班数据爬虫系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py -i input/flights.xlsx                    # 使用默认输出文件名
  python main.py -i input/flights.xlsx -o output/result.xlsx  # 指定输出文件名
  python main.py --sample                                 # 创建示例输入文件
  python main.py -c config/custom.json -i input/flights.xlsx  # 使用自定义配置文件
        """
    )
    
    parser.add_argument('-i', '--input', type=str, help='输入Excel文件路径')
    parser.add_argument('-o', '--output', type=str, help='输出Excel文件路径（可选）')
    parser.add_argument('-c', '--config', type=str, help='配置文件路径（可选）')
    parser.add_argument('--sample', action='store_true', help='创建示例输入文件')
    parser.add_argument('--version', action='version', version='航班数据爬虫系统 v1.0.0')
    
    args = parser.parse_args()
    
    # 创建示例文件
    if args.sample:
        create_sample_input()
        return
    
    # 检查必需参数
    if not args.input:
        parser.print_help()
        print("\n错误: 必须指定输入文件路径 (-i/--input)")
        print("使用 --sample 参数可以创建示例输入文件")
        sys.exit(1)
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}")
        print("使用 --sample 参数可以创建示例输入文件")
        sys.exit(1)
    
    try:
        # 创建爬虫实例
        crawler = FlightCrawler(args.config)
        
        # 运行爬取流程
        print("开始运行航班数据爬取...")
        print(f"输入文件: {args.input}")
        if args.output:
            print(f"输出文件: {args.output}")
        print("-" * 50)
        
        result = crawler.run(args.input, args.output)
        
        # 输出结果
        print("-" * 50)
        if result['success']:
            print("✓ 爬取完成!")
            print(f"总航班数: {result['total_flights']}")
            print(f"成功航班数: {result['successful_flights']}")
            print(f"总航段数: {result['total_segments']}")
            print(f"成功航段数: {result['successful_segments']}")
            
            if 'output_file' in result:
                print(f"结果文件: {result['output_file']}")
            
            # 显示统计信息
            if 'statistics' in result and result['statistics']:
                stats = result['statistics']
                print(f"数据成功率: {stats.get('success_rate', 0)}%")
        else:
            print(f"✗ 爬取失败: {result['message']}")
        
        print(f"开始时间: {result['start_time']}")
        print(f"结束时间: {result['end_time']}")
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"程序运行异常: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()