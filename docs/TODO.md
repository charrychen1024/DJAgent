# DJAgent 待解决事项

**更新日期**：2026-03-19

---

## 问题1：Staff端新任务切换失败 ❌

**现象**：
- Manager给一线人员创建了新任务
- SSE收到`new_task`事件
- 但页面没有切换到新任务，聊天记录还是写在旧任务里

**可能原因**：
- `tasks.find()` 在SSE回调时可能找不到新任务（tasks状态未更新）
- 需要在setSelectedTask之前先刷新tasks列表

**待排查**

---

## 问题2：Web端对话消息样式不紧凑 ❌

**现象**：
- Web端对话消息气泡文本间隔太大
- 内容不紧凑

**解决方案**：
- 调整Web端样式参数：
  - `.message` padding: 10px 14px → 6px 10px
  - `.message` margin-bottom: 6px → 4px
  - `.message-header` margin-bottom: 4px → 2px

---

## 问题3：Web端新建对话没有完全重新开始 ❌ (已修复 ✅)

**现象**：
- 新建对话后，智能体还能读到历史记录

**根因**：
- `session_manager` 按 `user_id` 存储 Agent 会话，不是按 `chat_id`
- 同一个用户的所有对话共享同一个 Agent 实例

**解决方案**：
- 创建新对话时，调用 cleanup 接口关闭旧的 Agent 会话
- 这样新对话就会有全新的上下文

**修改文件**：
- `frontend/src/App.jsx` - handleNewChat 函数中先调用 cleanup

---

## 待讨论

1. Staff端切换问题的根因需要进一步排查
2. 新建对话的上下文隔离问题
