#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础功能测试脚本
"""

import os
import sys

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    
    try:
        from modules.logger import get_logger
        print("✓ logger模块导入成功")
    except Exception as e:
        print(f"✗ logger模块导入失败: {e}")
        return False
    
    try:
        from modules.config_manager import get_config_manager
        print("✓ config_manager模块导入成功")
    except Exception as e:
        print(f"✗ config_manager模块导入失败: {e}")
        return False
    
    return True

def test_config():
    """测试配置文件"""
    print("\n测试配置文件...")
    
    try:
        from modules.config_manager import get_config_manager
        config_manager = get_config_manager()
        
        # 测试获取配置
        browser_config = config_manager.get_browser_config()
        print(f"✓ 浏览器配置: {browser_config}")
        
        ocr_config = config_manager.get_ocr_config()
        print(f"✓ OCR配置: {ocr_config}")
        
        return True
    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
        return False

def test_logger():
    """测试日志系统"""
    print("\n测试日志系统...")
    
    try:
        from modules.logger import get_logger, log_system_info
        
        logger = get_logger()
        if logger:
            print("✓ 日志系统初始化成功")
            log_system_info("测试日志消息")
            print("✓ 日志记录成功")
        else:
            print("✗ 日志系统初始化失败")
            return False
        
        return True
    except Exception as e:
        print(f"✗ 日志测试失败: {e}")
        return False

def test_directories():
    """测试目录结构"""
    print("\n测试目录结构...")
    
    required_dirs = ['input', 'output', 'logs', 'modules']
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✓ {dir_name}/ 目录存在")
        else:
            print(f"✗ {dir_name}/ 目录不存在")
            return False
    
    return True

def create_simple_sample():
    """创建简单的示例文件"""
    print("\n创建简单示例文件...")
    
    try:
        import pandas as pd
        
        # 创建示例数据
        sample_data = {
            '航班号': ['CA1234', 'MU5678', 'CZ9012'],
            '出发日期': ['2024-01-15', '2024-01-16', '2024-01-17']
        }
        
        df = pd.DataFrame(sample_data)
        
        # 保存到Excel文件
        output_file = os.path.join('input', 'simple_sample.xlsx')
        df.to_excel(output_file, index=False)
        
        print(f"✓ 简单示例文件创建成功: {output_file}")
        return True
        
    except ImportError:
        print("✗ pandas未安装，无法创建Excel文件")
        return False
    except Exception as e:
        print(f"✗ 创建示例文件失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("航班数据爬虫系统 - 基础功能测试")
    print("=" * 50)
    
    tests = [
        test_directories,
        test_imports,
        test_config,
        test_logger,
        create_simple_sample
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print("\n测试中断，请检查错误信息")
            break
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✓ 所有基础功能测试通过！")
        print("\n下一步:")
        print("1. 安装完整依赖: pip install selenium webdriver-manager")
        print("2. 编辑 input/simple_sample.xlsx 文件")
        print("3. 运行完整程序: python main.py -i input/simple_sample.xlsx")
    else:
        print("✗ 部分测试失败，请检查配置")
    
    print("=" * 50)

if __name__ == '__main__':
    main()