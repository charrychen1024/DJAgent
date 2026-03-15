# DJAgent UI 优化设计文档

> 更新时间：2026-03-15
> 项目：DJAgent 风控智能体
> 分支：feature/ui-optimization

---

## 一、项目概述

### 1.1 当前设计状态

DJAgent 当前已完成多轮UI优化，整体采用 **现代企业级管理后台 + 微信App风格** 设计。

**已完成优化**：
- 去掉边框，用阴影区分层次
- 加大圆角，增加柔和感
- 按钮悬停效果
- 卡片悬停效果
- 消息气泡优化
- 下拉菜单毛玻璃效果
- 左边栏紧凑化布局
- 初始对话欢迎界面 + 快捷功能卡片
- 个人中心下拉菜单

### 1.2 优化目标

1. **Web端 (Manager)**：打造现代企业级管理后台界面
2. **IM端 (Staff)**：全新手机App风格，微信式聊天体验
3. **整体风格**：遵循 Frontend Design 原则，避免"AI slop"美学

---

## 二、Web端 (Manager) 设计优化方案

### 2.1 整体布局

```
┌──────────────────────────────────────────────────────────────────────┐
│  🛡️ 风控数字员工        [地区▼]                    👤 个人中心     │  ← 顶部导航 (紧凑)
├─────────────┬────────────────────────────────┬──────────────────────┤
│             │                                │                      │
│  🔍 搜索...  │                                │   📋 详情信息       │
│             │   💬 智能体对话                 │   ━                  │
│ [日度][月度] │                                │   任务ID: xxx       │
│             │  ┌──────────────────────────┐  │   风险简述: xxx    │
│ ┌─────────┐ │  │  嗨，王经理 👋           │  │   状态: 已下发     │
│ │高风险:3 │ │  │  专属风控数字员工        │  │   ...              │
│ │中风险:5 │ │  └──────────────────────────┘  │                      │
│ │低风险:2 │ │                                │                      │
│ └─────────┘ │  [📊 今日风险分析]  [🔍 月度分析] │                      │
│             │  [📋 任务统计]    [⚙️ 创建任务]  │                      │
│ 📊 风险明细 │                                │   📎 上传文件       │
│ ┌─────────┐ │  ────────────────────────────  │                      │
│ │ ☐ 运单号│ │                                │                      │
│ │ ☐ 运单号│ │                                │                      │
│ └─────────┘ │                                │                      │
│             │                                │                      │
│ 📋 下发任务 │  ┌──────────────────────────┐  │                      │
│ ┌─────────┐ │  │ 👤 我         10:30    │  │                      │
│ │TASK_001 │ │  │ 消息内容...              │  │                      │
│ │TASK_002 │ │  └──────────────────────────┘  │                      │
│ │TASK_003 │ │                                │                      │
│ └─────────┘ │  ┌──────────────────────────┐  │                      │
│             │  │ 🤖 Agent       10:31    │  │                      │
│             │  │ 消息内容...              │  │                      │
│             │  └──────────────────────────┘  │                      │
│             │  ────────────────────────────  │                      │
│             │  [📎] [输入消息...        ] [➤] │                      │
└─────────────┴────────────────────────────────┴──────────────────────┘
```

### 2.2 顶部导航栏

```css
/* 优化后的顶部导航 */
.App-header {
  height: 48px;  /* 减小高度 */
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
}

.App-header h1 {
  font-size: 16px;
  font-weight: 600;
}
```

### 2.3 左侧栏 - 紧凑布局

```css
/* 左侧栏 - 紧凑化 */
.sidebar.left {
  padding: 12px;
  gap: 12px;
}

/* 全局搜索栏 */
.global-search-bar {
  display: flex;
  gap: 8px;
}

.global-search-bar input {
  flex: 1;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

/* Tab 切换 */
.data-tab-switch {
  display: flex;
  background: #f5f5f5;
  border-radius: 8px;
  padding: 4px;
}

.tab-btn {
  flex: 1;
  padding: 6px 12px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.tab-btn.active {
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* 风险统计看板 */
.risk-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.stat-card {
  padding: 10px;
  border-radius: 10px;
  text-align: center;
}

.stat-card.high {
  background: linear-gradient(135deg, #fff2f0 0%, #fff 100%);
  border: 1px solid #ffccc7;
}

.stat-card.medium {
  background: linear-gradient(135deg, #fffbe6 0%, #fff 100%);
  border: 1px solid #ffe58f;
}

.stat-card.low {
  background: linear-gradient(135deg, #f6ffed 0%, #fff 100%);
  border: 1px solid #b7eb8f;
}
```

### 2.4 任务列表 - 可折叠

```css
.task-list-section.collapsed .task-list-header .collapse-icon {
  transform: rotate(-90deg);
}

.collapse-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: #f5f5f5;
  cursor: pointer;
  transition: all 0.2s;
}

.collapse-btn:hover {
  background: #e8e8e8;
}
```

### 2.5 初始对话欢迎界面

```css
/* 初始对话视图 */
.initial-chat-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  min-height: 100%;
}

.welcome-greeting h2 {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 8px;
}

.welcome-tips {
  margin-top: 16px;
  color: #666;
}

/* 快捷功能卡片 */
.quick-prompts {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 24px;
  width: 100%;
  max-width: 560px;
}

.quick-prompt-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.quick-prompt-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  border-color: #1890ff;
}

.prompt-icon {
  font-size: 24px;
}

.prompt-label {
  font-size: 14px;
  color: #333;
  text-align: left;
}
```

### 2.6 个人中心菜单

```css
.profile-menu {
  position: relative;
}

.profile-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.profile-btn:hover {
  background: #f5f5f5;
}

.profile-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  min-width: 200px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  z-index: 100;
}

.profile-info {
  padding: 16px;
}

.profile-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.profile-detail {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.profile-divider {
  height: 1px;
  background: #f0f0f0;
}

.logout-btn {
  width: 100%;
  padding: 12px;
  border: none;
  background: #fff;
  color: #ff4d4f;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.logout-btn:hover {
  background: #fff1f0;
}
```

### 2.7 右侧栏 - 可折叠

```css
.sidebar.right {
  transition: width 0.3s ease;
}

.sidebar.right.collapsed {
  width: 40px !important;
}

.expand-panel-btn,
.toggle-panel-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: #f5f5f5;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.expand-panel-btn:hover,
.toggle-panel-btn:hover {
  background: #e8e8e8;
}
```

---

## 三、IM端 (Staff) 全新手机端设计

### 3.1 设计理念

**核心目标**：打造纯手机App体验，像微信App一样

- 聊天窗口居中，宽度限制（类似手机屏幕）
- 顶部导航栏：微信风格深色栏
- 底部输入框：胶囊造型
- 消息可滚动，悬浮感

### 3.2 整体布局

```
┌──────────────────────────────────┐
│  ←  风险核查助手           ⋮    │  ← 手机顶部导航 (56px)
├──────────────────────────────────┤
│                                  │
│     🤖 您有新任务待处理          │  ← 可滚动消息区域
│                                  │
│         收到！我来核实一下... 👤  │
│                                  │
│     🤖 请尽快完成反馈            │
│                                  │
├──────────────────────────────────┤
│  📎  ┌─────────────────┐   ➤    │  ← 底部输入区 (60px)
└──────────────────────────────────┘
```

### 3.3 容器样式

```css
/* 手机模拟器容器 */
.phone-container {
  width: 420px;           /* 限制宽度 */
  max-width: 95vw;        /* 响应式 */
  height: 85vh;           /* 不要满屏 */
  margin: 30px auto;      /* 居中 + 顶部留白 */
  border-radius: 28px;    /* 大圆角 */
  box-shadow:
    0 0 0 1px rgba(0, 0, 0, 0.05),
    0 20px 50px rgba(0, 0, 0, 0.2),
    0 0 100px rgba(0, 0, 0, 0.05) inset;
  overflow: hidden;
  background: #fff;
  display: flex;
  flex-direction: column;
}
```

### 3.4 顶部导航栏

```css
/* 导航栏 */
.chat-header.im-header {
  height: 56px;
  background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chat-header.im-header h3 {
  color: white;
  font-size: 17px;
  font-weight: 500;
}

/* 返回按钮 */
.back-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  cursor: pointer;
}

/* 更多按钮 */
.more-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}
```

### 3.5 消息区域

```css
/* 消息容器 */
.chat-messages.im-style {
  flex: 1;
  overflow-y: auto;
  background: #f5f5f5;
  padding: 12px 10px;
  /* 微信风格背景 */
  background-image:
    linear-gradient(rgba(0,0,0,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,0,0,0.03) 1px, transparent 1px);
  background-size: 20px 20px;
}

/* 时间分隔线 */
.time-divider {
  text-align: center;
  margin: 16px 0;
}

.time-divider span {
  background: rgba(0, 0, 0, 0.15);
  color: white;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 11px;
}
```

### 3.6 消息气泡优化

```css
/* 消息气泡基础 */
.chat-messages.im-style .message {
  display: flex;
  flex-direction: column;
  max-width: 78%;
  margin-bottom: 16px;
}

/* 用户消息 */
.chat-messages.im-style .message.user {
  align-self: flex-end;
}

.chat-messages.im-style .message.user .message-bubble {
  background: linear-gradient(135deg, #07c160 0%, #06ad56 100%);
  color: white;
  border-radius: 18px 18px 4px 18px;
  padding: 12px 16px;
  box-shadow: 0 2px 6px rgba(7, 193, 96, 0.3);
  border: none;
}

/* AI消息 */
.chat-messages.im-style .message.agent {
  align-self: flex-start;
}

.chat-messages.im-style .message.agent .message-bubble {
  background: #ffffff;
  color: #1a1a1a;
  border-radius: 18px 18px 18px 4px;
  padding: 12px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: none;
}

/* 头像 */
.message-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

/* 用户头像 */
.chat-messages.im-style .message.user .message-avatar {
  margin-left: 8px;
  background: linear-gradient(135deg, #07c160 0%, #06ad56 100%);
}

/* AI头像 */
.chat-messages.im-style .message.agent .message-avatar {
  margin-right: 8px;
  background: linear-gradient(135deg, #722ed1 0%, #531dab 100%);
}
```

### 3.7 底部输入框

```css
/* 输入区域容器 */
.chat-messages.im-style + .chat-input {
  background: #f8f8f8;
  padding: 10px 12px 14px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

/* 附件按钮 */
.chat-messages.im-style + .chat-input .upload-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f0f0f0;
  border: none;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.chat-messages.im-style + .chat-input .upload-btn:hover {
  background: #e0e0e0;
}

/* 输入框 */
.chat-messages.im-style + .chat-input textarea {
  flex: 1;
  border: none;
  border-radius: 20px;
  padding: 10px 16px;
  background: #fff;
  font-size: 15px;
  line-height: 1.4;
  resize: none;
  outline: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  min-height: 36px;
  max-height: 100px;
}

.chat-messages.im-style + .chat-input textarea:focus {
  box-shadow: 0 1px 5px rgba(24, 144, 255, 0.3);
}

/* 发送按钮 */
.chat-messages.im-style + .chat-input button:not(.upload-btn) {
  width: 50px;
  height: 36px;
  border-radius: 18px;
  background: linear-gradient(135deg, #07c160 0%, #06ad56 100%);
  color: white;
  border: none;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.chat-messages.im-style + .chat-input button:not(.upload-btn):hover {
  transform: scale(1.05);
}

.chat-messages.im-style + .chat-input button:not(.upload-btn):disabled {
  background: #ccc;
  cursor: not-allowed;
}
```

---

## 四、公共组件优化

### 4.1 字体系统

```css
:root {
  /* 字体 */
  --font-display: 'Noto Sans SC', -apple-system, sans-serif;
  --font-body: 'Noto Sans SC', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* 字号层级 */
  --text-xs: 11px;
  --text-sm: 13px;
  --text-base: 15px;
  --text-lg: 17px;
  --text-xl: 20px;
  --text-2xl: 24px;
  --text-3xl: 30px;
}
```

### 4.2 动画效果

```css
/* 消息出现动画 */
@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message {
  animation: messageSlideIn 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 按钮点击波纹效果 */
.btn-ripple {
  position: relative;
  overflow: hidden;
}

.btn-ripple::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%);
  transform: scale(0);
  transition: transform 0.5s;
}

.btn-ripple:active::after {
  transform: scale(2);
}
```

### 4.3 滚动条美化

```css
/* 隐藏滚动条但保持滚动 */
.phone-messages::-webkit-scrollbar {
  width: 0;
}

/* 或者美化滚动条 */
.phone-messages::-webkit-scrollbar {
  width: 4px;
}

.phone-messages::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
}

.phone-messages::-webkit-scrollbar-track {
  background: transparent;
}
```

---

## 五、已完成的优化清单

### 5.1 布局优化
- [x] 移除页面边框
- [x] 减小顶部Header尺寸（48px）
- [x] 三栏布局支持拖拽调整
- [x] 右侧栏可折叠/展开
- [x] 任务区域可折叠
- [x] 左边栏紧凑布局

### 5.2 交互优化
- [x] 按钮悬停效果
- [x] 卡片悬停效果
- [x] 消息出现动画
- [x] 下拉菜单毛玻璃效果
- [x] 个人中心菜单

### 5.3 功能优化
- [x] 全局搜索功能
- [x] 日度/月度数据Tab切换
- [x] 地区筛选功能
- [x] 初始对话欢迎界面
- [x] 快捷功能卡片入口

### 5.4 样式优化
- [x] 去掉边框，用阴影区分层次
- [x] 加大圆角（12-16px）
- [x] 消息气泡优化
- [x] 风险统计看板
- [x] 登录页角色卡片

---

## 六、实施计划

### 6.1 优先级

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P0 | **IM端全新手机样式** | ✅ 已完成 |
| P1 | Web端圆角+阴影优化 | ✅ 已完成 |
| P1 | 消息气泡重新设计 | ✅ 已完成 |
| P2 | 按钮/卡片 hover 效果 | ✅ 已完成 |
| P2 | 下拉菜单毛玻璃效果 | ✅ 已完成 |
| P3 | 字体系统优化 | ✅ 已完成 |

### 6.2 改动范围

**已修改的文件：**
- `frontend/src/App.jsx` - 组件结构调整
- `frontend/src/App.css` - 样式全面优化

**不需要修改的文件：**
- `frontend/src/main.jsx` - 无需改动
- `frontend/index.html` - 无需改动

---

## 七、设计原则

本项目遵循以下 Frontend Design 原则：

1. **大胆的圆角** - 12px-16px，拒绝方正
2. **无边框设计** - 用阴影区分层次
3. **图标优先** - 减少文字提示
4. **流畅动画** - 每个交互都有反馈
5. **层次分明** - 字号、间距有节奏感
6. **紧凑布局** - 高效利用空间

---

## 八、预期效果

### Web端
- 更现代的企业管理后台
- 卡片悬浮感，层次分明
- 交互动画流畅
- 紧凑的左侧栏布局
- 丰富的初始对话体验

### IM端
- 完整的手机App体验
- 居中聊天窗口，像微信App
- 顶部导航 + 底部输入框
- 消息可滚动，悬浮感强
- SSE 实时任务通知

---

*文档结束*
