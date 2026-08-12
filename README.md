# SocialSight 社交平台舆情分析系统

基于真实数据的社交平台舆情分析工具，支持微博、小红书、B站、京东等多平台数据采集与情感分析。

## 功能

- **多平台数据采集**：微博（需登录）、小红书（需登录）、B站（开放API）、京东（开放API）
- **一键登录**：内置浏览器，扫码登录自动获取 Cookie，无需手动复制
- **情感分析**：基于关键词的正负面情感分析，支持否定词翻转（如"没让我失望"→正面）
- **数据可视化**：环形图、堆叠柱状图、雷达图、关键词分布图
- **完整报告**：自动生成 HTML 报告，包含所有数据原文链接
- **Cookie 持久化**：登录后自动保存，下次启动无需重新登录
- **暗色主题**：专业克制的 UI 设计

## 快速开始

### 方式一：直接下载打包版

从 [Releases](https://cnb.cool/zuringg/SocialSight/releases) 下载 `SocialSight.tar.gz`，解压后双击 `启动系统.bat` 即可。

> 首次运行会自动下载浏览器组件（约 300MB，国内镜像），用于一键登录功能。
> 如不需要一键登录，直接粘贴 Cookie 也可正常使用全部功能。

### 方式二：源码运行

```bash
# 安装依赖
pip install flask requests playwright

# 安装浏览器（用于一键登录）
playwright install chromium

# 启动
python app.py
```

打开 http://127.0.0.1:5001 即可使用。

### 方式三：打包为可执行文件

```bash
pip install pyinstaller
python build.py
```

打包产物在 `dist/SocialSight/` 目录。

## 使用说明

### 数据采集

| 平台 | 是否需要登录 | 说明 |
|------|------------|------|
| 微博 | ✅ 需要 Cookie | 支持一键登录或手动粘贴 Cookie |
| 小红书 | ✅ 需要 Cookie | 支持一键登录或手动粘贴 Cookie |
| B站 | ❌ 无需登录 | 使用开放 API，开箱即用 |
| 京东 | ❌ 无需登录 | 搜索商品评论，开箱即用 |

### 一键登录

点击平台对应的「一键登录」按钮，会弹出浏览器窗口：
- **微博**：扫码或输入账号密码登录
- **小红书**：扫码登录
- 登录成功后 Cookie 自动获取并保存，下次打开无需重新登录

### 手动粘贴 Cookie

1. 浏览器打开目标平台并登录
2. 按 F12 → Network → 复制任意请求的 Cookie 头
3. 粘贴到对应文本框

## 技术栈

- **后端**：Python + Flask
- **前端**：HTML + CSS + Chart.js
- **数据采集**：Playwright（浏览器自动化）+ Requests（HTTP）
- **打包**：PyInstaller

## 项目结构

```
SocialSight/
├── app.py                      # 主程序
├── build.py                    # 打包脚本
├── .cnb.yml                    # 云原生构建配置
├── templates/
│   └── index.html              # 前端界面
├── collectors/
│   └── xiaohongshu_browser.py  # 小红书浏览器采集器
└── reports/                    # 生成的报告
```

## 许可证

MIT