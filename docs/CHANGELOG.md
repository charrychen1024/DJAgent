# DJAgent 更新日志

所有重要改动都会记录在此文件中。

格式参考 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)

---

## [未发布]

### 计划中 (V2.4.0)
- 反馈总结生成完整实现
- Manager Agent 智能确认逻辑
- Staff Agent 反馈内容智能审核

---

## [2.3.0] - 2026-03-23

### 新增
- 任务状态流转完整实现（已创建 → 已下发 → 反馈中 → 已完成/已超时）
- 自动超期检测（在 get_tasks API 中）
- 反馈总结 Skill 定义（summary_generator）
- Staff Agent 反馈督促和结束确认流程
- 任务反馈截止时间规则（日度24h，月度72h）
- 工号系统统一（使用 employee_id）
- 数据权限控制（按 region 字段过滤）

### 改进
- 更新任务数据模型，新增 sent_time、feedback_deadline、feedback_summary 字段
- 优化 Manager Agent 系统提示词
- 优化 Staff Agent 系统提示词
- 改进权限检查逻辑，三层权限控制（身份 → 角色 → 所有权）

### 修复
- 移除 unified_agent.py 中的重复 return 代码（第130-133行）
- 修复任务权限过滤逻辑

### 文档
- 补充 PRD.md 实现状态矩阵
- 补充 ARCHITECTURE_REFACTOR.md 深度实现分析（+240行）
- 更新 README.md 工号系统说明
- 更新 TODO.md 开发进度

---

## [2.2.0] - 2026-03-15

### 新增
- 月度数据 Tab 视图（data/risk_data_monthly_*.csv）
- 全局搜索功能（前端实现）
- 初始对话欢迎界面和功能卡片
- 个人中心菜单（用户切换、退出）
- 任务区域折叠功能

### 改进
- 左侧栏紧凑化设计
- 右侧栏可折叠/展开
- 顶部 Header 尺寸优化
- 移除页面边框

### 数据模型
- 风险数据新增 region 字段
- 任务新增 task_type 字段（日度/月度）

---

## [2.1.0] - 2026-03-01

### 新增
- 地区归属功能（总部、上海区、北京区、山西区、浙北区）
- 地区数据过滤（按用户 region）
- 总部管理员全数据查看权限

### 改进
- 任务权限控制优化
- 风险数据查询性能

### 数据模型
- users.csv 新增 region 和 employee_id 字段
- risk_data_*.csv 新增 region 字段

---

## [2.0.0] - 2026-02-15

### 新增
- UnifiedAgent 配置驱动设计（替代 Manager/Staff 双类）
- Agent 会话管理（SessionManager）
- 18 个 MCP 工具
- 6 个业务 Skill（risk_analyzer, task_creator, receiver_recommender, summary_generator, 核查_guider, hello_world）
- Skill 自动加载机制
- SSE 实时事件推送
- 文件上传和解析（CSV, Excel, PDF, Word）
- 任务创建、分配、查询、更新
- 反馈管理（data/feedback/{task_id}.json）

### 架构改进
- **从**：Manager/Staff 两个独立的 Agent 类
- **到**：配置驱动的 UnifiedAgent，通过 AgentConfig 实现不同模式

- **从**：手动 XML 解析工具调用
- **到**：SDK 自动处理 Tool Calling 和 ReAct 循环

- **从**：预设的工作流（分析→推荐→创建）
- **到**：自由的 ReAct 规划，用户随时提出新需求

### API 端点
- POST /api/chat - Agent 对话
- GET /api/users - 用户列表
- GET /api/tasks - 任务列表（带权限过滤）
- POST /api/tasks - 创建任务
- GET /api/tasks/{task_id} - 任务详情
- PUT /api/tasks/{task_id} - 更新任务
- POST /api/tasks/{task_id}/message - 任务对话
- GET /api/risk-data - 风险数据
- POST /api/upload - 文件上传
- GET /api/events/{user_id} - SSE 实时事件

### 数据模型
- users.csv: user_id, username, role, department
- tasks.csv: task_id, creator_id, assigned_to_id, status, ...
- risk_data_*.csv: 运单号, 发货地, 异常类型, 风险等级, ...
- feedback/{task_id}.json: 聊天历史, 上传文件, 反馈总结

---

## [1.1.0] - 2026-01-20

### 新增
- 基础 Manager Agent 实现
- 基础 Staff Agent 实现
- 任务列表和详情页面
- 风险数据展示（日度数据）
- 聊天界面

### 已知问题
- 权限控制不完善
- 没有反馈总结生成
- 没有超期检测

---

## [1.0.0] - 2026-01-01

### 初始发布
- 前端 React 界面（三栏布局）
- 后端 FastAPI 基础框架
- 用户登录和角色选择
- 风险数据展示
- 基础任务管理
- 文件上传接口

---

## 版本对比

### 功能完成度演进

| 功能 | v1.0 | v1.1 | v2.0 | v2.1 | v2.2 | v2.3 |
|------|------|------|------|------|------|------|
| 用户登录 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 风险数据展示 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 月度数据 Tab | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 任务创建/分配 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 权限控制 | ❌ | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| 地区过滤 | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| 全局搜索 | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 超期检测 | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 反馈总结 | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ |

### 架构演进

| 方面 | v1.x | v2.0+ |
|------|------|-------|
| Agent | Manager/Staff 双类 | 配置驱动统一设计 |
| 工具调用 | 手动 XML 解析 | SDK 自动处理 |
| 工作流 | 预设流程 | ReAct 自主规划 |
| 权限控制 | 基础 | 三层完整设计 |
| 工具数量 | ~10 | 18 |
| Skill 数量 | 2 | 6 |

---

## 破坏性改动

### v2.0.0
- **Agent 类变更**：Manager/Staff 两个独立类 → 统一 UnifiedAgent 类
  - **迁移指南**：更新 SessionManager 中的 Agent 初始化代码

- **系统提示词变更**：之前的 Manager/Staff 系统提示被合并到 AgentConfig
  - **迁移指南**：通过 config.system_prompt 设置自定义提示词

- **工具名称格式**：MCP 工具需要 `mcp__server__tool` 前缀
  - **迁移指南**：在 allowed_tools 中添加 `mcp__` 前缀

---

## 未来计划

### V2.4.0 (2026-03-31)
- [ ] 反馈总结生成完整实现（调用 summary_generator Skill）
- [ ] Manager Agent 智能确认逻辑（创建前显示预览）
- [ ] Staff Agent 反馈内容智能审核（检查文件和文字）
- [ ] 预期完成度：90%+

### V2.5.0 (2026-04-15)
- [ ] 进度督促提醒（定时任务 + 超期提醒）
- [ ] 批量操作功能（批量创建、分配、更新）
- [ ] 数据导出功能（CSV/Excel/PDF）
- [ ] 预期完成度：95%+

### V3.0.0 (2026-05-01)
- [ ] 性能优化（缓存、索引、连接池）
- [ ] 高级分析功能（趋势分析、预测）
- [ ] 移动端完整适配
- [ ] 预期完成度：98%+

---

## 贡献指南

### 报告问题
- 使用 GitHub Issues 报告 bug
- 包含重现步骤、期望行为、实际行为
- 附加相关日志或截图

### 提交改进
1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交改动 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

### 代码规范
- Python: PEP 8
- JavaScript: ESLint 配置
- 提交消息：简洁清晰，英文或中文

---

## 许可证

MIT License

---

**更新日期**: 2026-03-23
**维护者**: DJAgent Team
