#!/usr/bin/env python3
"""SocialSight 打包脚本 - PyInstaller"""

import os
import sys
import shutil
import subprocess

# 项目根目录
ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(ROOT, "dist", "SocialSight")

def main():
    print("=" * 50)
    print("  SocialSight 打包工具")
    print("=" * 50)
    
    # 清理旧构建
    for d in ["build", "dist"]:
        p = os.path.join(ROOT, d)
        if os.path.exists(p):
            print(f"清理 {d}...")
            shutil.rmtree(p)
    
    # 确保 templates 存在
    templates_dir = os.path.join(ROOT, "templates")
    if not os.path.exists(templates_dir):
        print("❌ 找不到 templates 目录")
        return
    
    # 运行 PyInstaller
    print("\n打包中...")
    # 先清空 cookies.json
    empty_cookies = os.path.join(ROOT, "cookies.json")
    with open(empty_cookies, "w", encoding="utf-8") as f:
        f.write("{}")
    
    add_data = f"templates{os.pathsep}templates"
    # 如果存在 cookies.json 且不为空，不打包它
    # 打包时只打包 templates
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "SocialSight",
        "--onedir",
        "--console",
        "--add-data", add_data,
        "--hidden-import", "playwright",
        "--hidden-import", "flask",
        "--hidden-import", "requests",
        "--hidden-import", "json",
        "--hidden-import", "threading",
        "--hidden-import", "uuid",
        "--collect-all", "playwright",
        "--collect-all", "flask",
        os.path.join(ROOT, "app.py"),
    ]
    
    result = subprocess.run(cmd, cwd=ROOT, capture_output=False)
    if result.returncode != 0:
        print(f"\n❌ 打包失败 (exit code: {result.returncode})")
        return
    
    # 创建启动脚本
    print("\n创建启动脚本...")
    bat_content = """@echo off
chcp 65001 >nul
echo ============================================
echo   SocialSight 社交平台舆情分析系统
echo ============================================
echo.
echo 首次启动会下载浏览器组件（约300MB，国内镜像）
echo 下载进度会显示在下方窗口中，请耐心等待
echo.
echo 正在启动服务...
start /B "SocialSight" "%~dp0SocialSight.exe"

echo 等待服务就绪...
:wait
timeout /t 2 /nobreak >nul
powershell -Command "try{$c=netstat -ano|findstr :5001;if($c){exit 0}}catch{};exit 1" 2>nul
if errorlevel 1 goto wait

echo 服务已启动，正在打开浏览器...
start "" "http://127.0.0.1:5001"
echo.
echo 系统运行中，浏览器已打开
echo.
echo 按任意键退出系统...
pause >nul
taskkill /F /IM SocialSight.exe >nul 2>&1
echo 系统已退出
timeout /t 2 /nobreak >nul
exit
"""
    bat_path = os.path.join(OUTPUT, "启动系统.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    
    print(f"✅ 打包完成！")
    print(f"输出目录: {OUTPUT}")
    print(f"启动文件: {bat_path}")
    print(f"大小: {get_dir_size(OUTPUT):.1f} MB")
    print()
    print("使用说明：")
    print("1. 把整个 SocialSight 文件夹复制给对方")
    print("2. 对方双击「启动系统.bat」")
    print("3. 浏览器自动打开 http://127.0.0.1:5001")
    print("4. 首次运行会自动下载浏览器组件（约300MB，需联网）")
    print("5. 之后不需要网络，离线可用")

def get_dir_size(path):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except:
                pass
    return total / (1024 * 1024)

if __name__ == "__main__":
    main()