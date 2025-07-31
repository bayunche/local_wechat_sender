from datetime import datetime
import time
import subprocess
import tempfile
import asyncio
import platform

from flask import Flask, request, jsonify
import requests
import os
import traceback
import re

# Windows特定导入
if platform.system() == "Windows":
    from wxauto import WeChat
    import pythoncom

app = Flask(__name__)

def sanitize_filename(name):
    # 替换掉 Windows 不允许的字符：\ / : * ? " < > |
    return re.sub(r'[\\/:*?"<>|]', "_", name)

def ensure_wechat_running_macos():
    """确保macOS微信程序正在运行"""
    try:
        # 检查微信进程是否存在
        result = subprocess.run(['pgrep', '-f', 'WeChat'], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("微信未运行，正在启动微信...")
            # 启动微信
            subprocess.run(['open', '-a', 'WeChat'])
            print("等待微信启动...")
            time.sleep(3)
            return True
        else:
            print("微信已在运行")
            return True
    except Exception as e:
        print(f"检查微信状态时出错: {e}")
        return False

def send_wechat_message_macos(group_name, message=None, file_path=None):
    """使用AppleScript在macOS上发送微信消息"""
    try:
        # 构建AppleScript
        script_parts = []
        
        # 激活微信并搜索聊天对象
        script_parts.append(f'''
        tell application "WeChat"
            activate
            delay 1
        end tell
        
        tell application "System Events"
            tell process "WeChat"
                -- 点击搜索框
                click text field 1 of group 1 of group 1 of window 1
                delay 0.5
                
                -- 输入群名称
                set the clipboard to "{group_name}"
                key code 9 using command down -- cmd+v
                delay 1
                
                -- 按回车选择第一个搜索结果
                key code 36 -- 回车键
                delay 1
            end tell
        end tell
        ''')
        
        # 发送文本消息
        if message:
            escaped_message = message.replace('"', '\\"').replace('\\', '\\\\')
            script_parts.append(f'''
            tell application "System Events"
                tell process "WeChat"
                    -- 在聊天输入框输入消息
                    set the clipboard to "{escaped_message}"
                    key code 9 using command down -- cmd+v
                    delay 0.5
                    
                    -- 发送消息
                    key code 36 -- 回车键
                    delay 1
                end tell
            end tell
            ''')
        
        # 发送文件
        if file_path and os.path.exists(file_path):
            abs_file_path = os.path.abspath(file_path).replace('\\', '/')
            script_parts.append(f'''
            tell application "System Events"
                tell process "WeChat"
                    -- 拖拽文件到聊天窗口
                    set theFile to POSIX file "{abs_file_path}"
                    
                    -- 使用快捷键打开文件选择器
                    key code 31 using command down -- cmd+o
                    delay 1
                    
                    -- 输入文件路径
                    keystroke "g" using {{command down, shift down}}
                    delay 0.5
                    type text "{abs_file_path}"
                    delay 0.5
                    key code 36 -- 回车
                    delay 1
                    key code 36 -- 回车确认选择
                    delay 2
                end tell
            end tell
            ''')
        
        # 执行AppleScript
        full_script = '\n'.join(script_parts)
        result = subprocess.run(['osascript', '-e', full_script], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ macOS微信消息发送成功")
            return True
        else:
            print(f"❌ AppleScript执行失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ AppleScript执行超时")
        return False
    except Exception as e:
        print(f"❌ macOS微信发送失败: {e}")
        traceback.print_exc()
        return False

def ensure_wechat_running():
    """确保微信程序正在运行"""
    try:
        # 检查微信进程是否存在
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq WeChat.exe'], 
                              capture_output=True, text=True, shell=True)
        
        if "WeChat.exe" not in result.stdout:
            print("微信未运行，正在启动微信...")
            # 尝试从常见路径启动微信
            wechat_paths = [
                r"C:\Program Files\Tencent\WeChat\WeChat.exe",
                r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
                r"D:\Program Files\Tencent\WeChat\WeChat.exe",
                r"D:\Program Files (x86)\Tencent\WeChat\WeChat.exe"
            ]
            
            wechat_started = False
            for path in wechat_paths:
                if os.path.exists(path):
                    print(f"从 {path} 启动微信")
                    subprocess.Popen([path])
                    wechat_started = True
                    break
            
            if not wechat_started:
                print("未找到微信安装路径，请手动启动微信")
                return False
            
            # 等待微信启动
            print("等待微信启动...")
            time.sleep(5)
            return True
        else:
            print("微信已在运行")
            return True
    except Exception as e:
        print(f"检查微信状态时出错: {e}")
        return False

async def record_audio_playback(html_content, audio_url, output_path):
    """使用playwright录制音频播放"""
    try:
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(headless=False)  # 设置为False以便调试
            context = await browser.new_context(
                record_video_dir="recordings",
                record_video_size={"width": 1280, "height": 720}
            )
            page = await context.new_page()
            
            print("浏览器启动完成")
            
            # 创建临时HTML文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                # 在HTML中嵌入音频URL
                modified_html = html_content.replace('{{AUDIO_URL}}', audio_url)
                f.write(modified_html)
                temp_html_path = f.name
            
            print(f"临时HTML文件创建: {temp_html_path}")
            
            # 加载HTML页面
            await page.goto(f"file://{temp_html_path}")
            print("页面加载完成")
            
            # 等待页面完全加载
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # 查找并点击播放按钮
            play_selectors = [
                'button[aria-label*="play"]',
                'button[title*="play"]',
                '.play-button',
                '#playButton',
                'button:has-text("播放")',
                'button:has-text("Play")',
                '[role="button"][aria-label*="play"]',
                'audio',
                'video'
            ]
            
            played = False
            for selector in play_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        print(f"找到播放元素: {selector}")
                        if selector in ['audio', 'video']:
                            # 对于audio/video元素，直接调用play方法
                            await page.evaluate('(element) => element.play()', element)
                        else:
                            # 对于按钮元素，点击
                            await element.click()
                        played = True
                        break
                except Exception as e:
                    print(f"尝试选择器 {selector} 失败: {e}")
                    continue
            
            if not played:
                print("未找到播放按钮，尝试自动播放音频")
                # 尝试通过JavaScript自动播放
                await page.evaluate('''
                    () => {
                        const audio = document.querySelector('audio');
                        if (audio) {
                            audio.play();
                            return true;
                        }
                        const video = document.querySelector('video');
                        if (video) {
                            video.play();
                            return true;
                        }
                        return false;
                    }
                ''')
            
            print("开始录制...")
            
            # 等待音频播放完成（这里设置一个合理的时间，或者监听音频结束事件）
            # 可以根据音频长度调整等待时间
            await asyncio.sleep(30)  # 默认录制30秒，可以根据需要调整
            
            print("录制完成")
            
            # 关闭浏览器
            await browser.close()
            
            # 删除临时文件
            os.unlink(temp_html_path)
            
            # 移动录制的视频到指定位置
            video_files = os.listdir("recordings")
            if video_files:
                video_path = os.path.join("recordings", video_files[0])
                os.rename(video_path, output_path)
                print(f"录制文件已保存到: {output_path}")
                return True
            else:
                print("未找到录制文件")
                return False
                
    except Exception as e:
        print(f"录制过程出错: {e}")
        traceback.print_exc()
        return False

@app.route('/record', methods=['POST'])
def record_screen():
    """录屏接口"""
    try:
        # 获取form data
        html_content = request.form.get('html_content')
        audio_url = request.form.get('audio_url')
        
        if not html_content:
            return jsonify({"status": "error", "msg": "缺少参数：html_content"}), 400
        if not audio_url:
            return jsonify({"status": "error", "msg": "缺少参数：audio_url"}), 400
        
        print(f"开始录制，音频URL: {audio_url}")
        
        # 创建录制目录
        os.makedirs("recordings", exist_ok=True)
        
        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"recording_{timestamp}.webm"
        output_path = os.path.join("recordings", output_filename)
        
        # 运行异步录制函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(record_audio_playback(html_content, audio_url, output_path))
        loop.close()
        
        if success:
            return jsonify({
                "status": "success", 
                "msg": "录制完成",
                "file_path": output_path
            })
        else:
            return jsonify({"status": "error", "msg": "录制失败"}), 500
            
    except Exception as e:
        print(f"录制接口出错: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "msg": f"录制失败: {e}"}), 500

def send_audio_windows(group_name, message, local_path):
    """Windows版微信发送逻辑"""
    if platform.system() != "Windows":
        raise Exception("此函数只能在Windows系统上运行")
    
    pythoncom.CoInitialize()
    
    # 确保微信正在运行
    if not ensure_wechat_running():
        raise Exception("无法启动微信，请手动打开微信后重试")
    
    # 使用微信发送
    print(f"正在打开微信并查找群: {group_name}")
    wx = WeChat()
    print("微信初始化完成")

    # 验证文件是否存在
    if not os.path.exists(local_path):
        raise Exception(f"音频文件不存在: {local_path}")
    print(f"音频文件验证通过: {local_path}")

    # 切换到指定聊天窗口
    print(f"正在切换到聊天窗口: {group_name}")
    wx.ChatWith(group_name)
    time.sleep(1.5)
    print("聊天窗口切换完成")
    
    # 发送文本消息（如果有）
    if message:
        print(f"开始发送消息: {message}")
        try:
            wx.SendMsg(message)
            print("文本消息发送完成")
            time.sleep(1)
        except Exception as msg_error:
            print(f"文本消息发送失败: {msg_error}")
            raise msg_error
    
    # 发送音频文件
    print(f"开始发送音频文件: {local_path}")
    file_sent = False
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"尝试发送音频文件 (第{attempt + 1}次)...")
            wx.SendFiles(local_path)
            time.sleep(2)
            print(f"音频文件发送操作完成 (第{attempt + 1}次)")
            file_sent = True
            break
        except Exception as file_error:
            print(f"音频文件发送失败 (第{attempt + 1}次): {file_error}")
            if attempt < max_retries - 1:
                print(f"等待3秒后重试...")
                time.sleep(3)
            else:
                raise file_error
    
    if file_sent:
        print("✅ 音频发送成功")
        # 切换窗口到Edge浏览器
        try:
            subprocess.run(['powershell', '-Command', '(New-Object -ComObject WScript.Shell).AppActivate("Microsoft Edge")'],
                          capture_output=True, text=True, shell=True)
            print("已切换到Edge浏览器窗口")
        except Exception as e:
            print(f"切换到Edge浏览器窗口失败: {e}")
        return True
    else:
        raise Exception("音频发送失败，已达到最大重试次数")

@app.route('/send', methods=['POST'])
def send_audio():
    data = request.get_json()
    group_name = data.get("group_name")
    audio_url = data.get("audio_url")
    message = data.get("message", "")

    if not group_name or not audio_url:
        return jsonify({"status": "error", "msg": "缺少参数：group_name 或 audio_url"}), 400

    # 创建临时保存目录
    os.makedirs("downloads", exist_ok=True)
    
    # 根据平台生成文件名格式
    if platform.system() == "Windows":
        file_name = datetime.now().strftime("%#m月%#d日") + message + ".mp3"
    else:  # macOS/Linux
        file_name = datetime.now().strftime("%-m月%-d日") + message + ".mp3"
    
    file_name_sanitized = sanitize_filename(file_name)
    local_path = os.path.join("downloads", file_name_sanitized)

    try:
        # 下载文件
        print(f"正在下载音频: {audio_url}")
        r = requests.get(audio_url, timeout=10)
        with open(local_path, "wb") as f:
            f.write(r.content)
        print(f"音频已保存至: {local_path}")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "msg": f"下载音频失败: {e}"}), 500

    try:
        # 根据平台选择发送方式
        current_platform = platform.system()
        print(f"当前平台: {current_platform}")
        
        if current_platform == "Windows":
            send_audio_windows(group_name, message, local_path)
        elif current_platform == "Darwin":  # macOS
            # 确保微信正在运行
            if not ensure_wechat_running_macos():
                return jsonify({"status": "error", "msg": "无法启动微信，请手动打开微信后重试"}), 500
            
            # 使用macOS版本发送
            if not send_wechat_message_macos(group_name, message, local_path):
                raise Exception("macOS微信发送失败")
        else:
            return jsonify({"status": "error", "msg": f"不支持的平台: {current_platform}"}), 400
            
        return jsonify({"status": "success", "msg": "发送成功"})
            
    except Exception as e:
        print(f"❌ 发送过程出错: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "msg": f"发送微信失败: {e}"}), 500

@app.route('/platform', methods=['GET'])
def get_platform_info():
    """获取平台信息"""
    current_platform = platform.system()
    platform_info = {
        "platform": current_platform,
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "supported": current_platform in ["Windows", "Darwin"],
        "wechat_method": "wxauto" if current_platform == "Windows" else "AppleScript" if current_platform == "Darwin" else "不支持"
    }
    return jsonify(platform_info)

if __name__ == '__main__':
    print(f"🚀 启动跨平台微信发送服务")
    print(f"📱 当前平台: {platform.system()}")
    print(f"🔧 支持的平台: Windows (wxauto), macOS (AppleScript)")
    print(f"🌐 服务地址: http://0.0.0.0:8899")
    print(f"📊 接口列表:")
    print(f"   - POST /send - 发送微信消息（跨平台）")
    print(f"   - POST /record - 录制音频播放（需要playwright）")
    print(f"   - GET /platform - 查看平台信息")
    app.run(host='0.0.0.0', port=8899)
