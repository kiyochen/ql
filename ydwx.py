#!/usr/bin/python3
# -- coding: utf-8 -- 
# -------------------------------
# @Author : github@wd210010 https://github.com/wd210010/just_for_happy
# @Time : 2023/2/27 13:23
# -------------------------------
# cron "6,10,15 * * *" script-path=xxx.py,tag=匹配cron用
# const $ = new Env('一点万象签到')

import requests, time, hashlib, json, os
import random  

# 一点万向签到领万向星 可抵扣停车费
# 登录后搜索https://app.mixcapp.com/mixc/gateway域名随意一个 请求体里面的deviceParams，token 多账号填多个单引号里面 用英文逗号隔开

ydwx_deviceParams = os.getenv("ydwx_deviceParams").split('&') if os.getenv("ydwx_deviceParams") else []
ydwx_token = os.getenv("ydwx_token").split('&') if os.getenv("ydwx_token") else []

plustoken = os.getenv("plustoken")

def Push(contents):
    headers = {'Content-Type': 'application/json'}
    push_data = {"token": plustoken, 'title': '一点万向签到', 'content': contents.replace('\n', '<br>'), "template": "json"}
    try:
        # 【修改】增加 15 秒超时时间，防止推送服务卡死脚本
        resp = requests.post(f'http://www.pushplus.plus/send', json=push_data, headers=headers, timeout=15).json()
        print('push+推送成功' if resp.get('code') == 200 else 'push+推送失败', flush=True)
    except Exception as e:
        print(f'push+推送异常: {e}', flush=True)


if __name__ == '__main__':
    
    initial_delay = random.randint(0, 100)
    # 【修改】增加 flush=True 强制立刻输出到面板日志，防止缓存不显示
    print(f"🚀 防检测机制触发：脚本将随机等待 {initial_delay} 秒后开始执行...", flush=True)
    time.sleep(initial_delay)
    
    print(f'共配置了{len(ydwx_deviceParams)}个账号', flush=True)
    log = []
    
    for i in range(len(ydwx_deviceParams)):
        print(f'\n***** 第 {str(i+1)} 个账号 *****', flush=True)
        timestamp = str(int(round(time.time() * 1000)))
        md5 = hashlib.md5()
        sig = f'action=mixc.app.memberSign.sign&apiVersion=1.0&appId=68a91a5bac6a4f3e91bf4b42856785c6&appVersion=3.53.0&deviceParams={ydwx_deviceParams[i]}&imei=2333&mallNo=20014&osVersion=12.0.1&params=eyJtYWxsTm8iOiIyMDAxNCJ9&platform=h5&timestamp={timestamp}&token={ydwx_token[i]}&P@Gkbu0shTNHjhM!7F'
        
        md5.update(sig.encode('utf-8'))  
        sign = md5.hexdigest()        
        url = 'https://app.mixcapp.com/mixc/gateway'
        headers = {
            'Host': 'app.mixcapp.com',
            'Connection': 'keep-alive',
            'Content-Length': '564',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://app.mixcapp.com',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; PCAM00 Build/QKQ1.190918.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.92 Mobile Safari/537.36/MIXCAPP/3.42.2/AnalysysAgent/Hybrid',
            'Sec-Fetch-Mode': 'cors',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'com.crland.mixc',
            'Sec-Fetch-Site': 'same-origin',
            'Referer': 'https://app.mixcapp.com/m/m-20014/signIn?showWebNavigation=true&timestamp=1676906528979&appVersion=3.53.0&mallNo=20014',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        data = f'mallNo=20014&appId=68a91a5bac6a4f3e91bf4b42856785c6&platform=h5&imei=2333&appVersion=3.53.0&osVersion=12.0.1&action=mixc.app.memberSign.sign&apiVersion=1.0&timestamp={timestamp}&deviceParams={ydwx_deviceParams[i]}&token={ydwx_token[i]}&params=eyJtYWxsTm8iOiIyMDAxNCJ9&sign={sign}'
        
        try:
            # 【修改】增加 15 秒超时，防止一点万象服务器不响应导致死等
            html = requests.post(url=url, headers=headers, data=data, timeout=15)
            response_msg = json.loads(html.text).get('message', '未知返回状态')
        except requests.exceptions.Timeout:
            response_msg = "请求超时(15秒)，可能是网络不佳或服务器拦截"
        except Exception as e:
            response_msg = f"网络请求或解析异常: {e}"
            
        result = f'帐号{i+1}签到结果: {response_msg}'
        print(result, flush=True)
        log.append(result)

        if i < len(ydwx_deviceParams) - 1:
            account_delay = random.randint(0, 60)
            print(f"⏳ 防检测机制触发：随机等待 {account_delay} 秒后处理下一个账号...", flush=True)
            time.sleep(account_delay)

    log2 = str(log).replace('[\'','').replace('\']','').replace(':','\n').replace('\', \'','\n')
    
    if plustoken:
        Push(contents=log2)
    else:
        print("\n通知：未配置 PushPlus Token，已跳过推送。", flush=True)
