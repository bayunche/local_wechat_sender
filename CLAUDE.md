# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个跨平台的微信自动发送服务，通过HTTP API提供微信消息和文件发送功能。支持Windows和macOS两个平台，使用不同的技术栈实现微信自动化。

## 核心架构

### 跨平台设计模式
项目采用**平台检测 + 条件导入**的架构模式：

```python
# 根据平台动态导入依赖
if platform.system() == "Windows":
    from wxauto import WeChat
    import pythoncom
```

### 双实现策略
- **Windows**: 使用 `wxauto` 库进行UI自动化，通过COM接口控制微信客户端
- **macOS**: 使用 `AppleScript` 通过系统脚本和辅助功能API控制微信

### 主要组件
1. **平台检测层** (`platform.system()`)
2. **Windows实现** (`send_audio_windows()`, `ensure_wechat_running()`)  
3. **macOS实现** (`send_wechat_message_macos()`, `ensure_wechat_running_macos()`)
4. **统一API层** (`/send`, `/platform`, `/record`)

## 开发命令

### 启动服务
```bash
python app.py
```
服务运行在 `http://0.0.0.0:8899`

### 安装依赖
```bash
pip install -r requirements.txt
```

### 测试API
```bash
# 查看平台信息
curl http://localhost:8899/platform

# 发送消息测试
curl -X POST http://localhost:8899/send \
  -H "Content-Type: application/json" \
  -d '{"group_name": "测试群", "audio_url": "https://example.com/test.mp3", "message": "测试消息"}'
```

## 关键实现细节

### 文件下载和存储
- 音频文件下载到 `downloads/` 目录
- 文件名格式：`{月份}{日期}{消息内容}.mp3`
- 使用 `sanitize_filename()` 处理特殊字符

### Windows微信控制 (`app.py:334-404`)
- 使用 `pythoncom.CoInitialize()` 初始化COM
- 通过 `wxauto.WeChat()` 创建微信控制实例
- 支持重试机制（最多3次）

### macOS微信控制 (`app.py:45-138`)
- 使用 `osascript` 执行AppleScript
- 通过剪贴板传递文本内容
- 使用键盘快捷键和UI自动化

### 错误处理策略
- 平台不兼容返回400错误
- 微信启动失败返回500错误
- 文件下载失败返回500错误
- 详细的错误日志和堆栈跟踪

## 平台特定注意事项

### macOS开发要求
- 需要在系统偏好设置中开启辅助功能权限
- 微信必须安装在 `/Applications/WeChat.app`
- AppleScript执行可能需要几秒钟延迟

### Windows开发要求  
- 需要安装微信桌面版
- 依赖 `wxauto` 和 `pywin32` 库
- COM组件需要正确初始化

## API接口规范

### POST /send
发送微信消息（跨平台）
- `group_name`: 群聊名称或好友昵称（必需）
- `audio_url`: 音频文件URL（必需）
- `message`: 可选的文本消息

### GET /platform
返回当前平台信息和支持状态

### POST /record
录制音频播放（需要playwright）
- `html_content`: HTML内容
- `audio_url`: 音频URL

## 日志和调试

- 微信操作日志存储在 `wxauto_logs/` 目录
- 使用 `print()` 进行关键步骤日志输出
- 异常处理使用 `traceback.print_exc()` 输出详细错误信息