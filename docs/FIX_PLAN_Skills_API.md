# Skills API 修复计划

## 问题汇总

### 1. YAML 解析问题
- **问题**：`skills_api.py` 的 `load_skill_metadata()` 使用简单 split 解析，无法正确处理：
  - 多行文本 (`|`) 格式
  - 带引号的字符串
- **现状**：返回 `"|"` 而不是实际内容
- **修复**：使用 `SkillService._parse_yaml_frontmatter()` 正确解析

### 2. 角色过滤缺失
- **问题**：API 不支持 `?role=manager/staff` 参数
- **现状**：Manager 和 Staff 都返回全部 6 个 Skills
- **预期**：
  - Manager: 5个 (除 core-check-guider)
  - Staff: 2个 (core-check-guider, form-generator)
- **修复**：添加 `role` 查询参数，使用 `SkillService.get_all_skills(user_role=...)`

### 3. task-creator description 英文问题
- **问题**：description 是英文，用户期望中文
- **现状**：`"Create and assign verification tasks..."`
- **预期**：中文描述

---

## 修复任务

### Task 1: 修复 YAML 解析 + 添加角色过滤
**文件**: `/backend/api/skills_api.py`

修改 `list_skills()` 函数：
1. 添加 `role: Optional[str] = None` 查询参数
2. 使用 `SkillService.get_all_skills(user_role=role)` 获取正确过滤的 Skills
3. 移除手动解析逻辑，直接使用 `SkillService`

### Task 2: 修改 task-creator description
**文件**: `/backend/.claude/skills/task-creator/SKILL.md`

将 description 从英文改为中文：
```yaml
description: 基于风险分析结果创建和分配核查任务
```

---

## 参考代码

```python
# skills_api.py 需要修改的部分
from typing import Optional

@router.get("")
async def list_skills(role: Optional[str] = None):
    """获取所有可用的 Skill 列表"""
    try:
        # 使用 SkillService 进行正确解析和角色过滤
        skills = _skill_service.get_all_skills(user_role=role)
        return {"skills": skills, "total": len(skills)}
    except Exception as e:
        logger.error(f"Error listing skills: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list skills: {str(e)}")
```

---

## 验收标准

| 测试项 | 预期结果 |
|--------|----------|
| `when_to_use` | 多行文本内容，不是 `\|` |
| `input_format` | 多行文本内容，不是 `\|` |
| `output_format` | 多行文本内容，不是 `\|` |
| `version` | 数字 `1.0`，不是字符串 `"1.0"` |
| `author` | `DJAgent 团队`，不是 `DJAgent Team` |
| `?role=manager` | 5个 Skills |
| `?role=staff` | 2个 Skills |
| task-creator description | 中文 |