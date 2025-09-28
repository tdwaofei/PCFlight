#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证码识别测试脚本 - 使用ddddocr
用于测试ddddocr的OCR识别功能
"""

import os
import sys
import base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入ddddocr
try:
    import ddddocr
    DDDDOCR_AVAILABLE = True
    print("ddddocr库导入成功")
except ImportError:
    DDDDOCR_AVAILABLE = False
    print("ddddocr库未安装，请先安装: pip install ddddocr")

def test_ddddocr_recognition():
    """
    测试ddddocr验证码识别功能 - 使用字符范围限定
    """
    print("=== 测试ddddocr验证码识别功能 ===")
    
    if not DDDDOCR_AVAILABLE:
        print("ddddocr库不可用，请先安装")
        return
    
    # 初始化ddddocr - 尝试不同的模式和字符范围设置
    ocr_configs = [
        ("默认模式", {}, None),
        ("小写字母限定", {"show_ad": False}, "abcdefghijklmnopqrstuvwxyz"),
        ("小写+大写字母限定", {"show_ad": False}, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        ("小写字母+数字限定", {"show_ad": False}, "abcdefghijklmnopqrstuvwxyz0123456789"),
    ]
    
    best_results = {}
    
    for config_name, config_params, char_range in ocr_configs:
        print(f"\n--- 测试 {config_name} ---")
        try:
            ocr = ddddocr.DdddOcr(**config_params)
            
            # 如果指定了字符范围，设置范围限定
            if char_range:
                ocr.set_ranges(char_range)
                print(f"设置字符范围: {char_range}")
            
            print(f"{config_name} 初始化成功")
            
            # 测试图片文件列表
            test_images = [
                "captcha1.png",
                "captcha2.png", 
                "captcha3.png",
                "captcha4.png"
            ]
            
            # 检查图片是否存在
            available_images = []
            for img_path in test_images:
                if os.path.exists(img_path):
                    available_images.append(img_path)
            
            if not available_images:
                print("未找到测试图片文件")
                continue
            
            # 对每个图片进行测试
            results = {}
            for img_path in available_images:
                try:
                    # 读取图片文件
                    with open(img_path, "rb") as f:
                        image_data = f.read()
                    
                    # 使用ddddocr识别
                    result = ocr.classification(image_data)
                    results[img_path] = result
                    print(f"{img_path}: '{result}'")
                    
                except Exception as e:
                    print(f"处理图片 {img_path} 时出错: {e}")
                    results[img_path] = None
            
            # 保存这个配置的结果
            best_results[config_name] = results
            
        except Exception as e:
            print(f"{config_name} 初始化失败: {e}")
            continue
    
    # 汇总最佳结果
    print(f"\n=== 识别结果汇总 ===")
    expected_results = {
        "captcha1.png": "lyjp",
        "captcha2.png": "lxzd", 
        "captcha3.png": "xlok",
        "captcha4.png": "vgsj"
    }
    
    for config_name, results in best_results.items():
        print(f"\n{config_name} 结果:")
        correct_count = 0
        total_count = 0
        
        for img_path, actual_result in results.items():
            expected = expected_results.get(img_path, "未知")
            total_count += 1
            
            if actual_result == expected:
                print(f"✅ {img_path}: '{actual_result}' (正确)")
                correct_count += 1
            else:
                print(f"❌ {img_path}: '{actual_result}' (期望: '{expected}')")
        
        accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
        print(f"识别准确率: {correct_count}/{total_count} ({accuracy:.1f}%)")
    
    print("\nddddocr验证码识别测试完成！")
    return best_results

def test_ddddocr_with_preprocessing():
    """
    测试ddddocr结合预处理的识别效果
    """
    print("\n=== 测试ddddocr结合预处理 ===")
    
    if not DDDDOCR_AVAILABLE:
        print("ddddocr库不可用")
        return
    
    # 初始化ddddocr
    try:
        ocr = ddddocr.DdddOcr()
    except Exception as e:
        print(f"ddddocr初始化失败: {e}")
        return
    
    # 简单的预处理函数
    def simple_preprocess(image_path):
        """
        简单的图片预处理
        """
        try:
            img = Image.open(image_path)
            
            # 转换为灰度图
            if img.mode != 'L':
                img = img.convert('L')
            
            # 放大图片
            scale_factor = 3
            new_size = (img.width * scale_factor, img.height * scale_factor)
            img = img.resize(new_size, Image.LANCZOS)
            
            # 保存预处理后的图片
            processed_path = f"processed_{os.path.basename(image_path)}"
            img.save(processed_path)
            
            # 转换为字节数据
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue(), processed_path
            
        except Exception as e:
            print(f"预处理失败: {e}")
            return None, None
    
    test_images = ["captcha2.png"]  # 重点测试captcha2.png
    
    for img_path in test_images:
        if not os.path.exists(img_path):
            continue
            
        print(f"\n--- 测试 {img_path} ---")
        
        # 原始图片识别
        try:
            with open(img_path, "rb") as f:
                original_data = f.read()
            original_result = ocr.classification(original_data)
            print(f"原始图片识别: '{original_result}'")
        except Exception as e:
            print(f"原始图片识别失败: {e}")
            original_result = None
        
        # 预处理后识别
        try:
            processed_data, processed_path = simple_preprocess(img_path)
            if processed_data:
                processed_result = ocr.classification(processed_data)
                print(f"预处理后识别: '{processed_result}' (预处理图片: {processed_path})")
            else:
                processed_result = None
        except Exception as e:
            print(f"预处理后识别失败: {e}")
            processed_result = None
        
        # 比较结果
        expected = "lxzd"  # captcha2.png的期望结果
        print(f"期望结果: '{expected}'")
        
        if original_result == expected:
            print("✅ 原始图片识别正确")
        elif processed_result == expected:
            print("✅ 预处理后识别正确")
        else:
            print("❌ 两种方法都未能正确识别")

def test_ddddocr_with_probability():
    """
    测试ddddocr的概率模式和更多预处理方法
    """
    print("\n=== 测试ddddocr概率模式和预处理 ===")
    
    if not DDDDOCR_AVAILABLE:
        print("ddddocr库不可用")
        return
    
    try:
        # 初始化ddddocr并设置字符范围
        ocr = ddddocr.DdddOcr(show_ad=False)
        ocr.set_ranges("abcdefghijklmnopqrstuvwxyz")
        print("ddddocr初始化成功，设置小写字母范围")
        
        # 重点测试captcha2.png
        test_image = "captcha2.png"
        if not os.path.exists(test_image):
            print(f"测试图片 {test_image} 不存在")
            return
        
        print(f"\n--- 测试 {test_image} ---")
        
        # 1. 原始图片测试
        with open(test_image, "rb") as f:
            original_data = f.read()
        
        # 普通识别
        result_normal = ocr.classification(original_data)
        print(f"普通识别: '{result_normal}'")
        
        # 概率识别
        try:
            result_prob = ocr.classification(original_data, probability=True)
            print(f"概率识别结果类型: {type(result_prob)}")
            if isinstance(result_prob, dict) and 'probability' in result_prob:
                # 获取概率最高的字符组合
                prob_chars = result_prob['probability']
                if isinstance(prob_chars, list) and len(prob_chars) > 0:
                    # 构建最可能的4个字符
                    best_chars = []
                    for char_probs in prob_chars[:4]:  # 取前4个位置
                        if isinstance(char_probs, dict):
                            # 找到概率最高的字符
                            best_char = max(char_probs.items(), key=lambda x: x[1])
                            best_chars.append(best_char[0])
                    
                    if len(best_chars) == 4:
                        prob_result = ''.join(best_chars)
                        print(f"概率模式识别: '{prob_result}'")
                    else:
                        print(f"概率模式字符数不足: {len(best_chars)}")
                else:
                    print("概率数据格式异常")
            else:
                print(f"概率识别返回: {result_prob}")
        except Exception as e:
            print(f"概率识别失败: {e}")
        
        # 2. 多种预处理方法测试
        preprocess_methods = [
            ("灰度+放大", lambda img: img.convert('L').resize((img.width*4, img.height*4), Image.LANCZOS)),
            ("灰度+放大+锐化", lambda img: img.convert('L').resize((img.width*4, img.height*4), Image.LANCZOS).filter(ImageFilter.SHARPEN)),
            ("灰度+放大+边缘增强", lambda img: img.convert('L').resize((img.width*4, img.height*4), Image.LANCZOS).filter(ImageFilter.EDGE_ENHANCE)),
        ]
        
        for method_name, preprocess_func in preprocess_methods:
            try:
                print(f"\n--- {method_name} ---")
                
                # 加载并预处理图片
                img = Image.open(test_image)
                processed_img = preprocess_func(img)
                
                # 保存预处理后的图片
                debug_path = f"dddd_debug_{method_name.replace('+', '_')}.png"
                processed_img.save(debug_path)
                print(f"预处理图片保存: {debug_path}")
                
                # 转换为字节数据
                buffer = io.BytesIO()
                processed_img.save(buffer, format='PNG')
                processed_data = buffer.getvalue()
                
                # 识别
                result = ocr.classification(processed_data)
                print(f"识别结果: '{result}'")
                
                # 检查是否正确
                if result == "lxzd":
                    print("✅ 识别正确！")
                    return result
                
            except Exception as e:
                print(f"{method_name} 处理失败: {e}")
        
        print("\n所有方法测试完成")
        
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    # 测试基本的ddddocr功能
    results = test_ddddocr_recognition()
    
    # 测试概率模式和更多预处理方法
    test_ddddocr_with_probability()
    
    # 测试结合预处理的效果
    test_ddddocr_with_preprocessing()