#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门测试captcha2.png的OCR识别脚本
目标：识别出正确结果 "lxzd"
"""

import os
import sys
from PIL import Image
import json

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.ocr_processor import OCRProcessor
from modules.config_manager import get_config_manager

def test_captcha2_only():
    """
    专门测试captcha2.png的识别效果
    """
    print("=== 专门测试 captcha2.png ===")
    print("目标结果: lxzd")
    print()
    
    # 加载配置
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        print(f"配置文件加载成功: {config_manager.config_file}")
    except Exception as e:
        print(f"配置文件加载失败: {e}")
        config = {}
    
    # 初始化OCR处理器
    ocr_processor = OCRProcessor(config)
    
    # 测试图片路径
    image_path = "captcha2.png"
    
    if not os.path.exists(image_path):
        print(f"图片文件不存在: {image_path}")
        return
    
    # 加载图片
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        image = Image.open(image_path)
        print(f"成功加载图片: {image_path}, 尺寸: {image.size}")
        print()
        
    except Exception as e:
        print(f"加载图片失败: {e}")
        return
    
    # 测试不同的预处理方法
    methods = [
        ("方法1 - 针对lxzd优化", ocr_processor._preprocess_captcha_image_method1),
        ("方法2 - 保守预处理", ocr_processor._preprocess_captcha_image_method2),
        ("方法3 - 激进预处理", ocr_processor._preprocess_captcha_image_method3),
    ]
    
    all_results = []
    
    for method_name, preprocess_func in methods:
        print(f"--- {method_name} ---")
        
        try:
            # 预处理
            processed_image = preprocess_func(image_data)
            
            # 保存预处理后的图片用于调试
            debug_filename = f"debug_captcha2_{method_name.split()[0]}.png"
            processed_image.save(debug_filename)
            print(f"预处理后图片已保存: {debug_filename}")
            
            # 使用标准Tesseract识别
            tesseract_result = ocr_processor._tesseract_recognize(processed_image, 'captcha')
            print(f"标准Tesseract结果: {tesseract_result}")
            if tesseract_result:
                all_results.append(tesseract_result)
            
            # 使用增强Tesseract识别
            enhanced_result = ocr_processor._tesseract_recognize_enhanced(processed_image)
            print(f"增强Tesseract结果: {enhanced_result}")
            if enhanced_result:
                all_results.append(enhanced_result)
            
            # 使用备用Tesseract识别
            alt_result = ocr_processor._tesseract_recognize_alternative(processed_image)
            print(f"备用Tesseract结果: {alt_result}")
            if alt_result:
                all_results.append(alt_result)
            
            # 使用PaddleOCR识别
            paddle_result = ocr_processor._paddleocr_recognize(processed_image)
            print(f"PaddleOCR结果: {paddle_result}")
            if paddle_result:
                all_results.append(paddle_result)
            
        except Exception as e:
            print(f"处理失败: {e}")
        
        print()
    
    # 测试完整识别流程
    print("--- 测试完整识别流程 ---")
    try:
        final_result = ocr_processor._enhanced_captcha_recognize(image_data)
        print(f"完整流程识别结果: {final_result}")
        
        # 检查是否识别正确
        if final_result == "lxzd":
            print("✅ 识别成功！结果正确")
        else:
            print(f"❌ 识别失败，期望: lxzd, 实际: {final_result}")
            
    except Exception as e:
        print(f"完整流程识别失败: {e}")
    
    print()
    print("--- 所有识别结果汇总 ---")
    if all_results:
        for i, result in enumerate(all_results, 1):
            cleaned_result = ocr_processor._clean_captcha_result(result)
            print(f"{i}. 原始: '{result}' -> 清理后: '{cleaned_result}'")
            if cleaned_result == "lxzd":
                print("   ✅ 这个结果是正确的！")
    else:
        print("没有获得任何识别结果")
    
    print("\n测试完成！")

if __name__ == "__main__":
    test_captcha2_only()