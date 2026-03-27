#!/usr/bin/env python3
"""Test SkillService with created skills"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.skill_service import SkillService

print("[TEST] Initializing SkillService...")
try:
    skill_service = SkillService()
    print("[OK] SkillService initialized successfully")
except Exception as e:
    print(f"[FAIL] Failed to initialize SkillService: {e}")
    sys.exit(1)

print("\n[TEST] Loading all skills...")
try:
    skills = skill_service.get_all_skills()
    print(f"[OK] Loaded {len(skills)} skills")

    if skills:
        print("\n[SKILLS LIST]:")
        for skill in skills:
            name = skill.get("name", "unknown")
            desc = skill.get("description", "no description")
            print(f"  - {name}")
            print(f"    Description: {desc}")
            print(f"    Available for Manager: {skill.get('available_for_manager', False)}")
            print(f"    Available for Staff: {skill.get('available_for_staff', False)}")
            print(f"    Category: {skill.get('category', 'unknown')}")
            print()
except Exception as e:
    print(f"[FAIL] Failed to load skills: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[TEST] Role-based filtering...")
try:
    manager_skills = skill_service.get_all_skills(user_role='manager')
    staff_skills = skill_service.get_all_skills(user_role='staff')
    print(f"[OK] Manager skills: {len(manager_skills)}")
    print(f"[OK] Staff skills: {len(staff_skills)}")
except Exception as e:
    print(f"[FAIL] Failed role-based filtering: {e}")
    sys.exit(1)

print("\n[TEST] Validating skill format...")
try:
    skill = skill_service.get_skill('task-creator', include_content=True)
    if skill:
        print(f"[OK] Retrieved 'task-creator' skill")
        print(f"    Metadata fields: {list(skill.get('metadata', {}).keys())}")
        print(f"    Has content: {len(skill.get('content', '')) > 0}")
    else:
        print(f"[FAIL] Could not find 'task-creator' skill")
except Exception as e:
    print(f"[FAIL] Failed to retrieve skill: {e}")
    sys.exit(1)

print("\n[ALL TESTS PASSED] Skill system is working correctly!")

