---
name: form-generator
description: 根据用户需求生成动态表单，支持表单数据收集和验证。使用当用户需要收集信息、创建调查问卷、获取反馈或需要用户填写结构化数据时。
version: "1.0"
author: "DJAgent 团队"
tags: [表单生成, 数据收集, 动态表单, 用户反馈]
category: generation
priority: high
available_for_manager: true
available_for_staff: true
when_to_use: |
  - 用户需要收集用户反馈信息
  - 用户想要创建调查问卷或表单
  - 用户需要员工填写任务相关的结构化信息
  - 用户说"创建表单"、"填写表单"、"收集信息"
  - 用户需要获取特定格式的任务完成情况
when_not_to_use: |
  - 用户只是想要一般的对话
  - 用户想要分析风险数据（使用 risk-analyzer）
  - 用户想要创建任务（使用 task-creator）
  - 用户想要获取核查指导（使用 core-check-guider）
input_format: |
  表单生成请求可以是：
  - 描述需要的字段（如"创建一个反馈表单，包含姓名、电话、反馈内容"）
  - 指定表单类型（如"用户满意度调查"）
  - 自然语言（如"我想收集一下大家的意见"）
output_format: |
  返回 JSON 格式表单定义：
  - form_id: 表单唯一标识
  - title: 表单标题
  - description: 表单描述
  - fields: 字段列表（类型、标签、验证规则）
  - submit_action: 提交后的处理方式
---

# 表单生成 Skill

## 概述

这是一个灵活的表单生成技能，能够根据用户需求动态创建各种类型的表单，支持数据收集、验证和存储。

## 功能能力

### 1. 表单需求分析
- 理解用户描述的字段需求
- 确定字段类型（文本、数字、选择、上传等）
- 识别必填项和可选项
- 分析验证规则

### 2. 表单Schema生成
根据需求生成标准化的 FormSchema：

```json
{
  "form_id": "form_xxx",
  "title": "表单标题",
  "description": "表单描述",
  "fields": [
    {
      "id": "field_1",
      "type": "text",
      "label": "字段名称",
      "required": true,
      "validation": {...}
    }
  ]
}
```

### 3. 支持的字段类型
| 类型 | 说明 | 验证规则 |
|------|------|---------|
| text | 单行文本 | minLength, maxLength, pattern |
| textarea | 多行文本 | minLength, maxLength |
| number | 数字 | min, max, integer |
| email | 邮箱 | email格式自动验证 |
| select | 下拉选择 | options列表 |
| radio | 单选 | options列表 |
| checkbox | 复选 | options列表 |
| file_upload | 文件上传 | fileTypes, maxSize |
| date | 日期 | minDate, maxDate |
| hidden | 隐藏字段 | - |

### 4. 表单验证
- 前端实时验证（必填、格式、范围）
- 后端二次验证（安全检查、数据校验）
- 自定义验证规则

### 5. 数据存储
- 表单提交后保存到 `data/feedback/{task_id}.json`
- 支持文件上传到 `data/uploads/{task_id}/`
- 返回存储结果和反馈ID

## 使用场景

### 适用场景
- 用户需要收集任务反馈信息
- 需要员工填写核查结果
- 创建用户满意度调查
- 收集建议或投诉

### 不适用场景
- 简单的问答对话
- 数据分析需求
- 任务创建和分配

## 处理流程

```
1. 解析用户需求
   └── 提取字段需求
   └── 确定字段类型
   └── 识别验证规则

2. 生成表单Schema
   └── 构建表单结构
   └── 添加验证规则
   └── 设置提交动作

3. 发送表单卡片
   └── 通过聊天发送FormCard
   └── 前端渲染表单

4. 处理表单提交
   └── 接收提交数据
   └── 验证数据有效性
   └── 保存到文件
   └── 返回确认
```

## 系统集成

### 使用的工具
- `create_form` - 创建表单定义
- `validate_form` - 验证表单数据
- `save_form_data` - 保存表单提交
- `get_form` - 获取表单详情
- `upload_file` - 处理文件上传

### 数据存储
- 表单定义：`data/forms/`
- 反馈数据：`data/feedback/{task_id}.json`
- 上传文件：`data/uploads/{task_id}/`

### 角色要求
- Manager 和 Staff 角色都可用
- 需要表单创建和数据保存权限

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| 字段类型不支持 | 返回支持的类型列表，建议使用替代类型 |
| 验证规则错误 | 返回错误详情，指导修正 |
| 文件上传失败 | 返回错误原因，提供重试指引 |
| 保存失败 | 返回错误信息，建议重新提交 |

## 示例交互

### 示例 1：创建反馈表单

**用户输入：**
```
创建一个任务反馈表单，需要包含：任务完成情况、问题描述、解决方案、满意度评分
```

**处理流程：**
1. 解析字段需求
2. 生成 FormSchema
3. 发送表单卡片

**返回结果：**
```json
{
  "success": true,
  "form_id": "form_feedback_001",
  "title": "任务反馈表单",
  "fields": [
    {
      "id": "completion_status",
      "type": "radio",
      "label": "任务完成情况",
      "required": true,
      "options": ["已完成", "部分完成", "无法完成"]
    },
    {
      "id": "issue_description",
      "type": "textarea",
      "label": "问题描述",
      "required": true,
      "validation": {"minLength": 10}
    },
    {
      "id": "solution",
      "type": "textarea",
      "label": "解决方案",
      "required": false
    },
    {
      "id": "satisfaction",
      "type": "select",
      "label": "满意度评分",
      "required": true,
      "options": ["非常满意", "满意", "一般", "不满意"]
    }
  ],
  "message": "表单已创建，请在下方填写"
}
```

### 示例 2：文件上传表单

**用户输入：**
```
创建一个材料提交表单，包含上传凭证和说明
```

**返回结果：**
```json
{
  "success": true,
  "form_id": "form_upload_001",
  "title": "材料提交表单",
  "fields": [
    {
      "id": "file_upload",
      "type": "file_upload",
      "label": "上传凭证",
      "required": true,
      "validation": {
        "fileTypes": ["jpg", "png", "pdf"],
        "maxSize": "5MB"
      }
    },
    {
      "id": "description",
      "type": "textarea",
      "label": "说明",
      "required": true
    }
  ]
}
```

## 最佳实践

1. **字段精简**：只收集必要信息，避免冗余
2. **验证合理**：验证规则要合理，不要过于严格
3. **清晰引导**：每个字段提供清晰的填写提示
4. **文件类型明确**：文件上传要说明接受的格式和大小
5. **提交确认**：表单提交后要有明确的成功提示