# 测试文件夹

本文件夹包含航班数据爬虫系统的各种测试脚本。

## 测试文件说明

### OCR相关测试
- `test_integrated_ocr.py` - 测试集成ddddocr后的OCR处理器
- `test_ocr.py` - 基础OCR功能测试
- `test_captcha2_ddddocr.py` - 专门测试ddddocr对captcha2的识别
- `test_captcha2_only.py` - 单独测试captcha2图片

### 数据验证测试
- `test_flight_number_validation.py` - 航班号格式验证测试
- `test_basic.py` - 基础功能测试

## 运行测试

在项目根目录下运行：
```bash
cd test
py test_flight_number_validation.py
py test_integrated_ocr.py
```

或者从项目根目录运行：
```bash
py test/test_flight_number_validation.py
py test/test_integrated_ocr.py
```

## 注意事项

- 所有测试脚本都已配置正确的路径引用
- OCR测试需要相应的验证码图片文件（位于项目根目录）
- 测试结果会显示详细的成功/失败信息和统计数据