#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试识别用户提供的base64图片
"""

import base64
import io
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.ocr_processor import OCRProcessor
import ddddocr
from PIL import Image

def test_base64_image():
    """
    测试识别用户提供的base64图片
    """
    # 用户提供的base64图片数据
    base64_data = "iVBORw0KGgoAAAANSUhEUgAAACgAAAASCAIAAACmfQvxAAAAAXNSR0IArs4c6QAABCxJREFUSInlVW1Mm1UUPn1bBq3UrIzWSRtI2AiNS+j7tnxMZDrYMCmVj+yHY0acLi7ID8eG/nbMwHAGCrjN8SUwYTillJlRMsOXmZl8jLjAZkOBALFQ0jYpHaXdW9re64/XvNYWjP/2w5P7457nnHufc889514OxhiehxDPhRUAeOxsbs5E0/ShQ69ERESw4NbW1uzsY4wRRVECgWC3Xbxe7/z8AsYoMTExOjr6vxJvbGx8fK78yZPfAUAikdz4+vqBA4kAMDQ0XHnpc5qmEUJCobChQaukqPAtOjo6275pd7vdALBnz54L58tPnSou/ahscnIqxDM7+2i9tu4vBWNcUfFpYdEJs9lstdpOFr/z9slijPHyyooqNf3ixUs0TTudzrNnS4/nvknTNA6TgoIig2HQ5XI5HI6qqmqSUhmNxonJSYNhkB09Pd8pSKXBMMiuAqvVRlKqsbGfGX18fEJBKk0mU2PjV5mvHWGZVlfXSEp1795PGGOTyWQ2m9ktHA4HO/f5fKrU9M7OmyHBdXV1Zx15fXt7m0WI6elpAMjISGcSoFIpuVzu7Ozj1bW1uLi4yMhIBpdK42JiYpjrOP3+mXPl59kEikSiv2+Ox+Pzo/yBQEiS9f39arU6uHp4f5jNYrGYz+czekREhFgstlgssfv2TU09RAgRBAEACCGapu12OwCUlZWK9opgJ5mbM7lcWxRFBoO/PXq0tLR8ubo6GCQ2nz59USgMhgQCvufZs6ysLKfT2dLaxoDXrl13u93+gB8A3ispyc9/K5wVIXTlypcUSYbUYJ9OL5fL5fLkYJDnDwQ4xD+6meAQBIeTmflqUWFhU1Pz7dvfA4BMJk1KSop+4d9apabmi+WVlVvdXcHg5qZraHj4k4oLIc48gUDg8XiCoS23WygUAkBl5WcaTZ7RaJS8JMnJzs4vKJLJpLuxNjW33B0wtDTfkErjgvG7AwMAoNHkhRLLpFKr1er3+3k8HgD4fD673Z6QkMCY09JS09JSAWB9fd1msykUih1Zv+3qam/vuHq1MSUlJcTUr+8/dixnh1dlfmFBQSrHxyeYKn/w4FeSUlmttpB+qKqqVudpAoEAxnhpaclisbCm3l6dKjX9/v1fwlt8ZmZGQSqnph6Gm3hJBw8qFCm1tXVabS0AaLX1ubnHJRKx1+vV9ekPZ2QAwJ07P+r69A0NWqbC3y05/fL+/TrdDwAwOjpWfbkmT632bnuHR0aYw8iTk2UyGQDo+vRSqZTJWahgjM1mc2HRCQWpVJDKD8586HQ6McYej+eNozkMmKfJHxkZZYNtbW3r7dUx8zptPeMTPLpv9WCMXS5XxuHM1ta28ONijDnMt4gQWlxcjIqKio+PZ2NCCNntdi6XGxsbu1tNIYQCYc8Fl8slCMLv9zscGyLR3uB3gxXO/+4//hOnjogUT/TcKQAAAABJRU5ErkJggg=="
    
    print("=== 测试识别base64图片 ===")
    
    try:
        # 解码base64数据
        image_data = base64.b64decode(base64_data)
        print(f"成功解码base64数据，图片大小: {len(image_data)} 字节")
        
        # 保存图片以便查看
        with open("test_base64_image.png", "wb") as f:
            f.write(image_data)
        print("图片已保存为: test_base64_image.png")
        
        # 使用PIL查看图片信息
        image = Image.open(io.BytesIO(image_data))
        print(f"图片尺寸: {image.size}")
        print(f"图片模式: {image.mode}")
        
    except Exception as e:
        print(f"解码base64数据失败: {e}")
        return
    
    print("\n=== 方法1: 使用OCRProcessor识别 ===")
    try:
        # 使用我们的OCRProcessor
        processor = OCRProcessor()
        result1 = processor._ddddocr_recognize(image_data, 'captcha')
        print(f"OCRProcessor识别结果: '{result1}'")
    except Exception as e:
        print(f"OCRProcessor识别失败: {e}")
        result1 = None
    
    print("\n=== 方法2: 直接使用ddddocr识别 ===")
    try:
        # 直接使用ddddocr
        ocr = ddddocr.DdddOcr(show_ad=False)
        result2 = ocr.classification(image_data)
        print(f"ddddocr直接识别结果: '{result2}'")
    except Exception as e:
        print(f"ddddocr直接识别失败: {e}")
        result2 = None
    
    print("\n=== 方法3: ddddocr概率模式识别 ===")
    try:
        ocr = ddddocr.DdddOcr(show_ad=False)
        result3 = ocr.classification(image_data, probability=True)
        
        if isinstance(result3, dict) and 'probability' in result3:
            probabilities = result3['probability']
            charsets = result3['charsets']
            
            print(f"识别到 {len(probabilities)} 个字符位置")
            print(f"字符集: {charsets}")
            
            # 提取最可能的字符
            final_result = ""
            for i, prob_list in enumerate(probabilities):
                if prob_list:
                    max_prob = max(prob_list)
                    max_idx = prob_list.index(max_prob)
                    char = charsets[max_idx]
                    print(f"位置{i+1}: '{char}' (置信度: {max_prob:.3f})")
                    if max_prob > 0.01 and char.strip():
                        final_result += char
            
            print(f"概率模式最终结果: '{final_result}'")
        else:
            print(f"概率模式结果: {result3}")
            
    except Exception as e:
        print(f"ddddocr概率模式识别失败: {e}")
    
    print("\n=== 方法4: 不同字符集设置 ===")
    try:
        ocr = ddddocr.DdddOcr(show_ad=False)
        
        # 测试不同的字符集设置
        ranges_to_test = [
            (0, "数字+小写字母"),
            (1, "数字+小写+大写字母"),
            (2, "数字+小写+大写+符号"),
            (3, "小写字母"),
            (4, "大写字母"),
            (5, "数字"),
            (6, "小写+大写字母"),
            (7, "数字+大写字母")
        ]
        
        for range_val, desc in ranges_to_test:
            try:
                ocr.set_ranges(range_val)
                result = ocr.classification(image_data)
                print(f"字符集{range_val}({desc}): '{result}'")
            except Exception as e:
                print(f"字符集{range_val}识别失败: {e}")
                
    except Exception as e:
        print(f"字符集测试失败: {e}")
    
    print("\n=== 识别结果总结 ===")
    print("请检查上述不同方法的识别结果，看哪种方法效果最好")

if __name__ == "__main__":
    test_base64_image()