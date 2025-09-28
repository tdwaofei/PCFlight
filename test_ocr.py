#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证码识别测试脚本
用于测试改进后的OCR识别功能
"""

import os
import sys
import base64
from PIL import Image, ImageDraw, ImageFont
import io

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.ocr_processor import OCRProcessor

def create_test_captcha():
    """创建测试验证码图片"""
    # 创建一个模拟验证码的图片
    img = Image.new('RGB', (120, 40), color='white')
    draw = ImageDraw.Draw(img)
    
    # 添加一些背景噪声
    import random
    for _ in range(50):
        x = random.randint(0, 119)
        y = random.randint(0, 39)
        draw.point((x, y), fill=(200, 200, 200))
    
    # 添加文字 "TEST"
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        # 如果没有找到字体，使用默认字体
        font = ImageFont.load_default()
    
    draw.text((20, 10), "TEST", fill='black', font=font)
    
    return img

def test_captcha_recognition():
    """测试验证码识别功能"""
    print("=== 测试验证码识别功能 ===")
    
    # 初始化OCR处理器
    ocr_processor = OCRProcessor()
    
    # 测试图片文件列表（假设用户已经提供了这些图片）
    test_images = [
        "captcha1.png",
        "captcha2.png", 
        "captcha3.png",
        "captcha4.png"
    ]
    
    # 如果没有找到用户提供的图片，创建测试图片
    available_images = []
    for img_path in test_images:
        if os.path.exists(img_path):
            available_images.append(img_path)
    
    if not available_images:
        print("未找到用户提供的验证码图片，创建测试图片...")
        test_img = create_test_captcha()
        test_img.save("test_captcha.png")
        available_images = ["test_captcha.png"]
    
    # 对每个图片进行测试
    for img_path in available_images:
        print(f"\n=== 测试图片: {img_path} ===")
        
        try:
            # 加载图片
            test_img = Image.open(img_path)
            print(f"成功加载图片: {img_path}, 尺寸: {test_img.size}")
            
            # 转换为字节数据
            buffer = io.BytesIO()
            test_img.save(buffer, format='PNG')
            img_data = buffer.getvalue()
            
            # 测试不同的预处理方法
            methods = [
                ('方法1 - 标准预处理', ocr_processor._preprocess_captcha_image),
                ('方法2 - 保守预处理', ocr_processor._preprocess_captcha_image_method2),
                ('方法3 - 激进预处理', ocr_processor._preprocess_captcha_image_method3),
            ]
            
            for method_name, preprocess_func in methods:
                print(f"\n--- {method_name} ---")
                
                try:
                    # 预处理图片
                    processed_img = preprocess_func(img_data)
                    
                    # 保存预处理后的图片用于调试
                    debug_path = f"debug_{os.path.splitext(img_path)[0]}_{method_name.split()[0]}.png"
                    processed_img.save(debug_path)
                    print(f"预处理后图片已保存: {debug_path}")
                    
                    # 转换为字节数据进行OCR识别
                    buffer = io.BytesIO()
                    processed_img.save(buffer, format='PNG')
                    processed_data = buffer.getvalue()
                    
                    # 直接测试OCR引擎
                    try:
                        # 测试Tesseract
                        result_tesseract = ocr_processor._tesseract_recognize(processed_img, 'captcha')
                        print(f"Tesseract结果: {result_tesseract}")
                    except Exception as e:
                        print(f"Tesseract错误: {str(e)}")
                    
                    try:
                        # 测试增强Tesseract
                        result_enhanced = ocr_processor._tesseract_recognize_enhanced(processed_img)
                        print(f"增强Tesseract结果: {result_enhanced}")
                    except Exception as e:
                        print(f"增强Tesseract错误: {str(e)}")
                    
                    try:
                        # 测试PaddleOCR
                        result_paddle = ocr_processor._paddleocr_recognize(processed_data)
                        print(f"PaddleOCR结果: {result_paddle}")
                    except Exception as e:
                        print(f"PaddleOCR错误: {str(e)}")
                    
                except Exception as e:
                    print(f"预处理错误: {str(e)}")
            
            # 测试完整的识别流程
            print(f"\n--- 测试 {img_path} 完整识别流程 ---")
            try:
                result = ocr_processor._perform_ocr(img_data, 'captcha')
                print(f"完整流程识别结果: {result}")
            except Exception as e:
                print(f"完整流程识别错误: {str(e)}")
                
        except Exception as e:
            print(f"处理图片 {img_path} 时出错: {e}")
    
    print("\n验证码识别测试完成！")

if __name__ == "__main__":
    test_captcha_recognition()