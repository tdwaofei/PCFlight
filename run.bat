@echo off
chcp 65001 >nul
echo ========================================
echo 航班数据爬虫系统 v1.0.0
echo ========================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

:: 检查是否存在虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo 激活虚拟环境...
    call venv\Scripts\activate.bat
)

:: 检查依赖是否安装
if not exist "modules\__init__.py" (
    echo 错误: 项目模块未找到，请确认在正确的目录下运行
    pause
    exit /b 1
)

:: 显示菜单
:menu
echo.
echo 请选择操作:
echo 1. 创建示例输入文件
echo 2. 运行爬虫程序（使用示例文件）
echo 3. 运行爬虫程序（指定输入文件）
echo 4. 查看帮助信息
echo 5. 安装依赖包
echo 6. 退出
echo.
set /p choice=请输入选项 (1-6): 

if "%choice%"=="1" goto create_sample
if "%choice%"=="2" goto run_sample
if "%choice%"=="3" goto run_custom
if "%choice%"=="4" goto show_help
if "%choice%"=="5" goto install_deps
if "%choice%"=="6" goto exit

echo 无效选项，请重新选择
goto menu

:create_sample
echo.
echo 正在创建示例输入文件...
python main.py --sample
if errorlevel 1 (
    echo 创建失败，请检查错误信息
) else (
    echo 示例文件创建成功！
    echo 请编辑 input\sample_flights.xlsx 文件，填入要查询的航班信息
)
pause
goto menu

:run_sample
echo.
if not exist "input\sample_flights.xlsx" (
    echo 示例文件不存在，正在创建...
    python main.py --sample
    if errorlevel 1 (
        echo 创建示例文件失败
        pause
        goto menu
    )
    echo 请先编辑 input\sample_flights.xlsx 文件，填入要查询的航班信息
    pause
    goto menu
)

echo 正在运行爬虫程序...
echo 输入文件: input\sample_flights.xlsx
echo.
python main.py -i input\sample_flights.xlsx
echo.
echo 程序运行完成！
echo 请查看 output\ 目录下的结果文件
echo 详细日志请查看 logs\ 目录
pause
goto menu

:run_custom
echo.
set /p input_file=请输入Excel文件路径: 
if "%input_file%"=="" (
    echo 未指定输入文件
    pause
    goto menu
)

if not exist "%input_file%" (
    echo 文件不存在: %input_file%
    pause
    goto menu
)

echo.
echo 正在运行爬虫程序...
echo 输入文件: %input_file%
echo.
python main.py -i "%input_file%"
echo.
echo 程序运行完成！
echo 请查看 output\ 目录下的结果文件
echo 详细日志请查看 logs\ 目录
pause
goto menu

:show_help
echo.
python main.py --help
echo.
pause
goto menu

:install_deps
echo.
echo 正在安装依赖包...
echo 这可能需要几分钟时间，请耐心等待...
echo.
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo 依赖安装失败，请检查网络连接或手动安装
    echo 可以尝试使用国内镜像源:
    echo pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
) else (
    echo.
    echo 依赖安装完成！
)
pause
goto menu

:exit
echo.
echo 感谢使用航班数据爬虫系统！
echo.
pause
exit /b 0