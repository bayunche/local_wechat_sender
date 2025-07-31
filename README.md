# 跨平台微信自动发送服务

这是一个支持 Windows 和 macOS 的微信自动发送服务，可以通过 HTTP API 发送文本消息、音频文件、HTML文件和视频文件到指定的微信群聊或私聊。

## 支持的平台

| 平台 | 实现方式 | 状态 |
|------|----------|------|
| Windows | wxauto + COM | ✅ 已测试 |
| macOS | AppleScript | ✅ 新增支持 |
| Linux | 暂不支持 | ❌ |

## 安装依赖

```bash
pip install -r requirements.txt
```

## 视频转换功能额外要求

如果需要使用视频发送功能，需要安装 FFmpeg 系统工具：

**Windows用户：**
1. 从 [FFmpeg官网](https://ffmpeg.org/download.html) 下载 Windows 版本
2. 解压到任意目录（如 `C:\ffmpeg`）
3. 将 `bin` 目录添加到系统环境变量 PATH 中
4. 重启命令行验证：`ffmpeg -version`

**macOS用户：**
```bash
brew install ffmpeg
```

**Linux用户：**
```bash
sudo apt-get install ffmpeg
```

## macOS 用户额外设置

1. **开启辅助功能权限**：
   - 系统偏好设置 → 安全性与隐私 → 辅助功能
   - 添加终端/Python/你的IDE到允许列表

2. **确保微信已安装**：
   - 微信需要安装在 `/Applications/WeChat.app`
   - 启动服务前需要手动打开微信并登录

## 启动服务

```bash
python app.py
```

服务启动后会显示：
- 当前平台信息
- 支持的功能
- API接口列表

## API 接口

### 1. 发送音频文件 (跨平台)

**POST** `/send`

```json
{
  "group_name": "群聊名称或好友昵称",
  "audio_url": "http://example.com/audio.mp3",
  "message": "可选的文本消息"
}
```

### 2. 发送HTML文件 (跨平台)

**POST** `/send_html`

```json
{
  "group_name": "群聊名称或好友昵称",
  "html_content": "<html><body>HTML内容</body></html>",
  "html_url": "http://example.com/page.html",
  "message": "可选的文本消息",
  "filename": "document.html"
}
```

**注意：** `html_content` 和 `html_url` 二选一即可。

### 3. 发送视频文件 (跨平台，支持格式转换)

**POST** `/send_video`

```json
{
  "group_name": "群聊名称或好友昵称",
  "video_url": "http://example.com/video.avi",
  "message": "可选的文本消息",
  "filename": "video",
  "force_convert": false
}
```

**特性：**
- 自动检测视频格式，非MP4格式会自动转换
- 支持常见格式：AVI, MOV, WMV, FLV, MKV 等
- `force_convert=true` 可强制转换为MP4
- 返回转换信息和视频详情

### 4. 查看平台信息

**GET** `/platform`

返回当前运行平台和支持信息。

### 5. 录制音频播放 (可选)

**POST** `/record`

需要安装 playwright 依赖。

## 使用示例

```bash
# 查看平台信息
curl http://localhost:8899/platform

# 发送音频文件
curl -X POST http://localhost:8899/send \
  -H "Content-Type: application/json" \
  -d '{
    "group_name": "测试群",
    "audio_url": "https://example.com/test.mp3",
    "message": "🎤 以下是今日的音频播客，请查收"
  }'

# 发送HTML文件
curl -X POST http://localhost:8899/send_html \
  -H "Content-Type: application/json" \
  -d '{
    "group_name": "测试群",
    "html_url": "https://example.com/report.html",
    "message": "📄 以下是今日的报告文件",
    "filename": "daily_report"
  }'

# 发送视频文件（自动转换格式）
curl -X POST http://localhost:8899/send_video \
  -H "Content-Type: application/json" \
  -d '{
    "group_name": "测试群",
    "video_url": "https://example.com/video.avi",
    "message": "🎬 以下是今日的视频内容",
    "filename": "daily_video"
  }'
```

## 注意事项

### Windows 用户
- 需要安装并启动微信桌面版
- 首次使用可能需要手动点击微信窗口激活

### macOS 用户
- **重要**：需要开启辅助功能权限
- AppleScript 可能需要几秒钟执行
- 如果发送失败，检查微信是否在前台或尝试手动切换到微信窗口

### 通用建议
- 群聊名称需要精确匹配
- 所有文件会下载到 `downloads` 目录
- 视频转换可能需要较长时间，请耐心等待
- 建议先用小群测试功能
- 大视频文件建议使用 `force_convert=false` 避免不必要的转换

## 故障排除

1. **权限问题**：确保系统辅助功能权限已开启
2. **微信未启动**：服务会自动尝试启动微信
3. **群聊找不到**：检查群聊名称是否完全匹配
4. **文件发送失败**：检查文件是否成功下载到本地
5. **视频转换失败**：确保 FFmpeg 已正确安装并添加到 PATH
6. **HTML文件乱码**：检查HTML内容的编码格式
7. **视频格式不支持**：尝试设置 `force_convert=true` 强制转换

## 开发说明

项目采用平台检测 + 条件导入的方式实现跨平台支持：
- Windows: 使用 `wxauto` 库进行 UI 自动化
- macOS: 使用 `AppleScript` 通过系统脚本控制微信

代码结构清晰，易于扩展其他平台支持。