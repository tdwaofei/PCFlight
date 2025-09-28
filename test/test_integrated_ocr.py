#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试集成ddddocr后的OCR处理器
"""

import os
import sys
from PIL import Image
import io

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.ocr_processor import OCRProcessor

def test_integrated_ocr():
    """
    测试集成ddddocr后的OCR处理器
    """
    print("=== 测试集成ddddocr后的OCR处理器 ===")
    
    # 初始化OCR处理器
    try:
        processor = OCRProcessor()
        print(f"OCR处理器初始化成功")
        print(f"默认引擎: {processor.engine}")
        print(f"ddddocr可用: {processor.ddddocr_available}")
        print(f"Tesseract可用: {processor.tesseract_available}")
        print(f"PaddleOCR可用: {processor.paddleocr_available}")
    except Exception as e:
        print(f"OCR处理器初始化失败: {e}")
        return
    
    # 测试图片列表
    test_images = [
        ("../captcha1.png", "lyjp"),
        ("../captcha2.jpg", "lxzd"),
        ("../captcha3.png", "xlok"),
        ("../captcha4.png", "vgsj")
    ]
    
    results = {}
    
    for img_path, expected in test_images:
        if not os.path.exists(img_path):
            print(f"图片文件不存在: {img_path}")
            continue
            
        print(f"\n--- 测试 {img_path} (期望: {expected}) ---")
        
        try:
            # 读取图片数据
            with open(img_path, "rb") as f:
                image_data = f.read()
            
            # 测试直接使用ddddocr识别
            if processor.ddddocr_available:
                result1 = processor._ddddocr_recognize(image_data, 'captcha')
                print(f"ddddocr直接识别: '{result1}'")
                
                # 测试预处理后识别
                try:
                    processed_image = processor._preprocess_captcha_image_method1(image_data)
                    buffer = io.BytesIO()
                    processed_image.save(buffer, format='PNG')
                    processed_data = buffer.getvalue()
                    
                    result2 = processor._ddddocr_recognize(processed_data, 'captcha')
                    print(f"ddddocr预处理后识别: '{result2}'")
                    
                    # 选择最佳结果
                    best_result = result2 if result2 and len(result2) == 4 else result1
                    results[img_path] = best_result
                    
                    if best_result == expected:
                        print(f"✅ 识别正确: '{best_result}'")
                    else:
                        print(f"❌ 识别错误: '{best_result}' (期望: '{expected}')")
                        
                except Exception as e:
                    print(f"预处理识别失败: {e}")
                    results[img_path] = result1
            else:
                print("ddddocr不可用")
                results[img_path] = None
                
        except Exception as e:
            print(f"处理图片 {img_path} 时出错: {e}")
            results[img_path] = None
    
    # 汇总结果
    print(f"\n=== 识别结果汇总 ===")
    correct_count = 0
    total_count = 0
    
    for (img_path, expected), actual in zip(test_images, results.values()):
        if os.path.exists(img_path):
            total_count += 1
            if actual == expected:
                correct_count += 1
                print(f"✅ {img_path}: '{actual}' (正确)")
            else:
                print(f"❌ {img_path}: '{actual}' (期望: '{expected}')")
    
    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
    print(f"\n总体识别准确率: {correct_count}/{total_count} ({accuracy:.1f}%)")
    
    if accuracy > 0:
        print("🎉 ddddocr集成成功！")
    else:
        print("⚠️ ddddocr识别效果需要进一步优化")

if __name__ == "__main__":
    test_integrated_ocr()