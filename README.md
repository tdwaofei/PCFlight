# 航班数据爬虫系统

一个基于Python的自动化航班数据爬取系统，支持批量查询航班信息并导出到Excel文件。

## 功能特性

- 📊 **批量处理**: 支持从Excel文件批量读取航班信息进行查询
- 🤖 **自动化操作**: 自动填写查询表单、处理验证码、提取数据
- 🔍 **OCR识别**: 支持验证码和时间图片的OCR识别（带重试机制）
- ✈️ **多航段支持**: 自动识别和提取多航段航班数据
- 📈 **数据导出**: 将结果保存为格式化的Excel文件，并生成统计报告
- 📝 **完整日志**: 详细的日志记录，支持按天分割
- ⚙️ **灵活配置**: 支持自定义配置文件，可调整各种参数

## 系统要求

- Python 3.7+
- Windows 操作系统
- Chrome 浏览器
- 至少 2GB 可用内存

## 安装步骤

### 1. 克隆项目

```bash
git clone <项目地址>
cd PCFlight
```

### 2. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 3. 安装Chrome浏览器

确保系统已安装Chrome浏览器，系统会自动下载对应的ChromeDriver。

### 4. 安装OCR依赖（可选）

#### Tesseract OCR

1. 下载并安装 [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
2. 将安装路径添加到系统环境变量PATH中
3. 默认路径通常为：`C:\Program Files\Tesseract-OCR`

#### PaddleOCR（推荐）

```bash
pip install paddlepaddle paddleocr
```

#### DdddOCR（轻量级验证码识别）

DdddOCR是一个轻量级的通用验证码识别库，特别适用于验证码识别场景。<mcreference link="https://github.com/tdwaofei/ddddocr.git" index="0">0</mcreference>

```bash
pip install ddddocr
```

**特点**：
- 无需额外配置，开箱即用
- 专门针对验证码识别优化
- 支持多种验证码类型（数字、字母、混合）
- 轻量级，依赖少

**使用建议**：
- 对于简单的数字或字母验证码，推荐使用DdddOCR
- 对于复杂的文本识别，推荐使用PaddleOCR
- 系统会根据配置自动选择合适的OCR引擎

## 项目结构

```
PCFlight/
├── main.py                 # 主程序入口
├── config.json            # 系统配置文件
├── requirements.txt       # Python依赖包
├── README.md             # 项目说明文档
├── modules/              # 功能模块目录
│   ├── __init__.py
│   ├── logger.py         # 日志系统
│   ├── config_manager.py # 配置管理
│   ├── input_handler.py  # Excel输入处理
│   ├── web_automation.py # 网页自动化
│   ├── ocr_processor.py  # OCR识别
│   ├── data_extractor.py # 数据提取
│   └── output_handler.py # Excel输出处理
├── input/                # 输入文件目录
├── output/               # 输出文件目录
└── logs/                 # 日志文件目录
```

## 使用方法

### 1. 创建示例输入文件

```bash
python main.py --sample
```

这将在 `input/` 目录下创建 `sample_flights.xlsx` 示例文件。

### 2. 编辑输入文件

打开生成的示例文件，按以下格式填入要查询的航班信息：

| 航班号 | 出发日期 |
|--------|----------|
| CA1234 | 2024-01-15 |
| MU5678 | 2024-01-16 |

### 3. 运行爬虫程序

#### 基本用法

```bash
# 使用默认输出文件名
python main.py -i input/sample_flights.xlsx

# 指定输出文件名
python main.py -i input/sample_flights.xlsx -o output/my_results.xlsx
```

#### 高级用法

```bash
# 使用自定义配置文件
python main.py -c config/custom.json -i input/flights.xlsx

# 查看帮助信息
python main.py --help

# 查看版本信息
python main.py --version
```

### 4. 查看结果

程序运行完成后，会在 `output/` 目录下生成：

- **数据文件**: `flight_data_YYYYMMDD_HHMMSS.xlsx` - 包含提取的航班数据
- **汇总报告**: `flight_summary_YYYYMMDD_HHMMSS.xlsx` - 包含统计信息
- **日志文件**: `logs/flight_crawler_YYYY-MM-DD.log` - 详细的运行日志

## 配置说明

系统配置文件 `config.json` 包含以下主要配置项：

### 浏览器配置

```json
{
  "browser": {
    "headless": false,          // 是否无头模式运行
    "window_size": "1920,1080", // 浏览器窗口大小
    "user_agent": "",           // 自定义User-Agent
    "page_load_timeout": 30,    // 页面加载超时时间
    "implicit_wait": 10         // 隐式等待时间
  }
}
```

### OCR配置

```json
{
  "ocr": {
    "engine": "paddleocr",      // OCR引擎: tesseract、paddleocr 或 ddddocr
    "tesseract_path": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
    "language": "eng",          // 识别语言
    "confidence_threshold": 60, // 置信度阈值
    "ddddocr_beta": false       // DdddOCR是否使用beta模型
  }
}
```

### 重试配置

```json
{
  "retry": {
    "max_attempts": 3,          // 最大重试次数
    "captcha_max_attempts": 5,  // 验证码最大重试次数
    "time_image_max_attempts": 3, // 时间图片最大重试次数
    "delay_between_attempts": 2, // 重试间隔（秒）
    "page_load_delay": 3,       // 页面加载延迟
    "flight_delay": 2           // 航班查询间隔
  }
}
```

## 输出数据格式

生成的Excel文件包含以下字段：

| 字段名 | 说明 |
|--------|------|
| 航班号 | 航班编号 |
| 出发日期 | 查询的出发日期 |
| 航段序号 | 航段编号（多航段时使用） |
| 出发机场 | 出发机场代码/名称 |
| 到达机场 | 到达机场代码/名称 |
| 计划起飞时间 | 计划起飞时间 |
| 计划到达时间 | 计划到达时间 |
| 实际起飞时间 | 实际起飞时间（OCR识别） |
| 实际到达时间 | 实际到达时间（OCR识别） |
| 航班状态 | 航班当前状态 |
| 数据获取时间 | 数据提取的时间戳 |

## 故障排除

### 常见问题

#### 1. ChromeDriver版本不匹配

**错误信息**: `This version of ChromeDriver only supports Chrome version XX`

**解决方案**: 
- 更新Chrome浏览器到最新版本
- 或者手动下载匹配的ChromeDriver版本

#### 2. OCR识别失败

**错误信息**: `OCR识别失败` 或识别结果为空

**解决方案**:
- 检查Tesseract是否正确安装并添加到PATH
- 尝试使用PaddleOCR引擎：修改配置文件中的 `ocr.engine` 为 `paddleocr`
- 尝试使用DdddOCR引擎：修改配置文件中的 `ocr.engine` 为 `ddddocr`（特别适用于验证码识别）
- 调整OCR置信度阈值

#### 3. 验证码处理失败

**解决方案**:
- 增加验证码重试次数：修改 `retry.captcha_max_attempts`
- 调整重试间隔：修改 `retry.delay_between_attempts`
- 检查网络连接是否稳定

#### 4. 页面元素找不到

**错误信息**: `NoSuchElementException`

**解决方案**:
- 检查目标网站是否更新了页面结构
- 更新配置文件中的XPath路径
- 增加页面加载等待时间

### 日志分析

系统会生成详细的日志文件，位于 `logs/` 目录下。日志级别包括：

- **INFO**: 正常运行信息
- **WARNING**: 警告信息（如OCR识别失败）
- **ERROR**: 错误信息（如页面加载失败）
- **DEBUG**: 调试信息（需要在配置中启用）

## 性能优化建议

1. **并发处理**: 目前系统采用串行处理，如需提高效率可考虑实现多线程处理
2. **缓存机制**: 对于重复查询的航班，可以实现缓存机制
3. **代理支持**: 在网络环境受限时，可以添加代理服务器支持
4. **数据库存储**: 对于大量数据，可以考虑使用数据库替代Excel文件

## 注意事项

1. **合规使用**: 请确保遵守目标网站的使用条款和robots.txt规定
2. **频率控制**: 避免过于频繁的请求，建议在配置中设置适当的延迟
3. **数据准确性**: OCR识别可能存在误差，建议对重要数据进行人工核验
4. **网络稳定性**: 确保网络连接稳定，避免在网络不稳定时运行

## 更新日志

### v1.0.0 (2024-01-XX)

- 初始版本发布
- 支持基本的航班数据爬取功能
- 实现OCR验证码识别
- 支持多航段数据提取
- 完整的日志和配置系统

## 技术支持

如果在使用过程中遇到问题，请：

1. 查看日志文件获取详细错误信息
2. 检查配置文件是否正确
3. 确认所有依赖包已正确安装
4. 参考本文档的故障排除部分

## 许可证

本项目仅供学习和研究使用，请勿用于商业用途。

---

**免责声明**: 本工具仅用于技术学习和研究目的。使用者应当遵守相关法律法规和网站使用条款，对使用本工具产生的任何后果承担全部责任。