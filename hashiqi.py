#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
青龙面板脚本: 二哈哈士奇自动签到 (V13.0 状态导向版)
Cron: 0 8 * * *
new Env('二哈哈士奇签到');

说明：
1. 采用“状态导向”判定逻辑：只要最终页面显示“已签到”且无弹窗报错，即判定为成功。
2. 解决了首次签到成功后因按钮变色被误判为重复的问题。
3. 包含自动登录、积分显示。
"""

import requests
import re
import time
import os
import sys
import random

# ================= 配置区域 =================

URL_TARGET = "https://vip.ioshashiqi.com/aspx3/mobile/qiandao.aspx"

# ===========================================

try:
    from notify import send
except ImportError:
    def send(title, content):
        print("未找到 notify 模块，仅打印日志:")
        print(f"{title}\n{content}")

def get_env(key):
    return os.getenv(key)

def run_qiandao():
    # 1. 基础配置读取
    username = get_env("SHASHIQI_USER")
    password = get_env("SHASHIQI_PWD")
    env_cookie = get_env("SHASHIQI_COOKIE") or ""
    
    if not username or not password:
        print("❌ 错误：缺少账号密码！")
        print("请在环境变量添加 SHASHIQI_USER (手机号) 和 SHASHIQI_PWD (密码)")
        return

    # 2. 随机延时 (1-300秒)
    sleep_time = random.randint(1, 300)
    print(f"⏱️ 随机延时 {sleep_time} 秒...")
    time.sleep(sleep_time)

    # 初始化 Session
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.66",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": URL_TARGET,
        "Origin": "https://vip.ioshashiqi.com"
    })
    
    if env_cookie:
        session.headers.update({"Cookie": env_cookie})

    print("\n--- [Step 1] 检查登录状态 ---")
    
    vs_data = None
    is_login_needed = False

    try:
        resp = session.get(URL_TARGET)
        resp.encoding = 'utf-8'
        vs_data = extract_viewstate(resp.text)
        
        # 检查是否包含密码输入框
        if "txtPwd_sign_in" in resp.text:
            print("⚠️ 检测到当前未登录 (Cookie已失效)")
            is_login_needed = True
        else:
            print("✅ 当前 Cookie 有效，直接进入签到流程")

    except Exception as e:
        print(f"❌ 网络请求异常: {e}")
        return

    # --- 自动登录流程 ---
    if is_login_needed:
        print(f"\n--- [Step 1.5] 执行自动登录 ({username}) ---")
        time.sleep(2)
        
        if not vs_data: 
             vs_data = {"vs": "", "gen": ""}

        login_data = {
            "__EVENTTARGET": "btnLogin",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": vs_data['vs'],
            "__VIEWSTATEGENERATOR": vs_data['gen'],
            "txtUser_sign_in": username,
            "txtPwd_sign_in": password
        }
        
        try:
            resp_login = session.post(URL_TARGET, data=login_data)
            resp_login.encoding = 'utf-8'
            
            if "txtPwd_sign_in" not in resp_login.text:
                print("🎉 自动登录成功！")
                vs_data = extract_viewstate(resp_login.text)
            else:
                print("❌ 登录失败：页面依然显示密码框，请检查账号密码。")
                send("二哈签到失败", "自动登录失败")
                return
        except Exception as e:
            print(f"❌ 登录请求异常: {e}")
            return

    # --- 签到流程 ---
    print("\n--- [Step 2] 提交签到 ---")
    time.sleep(2)
    
    if not vs_data:
        resp = session.get(URL_TARGET)
        vs_data = extract_viewstate(resp.text)

    checkin_data = {
        "__EVENTTARGET": "_lbtqd",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": vs_data['vs'],
        "__VIEWSTATEGENERATOR": vs_data['gen']
    }
    
    try:
        resp_post = session.post(URL_TARGET, data=checkin_data)
        resp_post.encoding = 'utf-8'
        txt = resp_post.text
        
        log_content = ""
        
        # 提取积分信息 (作为辅助验证)
        pts = re.search(r'(\d+)\s*积分', txt)
        pts_str = pts.group(1) if pts else "未知"
        
        # === V13.0 核心判定逻辑 ===
        
        # 1. 优先检查【弹窗警告】 (只有弹窗明确说重复，才是真正的重复)
        # 优化了正则，支持 alert("xxx") 这种带空格的写法
        alert_pattern = re.search(r"alert\s*\(\s*['\"](.*?)['\"]\s*\)", txt)
        alert_text = alert_pattern.group(1) if alert_pattern else ""
        
        if alert_text:
            print(f"💬 服务器弹窗: 【{alert_text}】")
            if any(k in alert_text for k in ["重复", "今天"]):
                log_content = f"⚠️ {alert_text} (无需重复)"
            elif any(k in alert_text for k in ["成功", "积分", "获得"]):
                log_content = f"🎉 {alert_text} (积分: {pts_str})"
            else:
                log_content = f"🔔 提示: {alert_text}"
        
        else:
            # 2. 如果【没有弹窗】，但页面显示“已签到”
            # 这通常意味着：刚才的操作成功了，或者页面状态刷新了。
            # 在没有弹窗报错的情况下，这被视为【成功/状态正常】。
            if "已签到" in txt or "重复" in txt:
                 log_content = f"✅ 签到状态确认: [已签到] (当前积分: {pts_str})"
            
            # 3. 如果没找到“已签到”，但有“成功”字样
            elif "签到成功" in txt or "获得积分" in txt:
                 log_content = f"🎉 签到成功！(当前积分: {pts_str})"
                 
            # 4. 异常：被踢回登录页
            elif "txtPwd_sign_in" in txt:
                 log_content = "❌ 异常：请求后会话丢失，跳转回登录页"
            
            # 5. 未知
            else:
                 log_content = f"❓ 操作完成，未匹配明确提示 (当前积分: {pts_str})"

        print(f"执行结果: {log_content}")
        
        # ⚠️ 只有明确的“重复弹窗”才不推送，其他情况（包括状态确认）都算正常推送
        if "⚠️" not in log_content:
            send("二哈签到结果", log_content)

    except Exception as e:
        print(f"❌ 签到请求异常: {e}")
        send("二哈签到出错", str(e))

def extract_viewstate(html):
    try:
        vs = re.search(r'name="__VIEWSTATE" id="__VIEWSTATE" value="(.*?)"', html)
        gen = re.search(r'name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="(.*?)"', html)
        if vs:
            return {
                "vs": vs.group(1), 
                "gen": gen.group(1) if gen else ""
            }
    except:
        pass
    return None

if __name__ == "__main__":
    run_qiandao()
