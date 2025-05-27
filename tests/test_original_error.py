#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试原始错误的脚本 - 模拟API调用
"""

import sys
import os
import requests
import json
import time

def test_original_error():
    """测试原始的API错误"""
    print("测试原始API错误...")
    
    # API端点
    url = "http://localhost:8000/data/query-test"
    
    # 测试数据
    test_data = {
        "query": "test query",
        "meta": {
            "maxQueryCount": 20,
            "topK": 10
        }
    }
    
    try:
        print("发送API请求...")
        response = requests.post(url, json=test_data, timeout=30)
        
        if response.status_code == 200:
            print("✅ API调用成功")
            result = response.json()
            print(f"返回结果: {result}")
            return True
        else:
            print(f"❌ API调用失败，状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保服务器正在运行")
        return False
    except Exception as e:
        print(f"❌ 请求过程中出错: {e}")
        return False

def wait_for_server(max_wait=60):
    """等待服务器启动"""
    print("等待服务器启动...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get("http://localhost:8000/", timeout=5)
            if response.status_code == 200:
                print("✅ 服务器已启动")
                return True
        except:
            pass
        time.sleep(2)
    
    print("❌ 服务器启动超时")
    return False

if __name__ == "__main__":
    if wait_for_server():
        success = test_original_error()
        sys.exit(0 if success else 1)
    else:
        print("服务器未启动，无法进行测试")
        sys.exit(1)
