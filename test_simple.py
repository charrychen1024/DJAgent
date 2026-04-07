#!/usr/bin/env python3
"""简单测试 DJAgent Skills API"""
import urllib.request
import json

BASE_URL = "http://localhost:5005"

def test_endpoint(path):
    """测试 API 端点"""
    print(f"\n{'='*60}")
    print(f"GET {path}")
    print('='*60)
    
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}")
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read().decode('utf-8')
            result = json.loads(data)
            
            if "skills" in result:
                skills = result["skills"]
                print(f"状态: 成功")
                print(f"Skills 总数: {len(skills)}")
                
                for skill in skills:
                    name = skill.get('name', 'N/A')
                    desc = skill.get('description', 'N/A')[:50]
                    author = skill.get('author', 'N/A')
                    version = skill.get('version', 'N/A')
                    when_to_use = skill.get('when_to_use', '')
                    
                    print(f"\n[{name}]")
                    print(f"  description: {desc}...")
                    print(f"  author: {author}")
                    print(f"  version: {version} (type: {type(version).__name__})")
                    
                    # 检查 when_to_use
                    if '|' in when_to_use:
                        print(f"  when_to_use: ❌ 包含 '|' - 解析问题")
                    else:
                        print(f"  when_to_use: ✅ 正常")
                        
                    print(f"  available_for_manager: {skill.get('available_for_manager')}")
                    print(f"  available_for_staff: {skill.get('available_for_staff')}")
            else:
                print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}")
                
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    test_endpoint("/api/skills")
    test_endpoint("/api/skills?role=manager")
    test_endpoint("/api/skills?role=staff")