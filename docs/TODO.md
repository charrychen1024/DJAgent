# DJAgent 待解决事项

**更新日期**：2026-03-26
**版本**: v2.4.0-dev
**当前分支**: `feature/dj-ai-report`

---

## 📊 项目整体进度

### 已完成功能 ✅
- ✅ 工号系统统一（使用 employee_id）
- ✅ 风险数据地区过滤
- ✅ 任务权限控制
- ✅ 任务创建和下发基础功能
- ✅ 任务超期自动检测
- ✅ Manager Agent 和 Staff Agent 框架
- ✅ 5个业务 Skill（risk_analyzer, task_creator, receiver_recommender, summary_generator, 核查_guider）
- ✅ 18个 MCP 工具
- ✅ SSE 实时事件推送
- ✅ 任务状态流转规则
- ✅ 动态表单卡片完整功能（Form Card + FormRenderer + 表单提交）
- ✅ 表单数据持久化（历史记录）
- ✅ 文件上传功能（FormData 序列化）
- ✅ 表单按钮状态机（提交/取消按钮交互）

### 部分完成功能 ⚠️
- ⚠️ 反馈总结生成（Skill已定义，执行流程需验证）
- ⚠️ Staff Agent 智能审核（基础框架已建立）
- ⚠️ Manager Agent 智能确认（基础框架已建立）
- ⚠️ 进度督促提醒（超期检测已实现，定时主动提醒需补充）

### 未实现功能 ❌
- ❌ 批量操作功能
- ❌ 数据导出功能
- ❌ 定时任务/调度系统（用于主动提醒）

---

## 🔴 关键待处理问题

### Issue-FE-1: SkillSelector 弹窗定位不稳定
**优先级**: 🔴 **P0 - 用户体验阻塞**
**状态**: 📋 **分析中，反复重现**
**预计工作量**: 2-4小时
**相关文件**: `frontend/src/components/SkillSelector.jsx`, `frontend/src/components/SkillSelector.css`

**问题描述**:
- 点击"使用技能"按钮后，弹窗位置会出现 3 种不同的位置
- 其中只有一个位置是正确的（紧贴按钮下方）
- 每次点击时位置都会变动，用户体验差

**症状**:
```
点击1: ✓ 正确位置（紧贴按钮下方）
点击2: ✗ 位置错误1（偏上）
点击3: ✗ 位置错误2（又偏上）
点击4: ✓ 正确位置
...（重复）
```

**根本原因分析**:
已尝试的方案及存在的问题：

1. **原始方案（已失败）**：
   - 使用 requestAnimationFrame + setTimeout
   - 问题：无法保证一致的位置，存在重排影响

2. **ResizeObserver 方案（已失败）**：
   - 监听 dropdown 高度变化直到稳定
   - 问题：高度持续变化（92px → 236px → 286px → 236px），永远无法满足"两次连续相同"条件

3. **提前保存按钮位置方案（已实施，问题仍存）**：
   - 在 effect 最开始调用 getBoundingClientRect()
   - 在 setTimeout 内仅测量高度
   - 问题：仍然出现三个不同位置

**已验证的事实**：
- 当 top ≈ 688.6 时，位置正确，说明计算逻辑本身没问题
- 问题不在定位计算，而在于**什么时候应用 finalPosition state**

**可能的深层原因**（需进一步调查）:
1. **State 更新时序**：setFinalPosition 可能被多次触发
2. **Dropdown 多次重渲染**：UI 更新导致高度变化，触发多次定位计算
3. **Component 卸载/重挂载**：visible 状态切换导致重新计算
4. **CSS 动画影响**：transition 导致测量时机不同

**已实施的改动**:
- Commit 5049c49a: 初步改进（失败）
- Commit 70499070: 保存按钮位置（问题仍存）

**建议下一步调查**:
1. **添加日志追踪**：在 setFinalPosition 前后添加日志，追踪状态更新次数和顺序
2. **分析重渲染次数**：检查是否 effect 被执行多次
3. **考虑使用 useCallback 缓存函数**：防止依赖项变化导致重复执行
4. **禁用 CSS 动画进行测试**：检查 transition 是否影响测量
5. **使用 MutationObserver**：监听 DOM 变化而非高度变化

**相关 Commit**:
- `5049c49a`: fix: SkillSelector 定位修复 - 使用 requestAnimationFrame 精确测量和定位
- `70499070`: fix: SkillSelector 定位改进 - 保存按钮位置避免重排影响

---

### Issue-1: 任务创建时序问题 - feedback_deadline 设置时机
**优先级**: 🔴 **P0 - 立即处理**
**状态**: 📋 **已分析完整，待实施**
**预计工作量**: 2-3小时

**问题描述**:
- Staff Agent 发送的任务通知消息没有包含截止时间
- 显示 "请尽快完成反馈" 而非具体截止时间

**根本原因分析**:
```
当前流程时序问题：
Manager Agent 创建任务 (status="已创建", feedback_deadline="")
    ↓ (缺少deadline)
MCP 工具调用 notify_new_task()
    ↓ (deadline 仍为空，无法通知截止时间)
最后才调用 assign_task() 和计算 deadline
    ↓ (太晚了！已经发送通知给 Agent 了)
```

**修复方案**:
改变任务创建流程，让 feedback_deadline 在创建时就生成：

```
Step 1: 修改 task_manager.py create_task() 函数
  - 添加自动计算 feedback_deadline 的逻辑
  - 如果 Manager Agent 未指定，根据 task_type（日度/月度）自动计算
  - 日度：deadline = now + 24小时
  - 月度：deadline = now + 72小时

Step 2: 简化 task_manager.py assign_task() 函数
  - 移除所有 deadline 计算逻辑
  - 仅更新 assigned_to_id, assigned_to_name, status
  - 设置 sent_time = 当前时间

Step 3: MCP create_task 工具流程无需改动
  - 保留 assign_task 调用（简化后自动起效）
  - MCP 工具会获取完整的 feedback_deadline 信息
  - notify_new_task() 时已包含截止时间
```

**相关代码位置**:
- `backend/agents/tools/task_manager.py` Line 133-171 (create_task)
- `backend/agents/tools/task_manager.py` Line 341-455 (assign_task)
- `backend/agents/mcp_server.py` Line 100-173 (MCP 工具集成)
- `backend/agents/identity/MANAGER_AGENT.md` Line 111-153 (系统提示词)

**依赖**: 无
**相关Commit**: 无（待实施）

---

### Issue-2: 新增后续问题清单 🔍

#### Issue-2.1: Form Card 中 readonly 字段被锁定 ✅ 已修复
**优先级**: 🟡 P1
**状态**: ✅ **已修复 (Fix 11A & 11B)**

**问题**: 任务编号、运单号等 readonly 字段显示为灰色禁用，无法交互

**修复方案**: 区分 readonly 和 disabled
- readonly 字段使用 HTML `readonly` 属性（可复制，不可编辑）
- 而非 `disabled` 属性（完全禁用）
- 提交时保留字段值

**相关Commit**:
- `c638a0c5`: Fix React key warning in FormRenderer
- `c638a0c5`: Fix 11A & 11B - 修复Form Card消息文本缺失和readonly字段被锁定

**已解决** ✅

---

## 🎯 高优先级待开发任务

### P0-1: 补充反馈总结生成执行流程 ⚠️ 需验证
**优先级**: 🔴 **P0**
**现状**: Skill已定义，但Staff Agent中未调用，需验证与 Issue-1 的兼容性
**预计工作量**: 2-4小时

**需要做**:
1. 等待 Issue-1 完成（确保 feedback_deadline 正确设置）
2. 验证 Staff Agent chat() 中反馈完成的判断逻辑
3. 补充调用 summary_generator skill
4. 更新任务状态为"已完成"

**实现示例**:
```python
# staff_agent.py 中补充逻辑
when user_confirms_completion:
    # 验证反馈是否符合要求
    is_valid = await self.review_feedback(task_id, feedback_data)
    if is_valid:
        # 调用总结 skill
        summary = await self.summary_generator.execute(task_id)
        # 更新任务状态
        update_task_status(task_id, "已完成", feedback_summary=summary)
```

**依赖**:
- Issue-1 完成
- summary_generator Skill
- Staff Agent 框架

**状态**: ⏳ 等待 Issue-1 完成后实施

---

### P0-2: Manager Agent 智能确认逻辑
**优先级**: 🔴 **P0**
**现状**: 基础Agent框架完整，但无确认流程
**预计工作量**: 4-6小时

**需要做**:
1. 任务创建前显示预览给用户
2. 询问用户确认
3. 危险操作始终需要用户确认

**关键操作列表**:
- 创建任务 → 显示预览，询问确认
- 分配任务 → 显示执行人，询问确认
- 删除任务 → 显示危险提示，始终确认
- 发送消息 → 显示内容，询问确认

**任务预览示例**:
```
📋 任务预览

任务内容：运单WLYD001重量异常核查
执行人：EMP_009（赵芳）
地区：上海区
类型：日度

📝 一线人员反馈要求：
1. 核实运单实际重量
2. 提供称重凭证照片
3. 说明异常原因
4. 提交核查报告

是否确认创建？回复"确认"或"取消"
```

**实现示例**:
```python
# manager_agent.py
preview = await self._build_task_preview(task_info)
confirmation = await self.client.query(f"请确认创建此任务:\n{preview}")
if "确认" in confirmation:
    await self._create_task_and_notify(task_info)
```

**依赖**: 无
**相关文件**: `backend/agents/manager_agent.py`

---

### P0-3: Staff Agent 反馈内容智能审核
**优先级**: 🔴 **P0**
**现状**: 框架存在，但无具体审核逻辑
**预计工作量**: 6-8小时

**需要做**:
1. 检查上传文件类型和内容
2. 检查文字说明与任务/风险的相关性
3. 判断是否符合任务要求

**审核规则**:

| 场景 | 审核逻辑 | 行为 |
|------|---------|------|
| 任务要求图片 | 检查是否上传了相关图片 | ✅ 通过 / ❌ 提醒重新上传 |
| 任务要求文字说明 | 检查内容是否与任务相关 | ✅ 通过 / ⚠️ 建议补充 / ❌ 引导重新回复 |
| 上传无关内容 | 检查文件内容 | ❌ 拒收，引导上传正确的文件 |
| 回答不够详细 | 检查是否包含关键信息 | ⚠️ 建议补充 |

**实现示例**:
```python
# staff_agent.py
async def review_feedback(self, task_id, feedback_content, files):
    task = await self.get_task(task_id)
    required_materials = task.get("required_materials", [])

    # 检查上传文件
    for material in required_materials:
        if material["type"] == "image":
            if not files or not any(f.type.startswith("image") for f in files):
                return {"valid": False, "hint": "请上传相关货物照片"}

    # 检查文字相关性
    if feedback_content:
        relevance = await self._check_relevance(feedback_content, task)
        if relevance < 0.5:
            return {"valid": False, "hint": "请提供与任务相关的说明"}

    return {"valid": True}
```

**依赖**: 无
**相关文件**: `backend/agents/staff_agent.py`

---

### P0-4: 任务超时提醒系统（定时任务 + 主动推送）
**优先级**: 🔴 **P0**
**现状**: 超期被动检测已实现，但无主动提醒机制
**预计工作量**: 8-10小时

**关键功能**:
- 后台定时任务（APScheduler，每5分钟检测一次）
- 即将超时预警（提前1-2小时通知）
- 已超时通知（超期后立即通知）
- Manager 手动催促功能
- 通知状态追踪（防止重复发送）

**监测范围**: 同时监测"反馈中"和"已下发"两种状态的任务

**实现步骤**（4阶段）:

**第一阶段：基础设施** (1-2小时)
```
├── 更新 requirements.txt 添加 apscheduler
├── 创建 timeout_config.py - 配置管理
└── 创建 notification_state.py - 通知状态管理
```

**第二阶段：核心服务** (3-4小时)
```
├── 创建 timeout_helpers.py - 时间计算工具
├── 创建 timeout_reminder_service.py - 主服务
└── 修改 sse_events.py - 新事件类型
```

**第三阶段：集成** (2-3小时)
```
├── 修改 session_manager.py - Agent可用性验证
├── 修改 app_fastapi.py - 启动/关闭和API端点
└── 验证日志和异常处理
```

**第四阶段：测试** (1-2小时)
```
├── 创建单元测试
├── 手动集成测试
└── 验证SSE前端显示
```

**新增文件** (5个):
| 文件 | 说明 | 工作量 |
|------|------|-------|
| backend/agents/timeout_config.py | 配置和常量定义 | 0.5h |
| backend/agents/notification_state.py | 通知状态管理器 | 1h |
| backend/agents/timeout_helpers.py | 辅助函数 | 0.5h |
| backend/agents/timeout_reminder_service.py | 核心服务 | 3h |
| backend/agents/tests/test_timeout_reminder.py | 单元测试 | 1.5h |

**修改文件** (4个):
| 文件 | 修改内容 | 工作量 |
|------|---------|-------|
| backend/app_fastapi.py | startup/shutdown事件 + API端点 | 2h |
| backend/agents/sse_events.py | 新事件类型 | 0.5h |
| backend/agents/session_manager.py | 验证Agent可用性 | 0.5h |
| backend/requirements.txt | 添加apscheduler | 0.1h |

**依赖**: APScheduler, StaffAgent, SSE事件系统
**相关文件**: `backend/agents/app_fastapi.py`, `backend/agents/sse_events.py`

---

## 🟡 短期优化任务 (P1)

### P1-1: 进度督促提醒
**优先级**: 🟡 **P1**
**现状**: 超期检测已实现，但无主动提醒
**预计工作量**: 4-6小时

**需要做**:
1. 建立定时任务系统（APScheduler）
2. 在截止时间前发送提醒（提前1-2小时）
3. 超期后发送警告（立即通知）

**实现流程**:
```python
# 添加后台定时任务
scheduler.add_job(check_task_deadlines, 'interval', minutes=5)

async def check_task_deadlines():
    for task in get_pending_tasks():
        time_until_deadline = task.feedback_deadline - now()

        # 提前1小时提醒
        if 0 < time_until_deadline < 1小时:
            await notify_staff_agent(task, "warning")

        # 已超期
        elif time_until_deadline <= 0:
            await notify_staff_agent(task, "overdue")
```

**提醒内容示例**:
```
⚠️ 任务即将超期

任务：运单WLYD001风险核查
执行人：刘伟（EMP_005）
截止时间：2026-03-22 18:00（剩余 1小时）

请尽快完成反馈，逾期将影响个人绩效。
```

**依赖**: APScheduler, SSE事件系统
**相关**: 依赖 P0-4 完成

---

### P1-2: 批量操作功能
**优先级**: 🟡 **P1**
**现状**: 暂未实现
**预计工作量**: 4-6小时

**需要做**:
1. 批量创建任务
2. 批量分配任务
3. 批量更新状态

**API设计示例**:
```python
@app.post("/api/tasks/batch")
async def batch_create_tasks(requests: List[TaskRequest]):
    results = []
    for req in requests:
        task = await create_task(req)
        results.append(task)
    return {"total": len(results), "created": results}

@app.post("/api/tasks/batch/assign")
async def batch_assign_tasks(assignments: List[AssignmentRequest]):
    # 批量分配任务给不同执行人
    pass
```

**依赖**: 无
**相关文件**: `backend/app_fastapi.py`

---

### P1-3: 数据导出功能
**优先级**: 🟡 **P1**
**现状**: 暂未实现
**预计工作量**: 4-6小时

**需要做**:
1. 导出任务列表（CSV/Excel）
2. 导出反馈总结报告
3. 导出风险数据统计

**支持格式**: CSV, Excel (.xlsx), PDF

**API设计**:
```python
@app.get("/api/export/tasks")
async def export_tasks(format: str = "csv"):  # csv, xlsx, pdf
    # 生成导出文件
    pass

@app.get("/api/export/feedback-report")
async def export_feedback_report(task_id: str, format: str = "pdf"):
    # 生成反馈报告
    pass
```

**依赖**: openpyxl (Excel), reportlab (PDF)
**相关文件**: `backend/app_fastapi.py`

---

## 🟢 可选功能优化 (P2)

### P2-1: Manager Agent 多步对话优化
**优先级**: 🟢 **P2**

**需要做**:
- 支持多轮对话收集信息
- 更智能的意图识别
- 更好的错误恢复

---

### P2-2: Staff Agent Skill 自动化增强
**优先级**: 🟢 **P2**

**需要做**:
- 基于任务类型自动选择Skill
- 支持Skill链式调用
- Skill执行结果验证

---

### P2-3: 性能优化
**优先级**: 🟢 **P2**

**需要做**:
- 任务列表分页查询优化
- 风险数据缓存策略
- 代理响应时间优化

---

## 📝 技术债务 & 代码质量

### 需要改进的地方

1. **代码注释完善**
   - [ ] Agent配置部分注释不足
   - [ ] Skill实现缺少业务说明
   - [ ] 工具函数需要补充docstring

2. **错误处理增强**
   - [ ] 任务创建失败的回滚逻辑
   - [ ] Agent对话异常时的降级方案
   - [ ] 文件上传错误提示完善

3. **单元测试补充**
   - [ ] 任务创建流程测试（包含新的 deadline 逻辑）
   - [ ] 状态流转逻辑测试
   - [ ] 权限控制测试
   - [ ] Skill执行测试
   - [ ] 表单提交端到端测试

4. **日志完善**
   - [ ] 任务流转日志
   - [ ] Agent决策日志
   - [ ] 性能指标日志

---

## 📅 里程碑规划

### V2.4.0 (预计 2026-03-31)
**主要目标**: 完成核心反馈流程和 Agent 智能功能

- 🔴 Issue-1 修复：feedback_deadline 时序问题
- 🔴 P0-1: 反馈总结生成执行流程
- 🔴 P0-2: Manager Agent 智能确认逻辑
- 🔴 P0-3: Staff Agent 反馈内容审核
- 🎯 预计完成度: 80%+

### V2.5.0 (预计 2026-04-15)
**主要目标**: 完成超时管理和数据导出

- 🔴 P0-4: 任务超时提醒系统（定时任务）
- 🟡 P1-1: 进度督促提醒
- 🟡 P1-2: 批量操作功能
- 🟡 P1-3: 数据导出功能
- 🎯 预计完成度: 95%+

### V3.0.0 (预计 2026-05-01)
**主要目标**: 完成性能优化和高级功能

- 🟢 P2-1: Manager Agent 多步对话优化
- 🟢 P2-2: Staff Agent Skill 自动化
- 🟢 P2-3: 性能优化
- 📊 数据分析和报表功能
- 🎯 预计完成度: 98%+

---

## 📋 文档更新记录

**2026-03-26** - 根据最新代码进度完整更新
- ✅ 精化了 Issue-1 的分析和修复方案
- ✅ 删除了已完成的功能描述
- ✅ 更新了优先级和工作量估算
- ✅ 完整列出了所有高优先级 P0 任务
- ✅ 清理了过时的 Issue 描述

**2026-03-25** - 初始分析和文档化
- ✅ 分析了 Issue-1 和 Issue-2
- ✅ 制定了修复方案

**版本**: v2.4.0-dev
**状态**: 持续维护中
