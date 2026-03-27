"""
表单生成Skill
根据用户需求生成动态表单，支持表单数据收集和验证
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 动态添加路径
backend_path = Path(__file__).parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from agents.skills.skill_base import Skill

logger = logging.getLogger(__name__)


class FormGeneratorSkill(Skill):
    """表单生成Skill"""

    name = "form_generator"
    description = "根据用户需求生成动态表单，支持表单数据收集和验证"
    tools = [
        "create_form",
        "validate_form",
        "save_form_data",
        "get_form",
        "list_forms"
    ]
    role = "表单生成和数据收集助手"
    responsibilities = [
        "理解用户表单需求（字段、验证、提示）",
        "生成FormSchema JSON结构",
        "发送表单卡片给用户",
        "处理表单提交和验证",
        "保存用户提交的数据"
    ]

    def __init__(self):
        super().__init__()
        self.form_templates = self._load_templates()
        logger.info("[FormGenerator] Skill初始化完成")

    def _load_templates(self) -> Dict[str, Dict]:
        """加载表单模板"""
        templates = {
            "user_feedback": {
                "title": "用户反馈表单",
                "description": "请填写您的宝贵意见",
                "sections": [
                    {
                        "title": "基本信息",
                        "fields": [
                            {
                                "id": "name",
                                "label": "姓名",
                                "type": "text",
                                "required": True,
                                "validation": {"minLength": 2, "maxLength": 50}
                            },
                            {
                                "id": "email",
                                "label": "邮箱",
                                "type": "email",
                                "required": True
                            }
                        ]
                    },
                    {
                        "title": "反馈内容",
                        "fields": [
                            {
                                "id": "feedback",
                                "label": "反馈内容",
                                "type": "textarea",
                                "required": True,
                                "validation": {"minLength": 10, "maxLength": 1000},
                                "placeholder": "请详细描述您的反馈内容..."
                            },
                            {
                                "id": "rating",
                                "label": "满意度评分",
                                "type": "select",
                                "required": True,
                                "options": [
                                    {"value": "5", "label": "非常满意"},
                                    {"value": "4", "label": "满意"},
                                    {"value": "3", "label": "一般"},
                                    {"value": "2", "label": "不满意"},
                                    {"value": "1", "label": "非常不满意"}
                                ]
                            }
                        ]
                    }
                ]
            },
            "task_feedback": {
                "title": "任务反馈表单",
                "description": "请反馈任务执行情况",
                "sections": [
                    {
                        "title": "任务信息",
                        "fields": [
                            {
                                "id": "task_id",
                                "label": "任务ID",
                                "type": "text",
                                "required": True,
                                "readonly": True
                            },
                            {
                                "id": "status",
                                "label": "执行状态",
                                "type": "select",
                                "required": True,
                                "options": [
                                    {"value": "completed", "label": "已完成"},
                                    {"value": "partial", "label": "部分完成"},
                                    {"value": "failed", "label": "执行失败"}
                                ]
                            }
                        ]
                    },
                    {
                        "title": "反馈详情",
                        "fields": [
                            {
                                "id": "description",
                                "label": "执行描述",
                                "type": "textarea",
                                "required": True,
                                "placeholder": "请描述任务执行的具体情况..."
                            },
                            {
                                "id": "attachments",
                                "label": "附件上传",
                                "type": "file_upload",
                                "required": False
                            }
                        ]
                    }
                ]
            }
        }
        return templates

    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        """
        执行表单生成

        Args:
            input_data: {
                "action": "generate|validate|submit",
                "template": "user_feedback|task_feedback|custom",
                "fields": [...],  # 自定义字段定义
                "form_id": "form_xxx",
                "data": {...}  # 表单提交数据
            }

        Returns:
            生成或验证结果
        """

        action = input_data.get("action", "generate")

        if action == "generate":
            return await self._generate_form(input_data, context)
        elif action == "validate":
            return await self._validate_form(input_data, context)
        elif action == "submit":
            return await self._submit_form(input_data, context)
        else:
            return {
                "success": False,
                "error": f"未知的操作: {action}"
            }

    async def _generate_form(self, input_data: Dict, context: Dict) -> Dict:
        """生成表单"""
        template_name = input_data.get("template", "user_feedback")
        custom_fields = input_data.get("fields")

        # 使用模板或自定义字段
        if template_name in self.form_templates:
            schema = self.form_templates[template_name].copy()
        elif custom_fields:
            schema = self._build_custom_schema(custom_fields)
        else:
            return {
                "success": False,
                "error": f"模板不存在: {template_name}"
            }

        # 添加表单元数据
        form_id = f"form_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        schema["id"] = form_id
        schema["state"] = "editable"

        logger.info(f"[FormGenerator] 生成表单: {form_id}")

        return {
            "success": True,
            "form_id": form_id,
            "schema": schema,
            "message": f"已生成表单: {schema.get('title', '未命名表单')}"
        }

    async def _validate_form(self, input_data: Dict, context: Dict) -> Dict:
        """验证表单"""
        form_id = input_data.get("form_id")
        data = input_data.get("data", {})
        schema = input_data.get("schema", {})

        if not form_id or not schema:
            return {
                "success": False,
                "error": "缺少form_id或schema"
            }

        # 验证必填字段
        errors = {}
        sections = schema.get("sections", [])

        for section in sections:
            for field in section.get("fields", []):
                field_id = field.get("id")
                required = field.get("required", False)
                field_type = field.get("type")

                value = data.get(field_id, "")

                # 验证必填
                if required and not value:
                    errors[field_id] = f"{field.get('label', 'Field')}是必填项"
                    continue

                # 验证格式
                if value:
                    validation_error = self._validate_field(field, value)
                    if validation_error:
                        errors[field_id] = validation_error

        if errors:
            return {
                "success": False,
                "errors": errors,
                "message": "表单验证失败"
            }

        logger.info(f"[FormGenerator] 验证通过: {form_id}")

        return {
            "success": True,
            "message": "表单验证通过"
        }

    async def _submit_form(self, input_data: Dict, context: Dict) -> Dict:
        """提交表单"""
        form_id = input_data.get("form_id")
        data = input_data.get("data", {})
        schema = input_data.get("schema", {})

        # 先验证
        validation_result = await self._validate_form(input_data, context)
        if not validation_result.get("success"):
            return validation_result

        # 保存数据
        submission = {
            "form_id": form_id,
            "submitted_at": datetime.now().isoformat(),
            "data": data,
            "user_id": context.get("user_id"),
            "username": context.get("username")
        }

        logger.info(f"[FormGenerator] 表单提交: {form_id}")

        return {
            "success": True,
            "submission_id": f"sub_{form_id}_{int(datetime.now().timestamp())}",
            "data": data,
            "message": "表单提交成功"
        }

    def _build_custom_schema(self, fields: List[Dict]) -> Dict:
        """根据自定义字段构建schema"""
        sections = [
            {
                "title": "自定义表单",
                "fields": fields
            }
        ]

        return {
            "title": "自定义表单",
            "description": "请填写下列信息",
            "sections": sections,
            "state": "editable"
        }

    def _validate_field(self, field: Dict, value: str) -> Optional[str]:
        """验证单个字段"""
        field_type = field.get("type")
        validation = field.get("validation", {})
        label = field.get("label", "Field")

        # 类型验证
        if field_type == "email":
            if "@" not in value or "." not in value:
                return f"{label}格式不正确"
        elif field_type == "number":
            try:
                float(value)
            except ValueError:
                return f"{label}必须是数字"

        # 长度验证
        if "minLength" in validation:
            if len(value) < validation["minLength"]:
                return f"{label}至少需要{validation['minLength']}个字符"

        if "maxLength" in validation:
            if len(value) > validation["maxLength"]:
                return f"{label}最多{validation['maxLength']}个字符"

        # 正则验证
        if "pattern" in validation:
            import re
            if not re.match(validation["pattern"], value):
                return f"{label}格式不符合要求"

        return None


__all__ = ['FormGeneratorSkill']
