---
name: task-creator
description: 基于风险分析结果创建和分配核查任务
version: "1.0"
author: "DJAgent 团队"
tags: [task-management, workflow, automation, risk-verification]
category: task
priority: high
available_for_manager: true
available_for_staff: false
when_to_use: |
  - 用户想要创建新的核查任务
  - 用户提及分配工作给具体员工
  - 用户想要发起风险核查流程
  - 用户说"创建任务"、"分配任务"、"下发任务"等
when_not_to_use: |
  - 用户只是在问一般问题
  - 用户想查看现有任务（使用 list_tasks）
  - 用户在给现有任务提供反馈
  - 用户想分析风险数据（使用 risk-analyzer）
input_format: |
  任务创建请求可以是：
  - 描述风险或任务要求的纯文本
  - 结构化信息（task_type, risk_description, assignee）
output_format: |
  返回任务详情的 JSON：
  - task_id: 唯一任务标识符
  - status: 任务状态（created/assigned/pending）
  - assigned_to: 员工姓名和 ID
  - feedback_deadline: 任务截止时间戳
  - 确认消息
---

# Task Creator Skill

## Overview

This skill helps managers create verification tasks from risk analysis results and assign them to appropriate staff members for execution.

## Capabilities

### 1. Task Information Confirmation
- Extract task details from user input
- Confirm key information (task type, description, assignee)
- Validate required fields

### 2. Task Creation
- Create new task with proper metadata
- Generate unique task ID
- Set appropriate feedback deadline based on task type:
  - Daily tasks: 24 hours deadline
  - Monthly tasks: 72 hours deadline

### 3. Task Assignment
- Assign task to specified staff member
- Update task status to "已下发"
- Send notification to staff

### 4. Result Reporting
- Return task creation confirmation
- Provide task ID and status
- Include next steps guidance

## When to Use

Use this skill when:
- User explicitly requests task creation ("创建一个任务")
- User wants to assign verification work ("让张三去核查")
- User provides risk data and wants to initiate verification

Do NOT use this skill when:
- User only wants to view tasks (use list_tasks tool)
- User is asking for risk analysis (use risk-analyzer skill)
- User wants staff recommendations (use receiver-recommender skill)

## Process Flow

```
1. Parse User Request
   └── Extract: task_type, risk_description, assignee
   
2. Validate Information
   └── Confirm: assignee exists, risk data valid
   
3. Calculate Deadline
   └── Daily → now + 24h
   └── Monthly → now + 72h
   
4. Create Task
   └── Generate task_id
   └── Set status = "已创建"
   └── Store in data/tasks.csv
   
5. Assign Task
   └── Update assigned_to_id
   └── Update status = "已下发"
   └── Set sent_time = now
   
6. Send Notification
   └── Use notify_new_task MCP tool
   └── Include task details and deadline
   
7. Return Confirmation
   └── JSON with task_id, status, deadline
```

## System Integration

### Tools Used
- `list_users` - Get available staff list
- `create_task` - Create new task record
- `assign_task` - Assign task to staff
- `notify_new_task` - Send task notification via SSE

### Data Storage
- Tasks stored in: `data/tasks.csv`
- Task fields: task_id, status, assigned_to_id, feedback_deadline, etc.

### Role Requirements
- Only available for Manager agents
- Requires Manager role in system

## Error Handling

| Error Scenario | Handling |
|----------------|----------|
| Assignee not found | Return error with available staff list |
| Invalid task type | Default to "daily" type |
| Deadline calculation error | Use default 24h deadline |
| Task creation failure | Return error with reason |

## Example Interaction

### Example 1: Create Task

**User Input:**
```
创建一个任务，让张三去核查这批风险数据
```

**Skill Process:**
1. Extract: assignee = "张三"
2. Confirm assignee exists in user list
3. Create task with type "daily"
4. Set deadline = now + 24h
5. Assign to EMP_003 (张三)
6. Send notification

**Result:**
```json
{
  "success": true,
  "task_id": "TASK_20260326_001",
  "status": "已下发",
  "assigned_to": "张三 (EMP_003)",
  "feedback_deadline": "2026-03-27 18:00:00",
  "message": "任务已创建并下发，通知已发送"
}
```

### Example 2: Assign Existing Task

**User Input:**
```
把这个任务分配给李四处理
```

**Skill Process:**
1. Identify task from context
2. Validate assignee "李四" exists
3. Update task assignment
4. Send notification

## Best Practices

1. **Always confirm before creating** - Show preview to user first
2. **Set appropriate deadline** - Daily=24h, Monthly=72h
3. **Include risk context** - Reference the original risk data
4. **Verify staff availability** - Check user is active staff
5. **Send notifications** - Ensure staff receives task details