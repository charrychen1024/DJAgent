"""
Skills API Routes

提供 Skill 的 REST API 接口：
- GET /api/skills - 获取所有可用 Skill 列表
- GET /api/skills/{name} - 获取特定 Skill 详情
- POST /api/skills - 创建新 Skill
- PUT /api/skills/{name} - 更新 Skill
- DELETE /api/skills/{name} - 删除 Skill
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from typing import List, Dict, Any, Optional
import os
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/skills", tags=["skills"])

# 导入 SkillService 用于正确的 YAML 解析
from services.skill_service import SkillService

# 创建 SkillService 实例
_skill_service = SkillService()


def get_skills_directory():
    """获取 Skills 目录路径"""
    project_root = Path(__file__).parent.parent.parent
    skills_dir = project_root / ".claude" / "skills"
    return skills_dir


def load_skill_metadata(skill_name: str) -> Dict[str, Any]:
    """
    从 SKILL.md 中加载 Skill 元数据

    使用 SkillService 进行正确的 YAML Frontmatter 解析，
    支持多行文本（| 语法）和正确的类型转换
    """
    skills_dir = get_skills_directory()
    skill_path = skills_dir / skill_name
    skill_md = skill_path / "SKILL.md"

    if not skill_md.exists():
        return None

    try:
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()

        # 使用 SkillService 正确解析 YAML Frontmatter
        metadata, _ = _skill_service._parse_yaml_frontmatter(content)

        if metadata:
            # 确保 name 字段存在
            metadata['name'] = metadata.get('name', skill_name)
            return metadata

        return None
    except Exception as e:
        logger.error(f"Error loading skill metadata: {e}")
        return None


def get_all_skills() -> List[Dict[str, Any]]:
    """获取所有可用的 Skill 列表"""
    skills_dir = get_skills_directory()

    if not skills_dir.exists():
        return []

    skills = []
    try:
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
                metadata = load_skill_metadata(skill_dir.name)
                if metadata:
                    # 确保必需字段
                    metadata['name'] = metadata.get('name', skill_dir.name)
                    metadata['description'] = metadata.get('description', 'No description')
                    skills.append(metadata)
    except Exception as e:
        logger.error(f"Error loading skills: {e}")

    return skills


@router.get("")
async def list_skills(role: Optional[str] = Query(None, description="Filter by role: manager or staff")):
    """
    获取所有可用的 Skill 列表

    Query Parameters:
        - role: 可选，按角色过滤 - 'manager' 或 'staff'

    返回示例:
    {
      "skills": [
        {
          "name": "task-creator",
          "description": "Create and assign verification tasks",
          "tags": ["task-management"],
          "available_for_manager": true,
          "available_for_staff": false,
          "when_to_use": "User wants to create a task"
        },
        ...
      ]
    }
    """
    try:
        # 使用 SkillService 进行正确解析和角色过滤
        skills = _skill_service.get_all_skills(user_role=role)
        return {"skills": skills, "total": len(skills)}
    except Exception as e:
        logger.error(f"Error listing skills: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list skills: {str(e)}")


@router.get("/{skill_name}")
async def get_skill(skill_name: str):
    """
    获取特定 Skill 的详情

    包含 SKILL.md 的完整内容
    """
    try:
        metadata = load_skill_metadata(skill_name)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        # 读取完整的 SKILL.md 内容
        skills_dir = get_skills_directory()
        skill_md = skills_dir / skill_name / "SKILL.md"

        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            "name": skill_name,
            "metadata": metadata,
            "content": content
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting skill: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get skill: {str(e)}")


@router.post("")
async def create_skill(
    name: str = Form(...),
    description: str = Form(...),
    tags: str = Form(default=""),
    content: str = Form(...)
):
    """
    创建新 Skill

    参数:
    - name: Skill 名称 (kebab-case, 如 'my-skill')
    - description: Skill 描述
    - tags: 标签 (逗号分隔)
    - content: SKILL.md 内容
    """
    try:
        # 验证 Skill 名称格式
        if not name or not name.replace('-', '').replace('_', '').isalnum():
            raise HTTPException(status_code=400, detail="Invalid skill name format")

        skills_dir = get_skills_directory()
        skill_path = skills_dir / name

        # 检查是否已存在
        if skill_path.exists():
            raise HTTPException(status_code=409, detail=f"Skill '{name}' already exists")

        # 创建 Skill 目录
        skill_path.mkdir(parents=True, exist_ok=True)

        # 写入 SKILL.md
        skill_md = skill_path / "SKILL.md"
        with open(skill_md, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Created skill: {name}")
        return {"message": f"Skill '{name}' created successfully", "name": name}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating skill: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create skill: {str(e)}")


@router.put("/{skill_name}")
async def update_skill(
    skill_name: str,
    content: str = Form(...)
):
    """
    更新现有 Skill
    """
    try:
        skills_dir = get_skills_directory()
        skill_path = skills_dir / skill_name
        skill_md = skill_path / "SKILL.md"

        if not skill_md.exists():
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        # 更新 SKILL.md
        with open(skill_md, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Updated skill: {skill_name}")
        return {"message": f"Skill '{skill_name}' updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating skill: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update skill: {str(e)}")


@router.delete("/{skill_name}")
async def delete_skill(skill_name: str):
    """
    删除 Skill
    """
    try:
        skills_dir = get_skills_directory()
        skill_path = skills_dir / skill_name

        if not skill_path.exists():
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        # 删除 Skill 目录
        import shutil
        shutil.rmtree(skill_path)

        logger.info(f"Deleted skill: {skill_name}")
        return {"message": f"Skill '{skill_name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting skill: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete skill: {str(e)}")


@router.post("/reload-session/{user_id}")
async def reload_session(user_id: str):
    """
    重新加载用户会话

    在创建/更新/删除 Skill 后调用此端点，
    强制清除用户的 Agent 会话缓存，
    使得 Agent 重新发现和加载 Skills
    """
    try:
        from agents.session_manager import clear_user_session
        result = clear_user_session(user_id)
        return result
    except Exception as e:
        logger.error(f"Error reloading session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload session: {str(e)}")
