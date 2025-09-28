#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试ddddocr识别captcha2.jpg - 深度分析版
目标：识别出完整的4个字符 "lxzd"
"""

import ddddocr
from PIL import Image
import io

def analyze_probability_result(result, method_name):
    """
    深度分析概率识别结果
    
    Args:
        result: ddddocr返回的概率结果
        method_name: 方法名称
    """
    print(f"\n=== {method_name} 详细分析 ===")
    
    if 'probability' not in result or 'charsets' not in result:
        print("概率数据格式异常")
        return ""
    
    probabilities = result['probability']
    charsets = result['charsets']
    
    print(f"字符集: {charsets}")
    print(f"识别到 {len(probabilities)} 个字符位置")
    
    # 找出有意义的字符位置（置信度 > 0.01）
    meaningful_chars = []
    final_result = ""
    
    for i, prob_list in enumerate(probabilities):
        if not prob_list:
            continue
            
        max_prob = max(prob_list)
        max_idx = prob_list.index(max_prob)
        char = charsets[max_idx]
        
        # 显示前3个最可能的字符
        sorted_probs = sorted(enumerate(prob_list), key=lambda x: x[1], reverse=True)
        top3 = sorted_probs[:3]
        
        print(f"位置{i+1:2d}: ", end="")
        for j, (char_idx, prob) in enumerate(top3):
            if prob > 0.001:  # 只显示概率大于0.001的
                print(f"'{charsets[char_idx]}'({prob:.3f})", end=" ")
        print()
        
        # 如果置信度足够高，认为是有意义的字符
        if max_prob > 0.01:
            meaningful_chars.append((i+1, char, max_prob))
            if char.strip():  # 非空字符
                final_result += char
    
    print(f"\n有意义的字符位置:")
    for pos, char, prob in meaningful_chars:
        print(f"  位置{pos}: '{char}' (置信度: {prob:.3f})")
    
    print(f"最终结果: '{final_result}'")
    return final_result

def test_captcha2_with_ddddocr():
    """
    使用ddddocr识别captcha2.jpg，深度分析识别过程
    """
    print("=== 测试ddddocr识别captcha2.jpg - 深度分析 ===")
    
    # 初始化ddddocr
    ocr = ddddocr.DdddOcr(show_ad=False)
    
    # 读取图片
    image_path = "textImg1.png"
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        print(f"成功读取图片: {image_path}")
    except FileNotFoundError:
        print(f"图片文件不存在: {image_path}")
        return
    
    # 方法1: 使用set_ranges(1) - 仅小写英文字母
    print("\n" + "="*50)
    print("方法1: set_ranges(1) 仅小写英文字母")
    try:
        ocr.set_ranges(0)
        result1 = ocr.classification(image_data, probability=True)
        result1_str = analyze_probability_result(result1, "方法1")
    except Exception as e:
        print(f"方法1失败: {e}")
        result1_str = ""
    
    # 方法2: 使用set_ranges(3) - 小写+大写英文字母
    print("\n" + "="*50)
    print("方法2: set_ranges(3) 小写+大写英文字母")
    try:
        ocr.set_ranges(6)
        result2 = ocr.classification(image_data, probability=True)
        result2_str = analyze_probability_result(result2, "方法2")
    except Exception as e:
        print(f"方法2失败: {e}")
        result2_str = ""
    
    # 方法3: 尝试提取4个最可能的字符位置
    print("\n" + "="*50)
    print("方法3: 智能提取4个字符")
    try:
        ocr.set_ranges(0)
        result3 = ocr.classification(image_data, probability=True)
        
        if 'probability' in result3 and 'charsets' in result3:
            probabilities = result3['probability']
            charsets = result3['charsets']
            
            # 找出置信度最高的4个字符位置
            char_candidates = []
            for i, prob_list in enumerate(probabilities):
                if prob_list:
                    max_prob = max(prob_list)
                    max_idx = prob_list.index(max_prob)
                    char = charsets[max_idx]
                    if char.strip() and max_prob > 0.005:  # 非空字符且置信度足够
                        char_candidates.append((i, char, max_prob))
            
            # 按置信度排序，取前4个
            char_candidates.sort(key=lambda x: x[2], reverse=True)
            top4 = char_candidates[:4]
            
            # 按位置排序
            top4.sort(key=lambda x: x[0])
            
            result3_str = ''.join([char for _, char, _ in top4])
            
            print("候选字符:")
            for pos, char, prob in char_candidates:
                print(f"  位置{pos+1}: '{char}' (置信度: {prob:.3f})")
            
            print(f"\n选择的前4个字符: {top4}")
            print(f"方法3结果: '{result3_str}'")
        else:
            result3_str = ""
            
    except Exception as e:
        print(f"方法3失败: {e}")
        result3_str = ""
    
    # 总结
    print("\n" + "="*50)
    print("=== 识别结果总结 ===")
    print(f"期望结果: 'vgsj'")
    print(f"方法1结果: '{result1_str}'")
    print(f"方法2结果: '{result2_str}'")
    print(f"方法3结果: '{result3_str}'")
    
    # 检查哪个结果最接近
    target = "vgsj"
    results = [
        ("方法1", result1_str),
        ("方法2", result2_str), 
        ("方法3", result3_str)
    ]
    
    best_match = ""
    best_score = 0
    best_method = ""
    
    for method, result in results:
        if result:
            # 计算匹配度
            score = sum(1 for i, char in enumerate(result) if i < len(target) and char == target[i])
            if score > best_score:
                best_score = score
                best_match = result
                best_method = method
    
    if best_match:
        print(f"\n最佳结果: {best_method} - '{best_match}' (匹配度: {best_score}/4)")
    else:
        print("\n所有方法都未能识别出有效结果")

if __name__ == "__main__":
    test_captcha2_with_ddddocr()
