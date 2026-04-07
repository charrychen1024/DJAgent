#!/usr/bin/env python3
"""DJAgent 完整测试脚本"""
import urllib.request
import urllib.parse
import json
import time

BASE_URL = "http://localhost:5008"

def test_endpoint(path, method="GET", data=None):
    """测试 API 端点"""
    try:
        url = f"{BASE_URL}{path}"
        
        if method == "GET":
            req = urllib.request.Request(url)
        else:
            req = urllib.request.Request(url, data=data.encode('utf-8') if data else None)
            req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return None, str(e)

# ============ 测试 Skills API ============
print("=" * 70)
print("【测试 1】Skills API - 获取所有 Skills")
print("=" * 70)

status, data = test_endpoint("/api/skills")
if status == 200:
    skills = data.get("skills", [])
    print(f"✅ 成功 - 共 {len(skills)} 个 Skills\n")
    
    for s in skills:
        print(f"  📦 {s.get('name')}")
        print(f"     description: {s.get('description', '')[:50]}...")
        print(f"     author: {s.get('author')}")
        print(f"     version: {s.get('version')} ({type(s.get('version')).__name__})")
        
        when = s.get('when_to_use', '')
        if '|' in when:
            print(f"     when_to_use: ❌ 解析错误 - '{when[:30]}...'")
        else:
            print(f"     when_to_use: ✅ 正常")
        print()
else:
    print(f"❌ 失败: {data}")

# ============ 测试角色过滤 ============
print("=" * 70)
print("【测试 2】角色过滤 - Manager")
print("=" * 70)

status, data = test_endpoint("/api/skills?role=manager")
if status == 200:
    skills = data.get("skills", [])
    print(f"✅ Manager 角色可用: {len(skills)} 个")
    for s in skills:
        print(f"  - {s.get('name')}")
else:
    print(f"❌ 失败: {data}")

print("\n" + "=" * 70)
print("【测试 3】角色过滤 - Staff")
print("=" * 70)

status, data = test_endpoint("/api/skills?role=staff")
if status == 200:
    skills = data.get("skills", [])
    print(f"✅ Staff 角色可用: {len(skills)} 个")
    for s in skills:
        print(f"  - {s.get('name')}")
else:
    print(f"❌ 失败: {data}")

# ============ 测试用户列表 ============
print("\n" + "=" * 70)
print("【测试 4】用户列表")
print("=" * 70)

status, data = test_endpoint("/api/users")
if status == 200:
    # API 返回的是列表
    users = data if isinstance(data, list) else data.get("users", [])
    print(f"✅ 成功 - 共 {len(users)} 个用户")
    for u in users[:3]:
        print(f"  - {u.get('username')} ({u.get('employee_id')}) - {u.get('role')}")
else:
    print(f"❌ 失败: {data}")

# ============ 测试任务列表 ============
print("\n" + "=" * 70)
print("【测试 5】任务列表")
print("=" * 70)

status, data = test_endpoint("/api/tasks?employee_id=EMP_001")
if status == 200:
    tasks = data if isinstance(data, list) else data.get("tasks", [])
    print(f"✅ 成功 - 共 {len(tasks)} 个任务")
else:
    print(f"❌ 失败: {data}")

# ============ 测试 Chat API ============
print("\n" + "=" * 70)
print("【测试 6】AI 对话测试")
print("=" * 70)

# 构造 FormData 格式的请求
chat_data = {
    "message": "你好，请介绍一下你自己",
    "user_id": "EMP_001"
}

# 使用 application/x-www-form-urlencoded 格式
encoded_data = urllib.parse.urlencode(chat_data)

try:
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=encoded_data.encode('utf-8'),
        method='POST'
    )
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(f"✅ 对话成功!")
        print(f"  回复: {result.get('reply', '')[:200]}...")
except Exception as e:
    print(f"❌ 对话失败: {e}")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)