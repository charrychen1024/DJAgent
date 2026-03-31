---
name: summary-generator
description: 根据核查结果和上传材料，生成反馈总结报告。使用当任务完成后需要生成总结报告、更新任务状态或需要整理反馈内容时。
version: "1.0"
author: "DJAgent 团队"
tags: [总结生成, 报告生成, 任务完成, 反馈汇总]
category: generation
priority: high
available_for_manager: true
available_for_staff: false
when_to_use: |
  - 任务完成后需要生成总结报告
  - 用户说"生成总结"、"生成报告"
  - 用户想要查看任务反馈的汇总信息
  - 员工提交反馈后需要整理成报告
  - 需要更新任务状态为"已完成"
when_not_to_use: |
  - Staff 角色使用（此技能仅限 Manager）
  - 用户只是想要一般的对话
  - 用户想要创建新任务（使用 task-creator）
  - 用户想要分析风险数据（使用 risk-analyzer）
  - 任务尚未完成，还在处理中
input_format: |
  总结生成请求可以是：
  - 指定任务ID，生成该任务的反馈总结
  - 描述需要总结的内容
  - 自然语言（如"帮我看看这个任务的反馈总结"）
output_format: |
  返回 JSON 格式总结报告：
  - task_id: 任务ID
  - task_summary: 任务摘要
  - feedback_summary: 反馈内容汇总
  - uploaded_files: 上传文件列表
  - conclusion: 核查结论
  - task_status: 更新后的任务状态
---

# 总结生成 Skill

## 概述

这是一个专业的报告生成技能，用于将一线员工的核查反馈整理成结构化的总结报告，并更新任务状态。

## 功能能力

### 1. 任务信息获取
- 获取任务详情（任务描述、执行人、截止时间）
- 获取风险数据摘要
- 获取任务状态历史

### 2. 反馈内容整理
- 汇总员工的文字反馈内容
- 整理上传的文件和材料
- 提取关键信息点

### 3. 文件处理
- 读取上传的凭证照片
- 解析上传的 PDF/Word 文档
- 提取文件中的关键信息

### 4. 总结报告生成
生成结构化的总结报告，包含：
- **任务概述**：任务内容、类型、执行人
- **反馈摘要**：文字反馈的关键点
- **材料清单**：上传的文件列表
- **核查结论**：基于反馈的结论
- **后续建议**：如有问题，给出建议

### 5. 任务状态更新
- 将任务状态从"反馈中"更新为"已完成"
- 记录完成时间和总结内容
- 更新任务的 feedback_summary 字段

## 使用场景

### 适用场景
- 员工已完成核查并提交反馈
- 需要将反馈整理成报告
- 需要更新任务状态

### 不适用场景
- Staff 角色使用（仅限 Manager）
- 任务尚未完成
- 想要创建新任务

## 处理流程

```
1. 获取任务信息
   └── 调用 get_task_detail 获取详情
   └── 获取风险数据
   └── 检查任务状态

2. 获取反馈内容
   └── 读取反馈文件 data/feedback/{task_id}.json
   └── 获取上传的文件列表
   └── 解析文件内容

3. 生成总结报告
   └── 整理文字反馈
   └── 汇总上传材料
   └── 给出核查结论

4. 更新任务状态
   └── 修改状态为"已完成"
   └── 记录完成时间
   └── 保存总结内容

5. 返回报告
   └── 返回结构化报告
```

## 系统集成

### 使用的工具
- `get_task_detail` - 获取任务详情
- `get_feedback` - 获取反馈内容
- `list_uploaded_files` - 列出上传文件
- `update_task_status` - 更新任务状态
- `parse_pdf` - 解析 PDF 文件
- `parse_image` - 解析图片

### 数据来源
- 任务信息：`data/tasks.csv`
- 反馈数据：`data/feedback/{task_id}.json`
- 上传文件：`data/uploads/{task_id}/`

### 角色要求
- 仅 Manager 角色可用
- 需要读取反馈和更新任务权限

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| 任务不存在 | 返回"未找到任务" |
| 任务尚未完成反馈 | 返回"任务尚未完成，无法生成总结" |
| 无反馈内容 | 返回"未找到反馈内容" |
| 更新状态失败 | 返回错误详情，但报告仍可查看 |

## 示例交互

### 示例 1：生成总结报告

**用户输入：**
```
帮我生成这个任务的总结报告
```

**处理流程：**
1. 获取任务详情
2. 读取反馈内容
3. 整理上传材料
4. 生成总结报告
5. 更新任务状态

**返回结果：**
```json
{
  "success": true,
  "task_id": "TASK_20260326_001",
  "task_summary": {
    "task_type": "日度核查",
    "risk_description": "运单WLYD001重量异常",
    "assigned_to": "张三 (EMP_003)",
    "feedback_deadline": "2026-03-27 18:00:00"
  },
  "feedback_summary": {
    "completion_status": "已完成",
    "description": "经核实，该运单实际重量为25.3kg，与系统记录23.5kg存在1.8kg差异。原因：货物打包时增加了包装材料。",
    "key_points": [
      "实际称重：25.3kg",
      "系统记录：23.5kg",
      "差异原因：包装材料增加"
    ]
  },
  "uploaded_files": [
    {"filename": "weighing_photo.jpg", "type": "image"},
    {"filename": "invoice.pdf", "type": "document"}
  ],
  "conclusion": "经核查，重量差异原因为包装材料增加，不存在异常情况。建议：加强打包环节重量复核。",
  "task_status": "已完成",
  "completion_time": "2026-03-26 15:30:00"
}
```

### 示例 2：查看反馈汇总

**用户输入：**
```
看看这个任务的反馈情况
```

**返回结果：**
```json
{
  "success": true,
  "task_id": "TASK_20260326_002",
  "feedback_summary": {
    "status": "部分完成",
    "issues": "部分材料因技术问题无法上传，已说明情况",
    "pending_items": ["称重视频"]
  },
  "uploaded_files": [
    {"filename": "photo1.jpg"},
    {"filename": "description.txt"}
  ],
  "recommendation": "建议跟进补齐材料后再次提交"
}
```

## 最佳实践

1. **提取关键信息**：不要简单复制反馈，而是提取关键点
2. **核实材料完整性**：检查上传的材料是否齐全
3. **给出明确结论**：基于事实给出核查结论
4. **提供后续建议**：如有问题，给出改进建议
5. **及时更新状态**：生成报告后及时更新任务状态