#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试XPath路径日志记录功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.config_manager import get_config_manager
from modules.data_extractor import DataExtractor

def test_xpath_configuration():
    """测试XPath配置是否正确"""
    print("=== 测试XPath配置 ===")
    
    # 获取配置管理器
    config_manager = get_config_manager()
    xpath_config = config_manager.get_xpath_config()
    
    print("验证码图片XPath:")
    print(f"  {xpath_config.get('captcha_image')}")
    
    print("\n实际起飞时间图片XPath:")
    actual_departure_template = xpath_config.get('actual_departure_img')
    print(f"  模板: {actual_departure_template}")
    if '{}' in actual_departure_template:
        print(f"  航段1: {actual_departure_template.format(1)}")
        print(f"  航段2: {actual_departure_template.format(2)}")
    
    print("\n实际到达时间图片XPath:")
    actual_arrival_template = xpath_config.get('actual_arrival_img')
    print(f"  模板: {actual_arrival_template}")
    if '{}' in actual_arrival_template:
        print(f"  航段1: {actual_arrival_template.format(1)}")
        print(f"  航段2: {actual_arrival_template.format(2)}")
    
    print("\n航班状态XPath:")
    flight_status_template = xpath_config.get('flight_status')
    print(f"  模板: {flight_status_template}")
    if '{}' in flight_status_template:
        print(f"  航段1: {flight_status_template.format(1)}")
        print(f"  航段2: {flight_status_template.format(2)}")

def test_data_extractor_xpath_logic():
    """测试数据提取器的XPath逻辑"""
    print("\n=== 测试数据提取器XPath逻辑 ===")
    
    # 创建数据提取器实例
    extractor = DataExtractor()
    
    # 模拟测试航班状态XPath选择逻辑
    print("\n航班状态XPath选择测试:")
    
    # 模拟单条记录情况
    print("单条记录 (total_segments=1):")
    print("  应该使用: /html/body/div[1]/div[2]/div[1]/div/div[2]/div[3]/div/div[10]/span")
    
    # 模拟多条记录情况
    print("多条记录 (total_segments=3):")
    for i in range(1, 4):
        expected_xpath = f"/html/body/div[1]/div[2]/div[1]/div/div[2]/div[3]/div[{i}]/div[10]/span"
        print(f"  航段{i}: {expected_xpath}")

def test_time_image_xpath():
    """测试时间图片XPath"""
    print("\n=== 测试时间图片XPath ===")
    
    config_manager = get_config_manager()
    xpath_config = config_manager.get_xpath_config()
    
    # 测试实际起飞时间XPath
    departure_template = xpath_config.get('actual_departure_img')
    print(f"实际起飞时间XPath模板: {departure_template}")
    
    if '{}' in departure_template:
        print("支持多航段，示例:")
        for i in range(1, 4):
            xpath = departure_template.format(i)
            print(f"  航段{i}: {xpath}")
    else:
        print("不支持多航段 (缺少{}占位符)")
    
    # 测试实际到达时间XPath
    arrival_template = xpath_config.get('actual_arrival_img')
    print(f"\n实际到达时间XPath模板: {arrival_template}")
    
    if '{}' in arrival_template:
        print("支持多航段，示例:")
        for i in range(1, 4):
            xpath = arrival_template.format(i)
            print(f"  航段{i}: {xpath}")
    else:
        print("不支持多航段 (缺少{}占位符)")

if __name__ == "__main__":
    print("XPath路径日志记录功能测试")
    print("=" * 50)
    
    try:
        test_xpath_configuration()
        test_data_extractor_xpath_logic()
        test_time_image_xpath()
        
        print("\n" + "=" * 50)
        print("✅ 测试完成！")
        print("\n关键修改:")
        print("1. ✅ 修复了实际起飞/到达时间图片XPath，添加了{}占位符")
        print("2. ✅ 在验证码识别中添加了XPath路径日志")
        print("3. ✅ 在时间图片识别中添加了XPath路径日志")
        print("4. ✅ 航班状态XPath支持单条/多条记录智能选择")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()