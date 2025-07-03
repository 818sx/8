#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
青龙面板 WEBHOST 自动登录脚本
使用 requests + session 方式，避免 Playwright 依赖问题
"""

import os
import sys
import time
import logging
import requests
from datetime import datetime
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 固定配置
LOGIN_EMAIL = "xtfneeq@hotmail.com"
LOGIN_PASSWORD = "zhang1202"
TELEGRAM_BOT_TOKEN = "6003308968:AAGqZQvAgLIukZsGKEeEG8L93I7-0wCa_8s"
TELEGRAM_CHAT_ID = "6185121064"

def send_telegram_message(message):
    """发送Telegram消息"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        logger.info("✅ Telegram消息发送成功")
        return response.json()
    except Exception as e:
        logger.error(f"❌ Telegram消息发送失败: {str(e)}")
        return None

def login_webhost():
    """使用requests方式登录WEBHOST"""
    try:
        logger.info(f"🔄 开始登录 WEBHOST 账号: {LOGIN_EMAIL}")
        
        # 创建session保持会话
        session = requests.Session()
        
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        session.headers.update(headers)
        
        # 第一步：访问登录页面获取token等必要信息
        logger.info("📄 正在访问登录页面...")
        login_url = "https://client.webhostmost.com/login"
        response = session.get(login_url, timeout=30)
        response.raise_for_status()
        
        # 检查是否成功获取登录页面
        if "login" not in response.text.lower():
            logger.error("❌ 无法访问登录页面")
            return False, "无法访问登录页面"
        
        # 尝试提取CSRF token或其他必要信息
        csrf_token = None
        # 查找可能的CSRF token
        csrf_patterns = [
            r'name="token"\s+value="([^"]+)"',
            r'name="_token"\s+value="([^"]+)"',
            r'name="csrf_token"\s+value="([^"]+)"',
            r'<meta\s+name="csrf-token"\s+content="([^"]+)"'
        ]
        
        for pattern in csrf_patterns:
            match = re.search(pattern, response.text, re.IGNORECASE)
            if match:
                csrf_token = match.group(1)
                logger.info(f"🔑 找到CSRF token: {csrf_token[:20]}...")
                break
        
        # 第二步：准备登录数据
        logger.info("📝 准备登录数据...")
        
        # 基本登录数据
        login_data = {
            'email': LOGIN_EMAIL,
            'password': LOGIN_PASSWORD,
        }
        
        # 如果找到CSRF token，添加到登录数据中
        if csrf_token:
            login_data['token'] = csrf_token
            login_data['_token'] = csrf_token
            login_data['csrf_token'] = csrf_token
        
        # 可能需要的其他字段
        login_data.update({
            'rememberme': 'on',
            'login': 'Login',
            'submit': 'Login'
        })
        
        # 第三步：执行登录
        logger.info("🔐 提交登录请求...")
        
        # 更新请求头
        login_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://client.webhostmost.com',
            'Referer': login_url,
        }
        session.headers.update(login_headers)
        
        # 发送登录请求
        login_response = session.post(login_url, data=login_data, timeout=30, allow_redirects=True)
        
        # 第四步：检查登录结果
        logger.info("🔍 检查登录结果...")
        
        # 检查响应状态
        if login_response.status_code != 200:
            logger.error(f"❌ 登录请求失败，状态码: {login_response.status_code}")
            return False, f"登录请求失败，状态码: {login_response.status_code}"
        
        # 检查是否有错误消息
        response_text = login_response.text.lower()
        error_indicators = [
            'invalid email',
            'invalid password',
            'login failed',
            'incorrect password',
            'account not found',
            'authentication failed'
        ]
        
        for error in error_indicators:
            if error in response_text:
                logger.error(f"❌ 登录失败: 发现错误信息 - {error}")
                return False, f"登录失败: {error}"
        
        # 检查是否成功登录（通过URL或页面内容判断）
        current_url = login_response.url
        success_indicators = [
            'clientarea.php',
            'dashboard',
            'client area',
            'welcome',
            'account',
            'billing'
        ]
        
        # 检查URL
        for indicator in success_indicators:
            if indicator in current_url.lower():
                logger.info(f"✅ 登录成功！当前URL: {current_url}")
                return True, "登录成功"
        
        # 检查页面内容
        for indicator in success_indicators:
            if indicator in response_text:
                logger.info(f"✅ 登录成功！页面包含: {indicator}")
                return True, "登录成功"
        
        # 如果没有明确的成功标识，但也没有错误，尝试访问客户区域确认
        try:
            logger.info("🔍 尝试访问客户区域确认登录状态...")
            clientarea_response = session.get("https://client.webhostmost.com/clientarea.php", timeout=30)
            
            if clientarea_response.status_code == 200 and "login" not in clientarea_response.text.lower():
                logger.info("✅ 登录成功！能够访问客户区域")
                return True, "登录成功"
            else:
                logger.error("❌ 登录失败：无法访问客户区域")
                return False, "登录失败：无法访问客户区域"
                
        except Exception as e:
            logger.error(f"❌ 验证登录状态时出错: {str(e)}")
            return False, f"验证登录状态时出错: {str(e)}"
        
    except requests.exceptions.Timeout:
        logger.error("❌ 请求超时")
        return False, "请求超时"
    except requests.exceptions.ConnectionError:
        logger.error("❌ 网络连接错误")
        return False, "网络连接错误"
    except Exception as e:
        logger.error(f"❌ 登录过程中发生错误: {str(e)}")
        return False, f"登录过程中发生错误: {str(e)}"

def main():
    """主函数"""
    logger.info("🚀 WEBHOST 自动登录脚本启动")
    logger.info(f"📅 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 执行登录
    success, message = login_webhost()
    
    # 准备Telegram消息
    if success:
        telegram_message = f"""
🎉 **WEBHOST 登录成功**

📧 **账号**: `{LOGIN_EMAIL}`
⏰ **时间**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
✅ **状态**: 登录成功
🔧 **方式**: HTTP请求方式

---
_青龙面板自动执行_
        """.strip()
        logger.info("🎉 脚本执行完成，登录成功")
    else:
        telegram_message = f"""
❌ **WEBHOST 登录失败**

📧 **账号**: `{LOGIN_EMAIL}`
⏰ **时间**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
❌ **错误**: `{message}`
🔧 **方式**: HTTP请求方式

---
_青龙面板自动执行_
        """.strip()
        logger.error(f"💥 脚本执行完成，登录失败: {message}")
    
    # 发送Telegram通知
    send_telegram_message(telegram_message)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
