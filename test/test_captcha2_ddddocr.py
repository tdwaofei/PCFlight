#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试ddddocr识别验证码图片 - 批量测试版
目标：批量测试output/captchaimage/下的所有验证码图片，统计识别成功率
"""

import ddddocr
from PIL import Image
import io
import os
import glob
from collections import defaultdict

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

def test_single_captcha(image_path, ocr):
    """
    测试单个验证码图片的识别
    
    Args:
        image_path: 图片路径
        ocr: ddddocr实例
        
    Returns:
        dict: 包含识别结果的字典
    """
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # 使用三种方法进行识别
        results = {}
        
        # 方法1: 仅小写英文字母
        try:
            ocr.set_ranges(0)
            result1 = ocr.classification(image_data, probability=True)
            result1_str = extract_best_result(result1)
            results['method1'] = result1_str
        except Exception as e:
            results['method1'] = ""
        
        # 方法2: 小写+大写英文字母
        try:
            ocr.set_ranges(6)
            result2 = ocr.classification(image_data, probability=True)
            result2_str = extract_best_result(result2)
            results['method2'] = result2_str
        except Exception as e:
            results['method2'] = ""
        
        # 方法3: 智能提取4个字符
        try:
            ocr.set_ranges(0)
            result3 = ocr.classification(image_data, probability=True)
            result3_str = extract_top_chars(result3, 4)
            results['method3'] = result3_str
        except Exception as e:
            results['method3'] = ""
        
        return results
        
    except Exception as e:
        print(f"处理图片 {image_path} 时出错: {e}")
        return {'method1': '', 'method2': '', 'method3': ''}

def extract_best_result(result):
    """
    从概率结果中提取最佳识别结果
    
    Args:
        result: ddddocr返回的概率结果
        
    Returns:
        str: 识别出的字符串
    """
    if 'probability' not in result or 'charsets' not in result:
        return ""
    
    probabilities = result['probability']
    charsets = result['charsets']
    
    final_result = ""
    for prob_list in probabilities:
        if prob_list:
            max_prob = max(prob_list)
            if max_prob > 0.01:  # 置信度阈值
                max_idx = prob_list.index(max_prob)
                char = charsets[max_idx]
                if char.strip():  # 非空字符
                    final_result += char
    
    return final_result

def extract_top_chars(result, num_chars):
    """
    提取置信度最高的指定数量字符
    
    Args:
        result: ddddocr返回的概率结果
        num_chars: 要提取的字符数量
        
    Returns:
        str: 识别出的字符串
    """
    if 'probability' not in result or 'charsets' not in result:
        return ""
    
    probabilities = result['probability']
    charsets = result['charsets']
    
    # 找出置信度最高的字符位置
    char_candidates = []
    for i, prob_list in enumerate(probabilities):
        if prob_list:
            max_prob = max(prob_list)
            max_idx = prob_list.index(max_prob)
            char = charsets[max_idx]
            if char.strip() and max_prob > 0.005:  # 非空字符且置信度足够
                char_candidates.append((i, char, max_prob))
    
    # 按置信度排序，取前N个
    char_candidates.sort(key=lambda x: x[2], reverse=True)
    top_chars = char_candidates[:num_chars]
    
    # 按位置排序
    top_chars.sort(key=lambda x: x[0])
    
    return ''.join([char for _, char, _ in top_chars])

def batch_test_captcha():
    """
    批量测试验证码图片识别
    """
    print("=== 批量测试ddddocr验证码识别 ===")
    
    # 初始化ddddocr
    ocr = ddddocr.DdddOcr(show_ad=False)
    
    # 获取所有验证码图片
    captcha_dir = "../output/captchaimage"
    if not os.path.exists(captcha_dir):
        print(f"验证码图片目录不存在: {captcha_dir}")
        return
    
    image_files = glob.glob(os.path.join(captcha_dir, "*.png"))
    if not image_files:
        print(f"在 {captcha_dir} 中未找到PNG图片文件")
        return
    
    print(f"找到 {len(image_files)} 个验证码图片文件")
    
    # 统计变量
    total_files = len(image_files)
    method_stats = {
        'method1': {'total': 0, 'success': 0, 'results': []},
        'method2': {'total': 0, 'success': 0, 'results': []},
        'method3': {'total': 0, 'success': 0, 'results': []}
    }
    
    # 按航班号分组统计
    flight_stats = defaultdict(lambda: {'total': 0, 'results': []})
    
    print("\n开始批量识别...")
    print("-" * 80)
    
    for i, image_path in enumerate(image_files, 1):
        filename = os.path.basename(image_path)
        print(f"[{i:2d}/{total_files}] 处理: {filename}")
        
        # 从文件名提取航班号
        flight_number = ""
        if "captcha_" in filename:
            parts = filename.split("_")
            if len(parts) >= 2:
                flight_number = parts[1]
        
        # 识别验证码
        results = test_single_captcha(image_path, ocr)
        
        # 统计结果
        for method, result in results.items():
            method_stats[method]['total'] += 1
            method_stats[method]['results'].append((filename, result))
            
            # 判断是否成功（假设4个字符为成功）
            if len(result) == 4 and result.isalpha():
                method_stats[method]['success'] += 1
                success_flag = "[成功]"
            else:
                success_flag = "[失败]"
            
            print(f"  {method}: '{result}' {success_flag}")
        
        # 记录航班统计
        if flight_number:
            flight_stats[flight_number]['total'] += 1
            flight_stats[flight_number]['results'].append((filename, results))
        
        print()
    
    # 输出统计结果
    print("=" * 80)
    print("=== 识别结果统计 ===")
    
    for method, stats in method_stats.items():
        success_rate = (stats['success'] / stats['total']) * 100 if stats['total'] > 0 else 0
        method_name = {
            'method1': '方法1(仅小写)',
            'method2': '方法2(大小写)',
            'method3': '方法3(智能提取)'
        }[method]
        
        print(f"\n{method_name}:")
        print(f"  总数: {stats['total']}")
        print(f"  成功: {stats['success']}")
        print(f"  成功率: {success_rate:.1f}%")
    
    # 按航班号统计
    print("\n=== 按航班号统计 ===")
    for flight_number, stats in flight_stats.items():
        print(f"\n航班 {flight_number}: {stats['total']} 个验证码")
        
        # 统计该航班各方法的成功率
        flight_method_stats = {'method1': 0, 'method2': 0, 'method3': 0}
        for filename, results in stats['results']:
            for method, result in results.items():
                if len(result) == 4 and result.isalpha():
                    flight_method_stats[method] += 1
        
        for method, success_count in flight_method_stats.items():
            success_rate = (success_count / stats['total']) * 100 if stats['total'] > 0 else 0
            method_name = {
                'method1': '方法1',
                'method2': '方法2', 
                'method3': '方法3'
            }[method]
            print(f"  {method_name}: {success_count}/{stats['total']} ({success_rate:.1f}%)")
    
    # 找出最佳方法
    best_method = max(method_stats.keys(), key=lambda x: method_stats[x]['success'])
    best_success_rate = (method_stats[best_method]['success'] / method_stats[best_method]['total']) * 100
    
    print(f"\n=== 总结 ===")
    print(f"最佳识别方法: {best_method} (成功率: {best_success_rate:.1f}%)")
    print(f"总共处理: {total_files} 个验证码图片")
    
    # 显示识别失败的图片
    print(f"\n=== 识别困难的图片 ===")
    failed_files = []
    for method, stats in method_stats.items():
        for filename, result in stats['results']:
            if not (len(result) == 4 and result.isalpha()):
                if filename not in [f[0] for f in failed_files]:
                    failed_files.append((filename, {}))
    
    # 收集所有方法对失败图片的识别结果
    for filename, _ in failed_files:
        all_results = {}
        for method, stats in method_stats.items():
            for fn, result in stats['results']:
                if fn == filename:
                    all_results[method] = result
                    break
        failed_files = [(fn, all_results) if fn == filename else (fn, res) for fn, res in failed_files]
    
    if failed_files:
        print("以下图片所有方法都识别困难:")
        for filename, results in failed_files:
            print(f"  {filename}:")
            for method, result in results.items():
                print(f"    {method}: '{result}'")
    else:
        print("所有图片都至少有一种方法能够成功识别!")

if __name__ == "__main__":
    batch_test_captcha()
