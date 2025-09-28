#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试航班号验证逻辑
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.input_handler import InputHandler

def test_flight_number_validation():
    """
    测试航班号验证功能
    """
    print("=== 测试航班号验证功能 ===")
    
    handler = InputHandler()
    
    # 测试用例：应该通过验证的航班号
    valid_flight_numbers = [
        'MU5100',    # 传统格式：2个字母+4个数字
        'CA1234',    # 传统格式：2个字母+4个数字
        'CZ3456',    # 传统格式：2个字母+4个数字
        'G54381',    # 1个字母+1个数字+4个数字
        '3U8888',    # 1个数字+1个字母+4个数字
        '9C8888',    # 1个数字+1个字母+4个数字
        'HO1234',    # 2个字母+4个数字
        'FM123',     # 2个字母+3个数字
        '8L456',     # 1个数字+1个字母+3个数字
    ]
    
    # 测试用例：应该不通过验证的航班号
    invalid_flight_numbers = [
        'M5100',     # 只有1位前缀
        'MU51',      # 数字部分太短
        'MU51000',   # 数字部分太长
        'mu5100',    # 小写字母
        'MU-5100',   # 包含特殊字符
        '12345',     # 全数字
        'ABCDE',     # 全字母
        '',          # 空字符串
        'MU 5100',   # 包含空格
    ]
    
    print("\n--- 测试有效航班号 ---")
    valid_count = 0
    for flight_number in valid_flight_numbers:
        try:
            result = handler._clean_and_validate_flight_number(flight_number, 1)
            print(f"✅ {flight_number} -> {result}")
            valid_count += 1
        except Exception as e:
            print(f"❌ {flight_number} -> 验证失败: {e}")
    
    print(f"\n有效航班号测试结果: {valid_count}/{len(valid_flight_numbers)} 通过")
    
    print("\n--- 测试无效航班号 ---")
    invalid_count = 0
    for flight_number in invalid_flight_numbers:
        try:
            result = handler._clean_and_validate_flight_number(flight_number, 1)
            print(f"❌ {flight_number} -> {result} (应该失败但通过了)")
        except Exception as e:
            print(f"✅ {flight_number} -> 正确拒绝: {str(e)[:50]}...")
            invalid_count += 1
    
    print(f"\n无效航班号测试结果: {invalid_count}/{len(invalid_flight_numbers)} 正确拒绝")
    
    # 总结
    total_valid = len(valid_flight_numbers)
    total_invalid = len(invalid_flight_numbers)
    success_rate = ((valid_count + invalid_count) / (total_valid + total_invalid)) * 100
    
    print(f"\n=== 测试总结 ===")
    print(f"总测试用例: {total_valid + total_invalid}")
    print(f"正确处理: {valid_count + invalid_count}")
    print(f"成功率: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 航班号验证逻辑修复成功！")
    else:
        print("⚠️ 航班号验证逻辑需要进一步调整")

if __name__ == "__main__":
    test_flight_number_validation()