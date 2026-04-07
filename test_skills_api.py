#!/usr/bin/env python3
"""测试 DJAgent Skills API"""

import httpx
import json
import sys

BASE_URL = "http://localhost:5005"

def test_skills():
    """测试 Skills API"""
    print("=" * 60)
    print("测试 1: GET /api/skills (获取所有 Skills)")
    print("=" * 60)
    
    try:
        response = httpx.get(f"{BASE_URL}/api/skills", timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            skills = data.get("skills", [])
            print(f"Skills 总数: {len(skills)}")
            
            for skill in skills:
                print(f"\n--- {skill.get('name')} ---")
                print(f"  description: {skill.get('description')}")
                print(f"  author: {skill.get('author')}")
                print(f"  version: {skill.get('version')} (type: {type(skill.get('version')).__name__})")
                print(f"  available_for_manager: {skill.get('available_for_manager')}")
                print(f"  available_for_staff: {skill.get('available_for_staff')}")
                
                # 检查多行文本字段
                when_to_use = skill.get('when_to_use', '')
                if when_to_use and '|' not in when_to_use:
                    print(f"  when_to_use: {when_to_use[:100]}...")
                else:
                    print(f"  when_to_use: '{when_to_use}' (有问题的值)")
        else:
            print(f"错误: {response.text}")
            
    except Exception as e:
        print(f"请求失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试 2: GET /api/skills?role=manager")
    print("=" * 60)
    
    try:
        response = httpx.get(f"{BASE_URL}/api/skills?role=manager", timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            skills = data.get("skills", [])
            print(f"Manager 可用 Skills: {len(skills)}")
            for skill in skills:
                print(f"  - {skill.get('name')}")
    except Exception as e:
        print(f"请求失败: {e}")

    print("\n" + "=" * 60)
    print("测试 3: GET /api/skills?role=staff")
    print("=" * 60)
    
    try:
        response = httpx.get(f"{BASE_URL}/api/skills?role=staff", timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            skills = data.get("skills", [])
            print(f"Staff 可用 Skills: {len(skills)}")
            for skill in skills:
                print(f"  - {skill.get('name')}")
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    test_skills()