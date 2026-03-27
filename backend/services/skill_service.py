"""
SkillService - Service layer for Skill management and loading

Provides unified interface for:
- Loading skills from YAML Frontmatter format
- Validating skill metadata and content
- Creating, updating, and deleting skills
- Caching and performance optimization
- Role-based skill filtering
"""

import os
import re
import time
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SkillService:
    """
    Skill management service for loading and managing skills with YAML Frontmatter

    Skill directory structure:
    .claude/skills/
    ├── skill-name/
    │   └── SKILL.md (with YAML Frontmatter)
    """

    # Required metadata fields
    REQUIRED_FIELDS = {'name', 'description', 'version', 'author', 'tags', 'category',
                       'available_for_manager', 'available_for_staff'}

    # Optional metadata fields
    OPTIONAL_FIELDS = {'priority', 'when_to_use', 'when_not_to_use', 'input_format',
                       'output_format', 'dependencies', 'requires_confirmation'}

    # Valid category values
    VALID_CATEGORIES = {'task', 'analysis', 'recommendation', 'generation', 'guidance'}

    # Valid priority values
    VALID_PRIORITIES = {'low', 'medium', 'high'}

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize SkillService with caching

        Args:
            ttl_seconds: Cache time-to-live in seconds (default 5 minutes)
        """
        self.skills_dir = self._get_skills_directory()
        self._cache = {}
        self._cache_timestamp = 0
        self._ttl = ttl_seconds

        logger.info(f"[SkillService] 初始化成功，Skills 目录: {self.skills_dir}")

    def _get_skills_directory(self) -> Path:
        """Get the .claude/skills directory path"""
        project_root = Path(__file__).parent.parent.parent
        skills_dir = project_root / ".claude" / "skills"
        return skills_dir

    def _is_cache_expired(self) -> bool:
        """Check if cache has expired"""
        return (time.time() - self._cache_timestamp) > self._ttl

    def _invalidate_cache(self) -> None:
        """Invalidate all caches"""
        self._cache = {}
        self._cache_timestamp = 0
        logger.info("[SkillService] 缓存已清除")

    def _parse_yaml_frontmatter(self, content: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Parse YAML Frontmatter from skill content

        Format:
        ---
        name: skill-name
        description: Description
        ...
        ---

        # Remaining content

        Args:
            content: Full SKILL.md content

        Returns:
            Tuple of (metadata_dict, remaining_content) or (None, content) if invalid
        """
        if not content.startswith('---'):
            return None, content

        try:
            lines = content.split('\n')
            end_idx = None

            # Find closing --- delimiter
            for i in range(1, len(lines)):
                if lines[i].strip() == '---':
                    end_idx = i
                    break

            if end_idx is None:
                return None, content

            # Extract and parse YAML
            frontmatter_str = '\n'.join(lines[1:end_idx])
            remaining_content = '\n'.join(lines[end_idx + 1:])

            try:
                metadata = yaml.safe_load(frontmatter_str) or {}
                return metadata, remaining_content
            except yaml.YAMLError as e:
                logger.error(f"[SkillService] YAML 解析错误: {e}")
                return None, content

        except Exception as e:
            logger.error(f"[SkillService] Frontmatter 解析失败: {e}")
            return None, content

    def validate_skill_name(self, name: str) -> Tuple[bool, str]:
        """
        Validate skill name format

        Rules:
        - Length: 3-50 characters
        - Only alphanumeric, hyphens, underscores
        - Cannot start/end with hyphen or underscore
        - Must be kebab-case or snake_case

        Args:
            name: Skill name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name:
            return False, "Skill 名称不能为空"

        if len(name) < 3 or len(name) > 50:
            return False, "Skill 名称长度必须在 3-50 字符之间"

        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-_]*[a-zA-Z0-9])?$', name):
            return False, "Skill 名称只能包含字母、数字、连字符、下划线，不能以连字符或下划线开头/结尾"

        return True, ""

    def validate_skill_md(self, content: str) -> Tuple[bool, List[str]]:
        """
        Validate SKILL.md content

        Checks:
        - YAML Frontmatter format
        - Required fields present
        - Field types and values valid
        - Markdown structure reasonable

        Args:
            content: Full SKILL.md content

        Returns:
            Tuple of (is_valid, error_list)
        """
        errors = []

        # Parse Frontmatter
        metadata, remaining = self._parse_yaml_frontmatter(content)

        if metadata is None:
            errors.append("缺少有效的 YAML Frontmatter")
            return False, errors

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in metadata:
                errors.append(f"缺少必需字段: {field}")

        if errors:
            return False, errors

        # Validate field types and values

        # name validation
        name = metadata.get('name', '')
        valid, msg = self.validate_skill_name(name)
        if not valid:
            errors.append(f"name 字段无效: {msg}")

        # description validation
        description = metadata.get('description', '')
        if not isinstance(description, str) or len(description) > 200:
            errors.append("description 必须是字符串且不超过 200 字符")

        # version validation (semver)
        version = metadata.get('version', '')
        if not re.match(r'^\d+\.\d+(\.\d+)?$', str(version)):
            errors.append("version 必须符合 semver 格式 (e.g., 1.0 或 1.0.0)")

        # tags validation
        tags = metadata.get('tags', [])
        if not isinstance(tags, list):
            errors.append("tags 必须是数组")

        # category validation
        category = metadata.get('category', '')
        if category not in self.VALID_CATEGORIES:
            errors.append(f"category 必须是以下之一: {', '.join(self.VALID_CATEGORIES)}")

        # priority validation (optional but must be valid if present)
        priority = metadata.get('priority')
        if priority is not None and priority not in self.VALID_PRIORITIES:
            errors.append(f"priority 必须是以下之一: {', '.join(self.VALID_PRIORITIES)}")

        # boolean fields
        for field in ['available_for_manager', 'available_for_staff', 'requires_confirmation']:
            if field in metadata:
                if not isinstance(metadata[field], bool):
                    errors.append(f"{field} 必须是布尔值 (true/false)")

        # Check Markdown content structure
        if not remaining.strip():
            errors.append("SKILL.md 必须包含 Markdown 内容")
        elif not re.search(r'^#\s+', remaining, re.MULTILINE):
            errors.append("SKILL.md 必须包含至少一个顶级标题 (# Title)")

        return len(errors) == 0, errors

    def get_all_skills(self, user_role: Optional[str] = None, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get all available skills with optional role-based filtering

        Args:
            user_role: Filter by role - 'manager' or 'staff' (None = no filtering)
            use_cache: Use cached results if available

        Returns:
            List of skill metadata dictionaries
        """
        # Check cache
        cache_key = f"all_skills_{user_role}"
        if use_cache and cache_key in self._cache and not self._is_cache_expired():
            logger.debug(f"[SkillService] 使用缓存: {cache_key}")
            return self._cache[cache_key]

        # Load skills directory
        if not self.skills_dir.exists():
            logger.warning(f"[SkillService] Skills 目录不存在: {self.skills_dir}")
            return []

        skills = []

        try:
            for skill_dir in self.skills_dir.iterdir():
                if not skill_dir.is_dir() or skill_dir.name.startswith('_'):
                    continue

                skill_data = self.get_skill(skill_dir.name, include_content=False)

                if skill_data is None:
                    continue

                metadata = skill_data.get('metadata', {})

                # Role-based filtering
                if user_role == 'manager':
                    if not metadata.get('available_for_manager', False):
                        continue
                elif user_role == 'staff':
                    if not metadata.get('available_for_staff', False):
                        continue

                skills.append(metadata)

            # Update cache
            self._cache[cache_key] = skills
            self._cache_timestamp = time.time()

            logger.info(f"[SkillService] 加载了 {len(skills)} 个 Skill (role={user_role})")
            return skills

        except Exception as e:
            logger.error(f"[SkillService] 加载 Skill 失败: {e}")
            return []

    def get_skill(self, name: str, include_content: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get skill details by name

        Args:
            name: Skill name
            include_content: Whether to include full SKILL.md content

        Returns:
            Dict with 'metadata' and optionally 'content', or None if not found
        """
        skill_path = self.skills_dir / name
        skill_md = skill_path / "SKILL.md"

        if not skill_md.exists():
            logger.warning(f"[SkillService] Skill 不存在: {name}")
            return None

        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()

            metadata, remaining = self._parse_yaml_frontmatter(content)

            if metadata is None:
                logger.error(f"[SkillService] {name} 缺少有效的 Frontmatter")
                return None

            # Ensure name field
            metadata.setdefault('name', name)
            metadata.setdefault('description', 'No description')

            result = {'metadata': metadata}

            if include_content:
                result['content'] = content

            return result

        except Exception as e:
            logger.error(f"[SkillService] 读取 Skill '{name}' 失败: {e}")
            return None

    def create_skill(self, name: str, description: str, tags: List[str],
                    content: str, author: str = "DJAgent User") -> Tuple[bool, str, Optional[str]]:
        """
        Create a new skill

        Args:
            name: Skill name (kebab-case)
            description: Short description
            tags: List of tags
            content: Full SKILL.md content with Frontmatter
            author: Author name

        Returns:
            Tuple of (success, message, error_message or None)
        """
        # Validate name
        valid, error = self.validate_skill_name(name)
        if not valid:
            return False, "", error

        # Check if already exists
        skill_path = self.skills_dir / name
        if skill_path.exists():
            error_msg = f"Skill '{name}' 已存在"
            logger.warning(f"[SkillService] {error_msg}")
            return False, "", error_msg

        # Validate content
        valid, errors = self.validate_skill_md(content)
        if not valid:
            error_msg = "; ".join(errors)
            logger.warning(f"[SkillService] Skill 内容验证失败: {error_msg}")
            return False, "", error_msg

        try:
            # Create directory
            skill_path.mkdir(parents=True, exist_ok=True)

            # Write SKILL.md
            skill_md = skill_path / "SKILL.md"
            with open(skill_md, 'w', encoding='utf-8') as f:
                f.write(content)

            # Invalidate cache
            self._invalidate_cache()

            message = f"Skill '{name}' 创建成功"
            logger.info(f"[SkillService] {message}")
            return True, message, None

        except Exception as e:
            error_msg = f"创建 Skill 失败: {str(e)}"
            logger.error(f"[SkillService] {error_msg}")
            return False, "", error_msg

    def update_skill(self, name: str, content: str) -> Tuple[bool, str, Optional[str]]:
        """
        Update an existing skill

        Args:
            name: Skill name
            content: New SKILL.md content

        Returns:
            Tuple of (success, message, error_message or None)
        """
        skill_path = self.skills_dir / name
        skill_md = skill_path / "SKILL.md"

        if not skill_md.exists():
            error_msg = f"Skill '{name}' 不存在"
            logger.warning(f"[SkillService] {error_msg}")
            return False, "", error_msg

        # Validate content
        valid, errors = self.validate_skill_md(content)
        if not valid:
            error_msg = "; ".join(errors)
            logger.warning(f"[SkillService] Skill 内容验证失败: {error_msg}")
            return False, "", error_msg

        try:
            with open(skill_md, 'w', encoding='utf-8') as f:
                f.write(content)

            # Invalidate cache
            self._invalidate_cache()

            message = f"Skill '{name}' 更新成功"
            logger.info(f"[SkillService] {message}")
            return True, message, None

        except Exception as e:
            error_msg = f"更新 Skill 失败: {str(e)}"
            logger.error(f"[SkillService] {error_msg}")
            return False, "", error_msg

    def delete_skill(self, name: str) -> Tuple[bool, str, Optional[str]]:
        """
        Delete a skill

        Args:
            name: Skill name

        Returns:
            Tuple of (success, message, error_message or None)
        """
        skill_path = self.skills_dir / name

        if not skill_path.exists():
            error_msg = f"Skill '{name}' 不存在"
            logger.warning(f"[SkillService] {error_msg}")
            return False, "", error_msg

        try:
            import shutil
            shutil.rmtree(skill_path)

            # Invalidate cache
            self._invalidate_cache()

            message = f"Skill '{name}' 已删除"
            logger.info(f"[SkillService] {message}")
            return True, message, None

        except Exception as e:
            error_msg = f"删除 Skill 失败: {str(e)}"
            logger.error(f"[SkillService] {error_msg}")
            return False, "", error_msg

    def export_skill(self, name: str, format: str = 'json') -> Tuple[bool, Any, Optional[str]]:
        """
        Export skill in JSON or YAML format

        Args:
            name: Skill name
            format: Export format ('json' or 'yaml')

        Returns:
            Tuple of (success, exported_data, error_message or None)
        """
        skill_data = self.get_skill(name, include_content=True)

        if skill_data is None:
            return False, None, f"Skill '{name}' 不存在"

        try:
            if format == 'json':
                import json
                return True, json.dumps(skill_data, ensure_ascii=False, indent=2), None
            elif format == 'yaml':
                return True, yaml.dump(skill_data, allow_unicode=True, default_flow_style=False), None
            else:
                return False, None, f"不支持的导出格式: {format}"
        except Exception as e:
            return False, None, f"导出 Skill 失败: {str(e)}"

    def import_skill(self, data: Dict[str, Any], format: str = 'json') -> Tuple[bool, str, Optional[str]]:
        """
        Import skill from exported data

        Args:
            data: Skill data
            format: Import format ('json' or 'yaml')

        Returns:
            Tuple of (success, message, error_message or None)
        """
        try:
            if 'metadata' not in data or 'content' not in data:
                return False, "", "缺少 metadata 或 content 字段"

            metadata = data['metadata']
            name = metadata.get('name')
            content = data['content']

            if not name:
                return False, "", "缺少 Skill 名称"

            # Check if already exists
            if (self.skills_dir / name).exists():
                return False, "", f"Skill '{name}' 已存在"

            return self.create_skill(
                name=name,
                description=metadata.get('description', ''),
                tags=metadata.get('tags', []),
                content=content,
                author=metadata.get('author', 'DJAgent User')
            )

        except Exception as e:
            return False, "", f"导入 Skill 失败: {str(e)}"


# Global instance
_skill_service = None


def get_skill_service() -> SkillService:
    """Get or create global SkillService instance"""
    global _skill_service
    if _skill_service is None:
        _skill_service = SkillService()
    return _skill_service
