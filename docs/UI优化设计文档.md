# DJAgent UI 优化设计文档

> 更新时间：2026-03-14
> 项目：DJAgent 风控智能体
> 分支：feature/ui-optimization

---

## 一、项目概述

### 1.1 当前设计状态

DJAgent 当前采用 **微信/企业微信风格** 设计，整体偏传统，存在以下共性问题：

- 线条过于生硬（大量 1px 边框线）
- 圆角偏小（4-8px），视觉效果方正
- 缺少微交互和动画效果
- 字体单调，缺乏层次感

### 1.2 优化目标

1. **Web端 (Manager)**：打造现代企业级管理后台界面
2. **IM端 (Staff)**：全新手机App风格，微信式聊天体验
3. **整体风格**：遵循 Frontend Design 原则，避免"AI slop"美学

---

## 二、Web端 (Manager) 设计优化方案

### 2.1 当前问题

| 问题 | 现状 |
|------|------|
| 边框 | 大量 `1px solid #e8e8e8` 边框，卡片像表格 |
| 圆角 | `--radius-sm: 4px`，`--radius-md: 8px` 过于方正 |
| 阴影 | 仅基础阴影，层次感不足 |
| 动画 | 几乎没有交互动画 |

### 2.2 优化方向

#### 2.2.1 去掉边框，用阴影区分层次

```css
/* 改前 */
.card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);  /* 8px */
}

/* 改后 */
.card {
  border: none;
  border-radius: var(--radius-lg);  /* 16px */
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}
```

#### 2.2.2 加大圆角，增加柔和感

```css
:root {
  /* 圆角层级 */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;
}
```

#### 2.2.3 按钮悬停效果

```css
.btn-primary {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(24, 144, 255, 0.4);
}

.btn-primary:active {
  transform: translateY(0);
}
```

#### 2.2.4 卡片悬停效果

```css
.role-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.role-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
}
```

### 2.3 消息气泡优化

```css
/* 用户消息 - 渐变+阴影 */
.message-user {
  background: linear-gradient(135deg, #07c160 0%, #06ad56 100%);
  border-radius: 18px 18px 4px 18px;
  box-shadow: 0 2px 8px rgba(7, 193, 96, 0.25);
}

/* AI消息 - 白色+淡阴影 */
.message-ai {
  background: #ffffff;
  border-radius: 18px 18px 18px 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}
```

### 2.4 下拉菜单毛玻璃效果

```css
.profile-dropdown {
  backdrop-filter: blur(12px);
  background: rgba(255, 255, 255, 0.88);
  animation: dropdownFade 0.2s ease;
}

@keyframes dropdownFade {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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

/* 状态栏模拟 */
.phone-status-bar {
  height: 44px;
  background: linear-gradient(180deg, #1a1a1a 0%, #2d2d2d 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  color: white;
  font-size: 12px;
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
  border-radius: 50%;  /* 圆形头像 */
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

## 五、实施计划

### 5.1 优先级

| 优先级 | 任务 | 预计改动量 |
|--------|------|-----------|
| P0 | **IM端全新手机样式** | StaffWorkspace 组件 + CSS |
| P1 | Web端圆角+阴影优化 | App.css 变量 + 组件样式 |
| P1 | 消息气泡重新设计 | Web + IM 通用 |
| P2 | 按钮/卡片 hover 效果 | App.css |
| P2 | 下拉菜单毛玻璃效果 | App.css |
| P3 | 字体系统优化 | CSS 变量 |

### 5.2 改动范围

**需要修改的文件：**
- `frontend/src/App.jsx` - 组件结构调整（IM端）
- `frontend/src/App.css` - 样式全面优化

**不需要修改的文件：**
- `frontend/src/main.jsx` - 无需改动
- `frontend/index.html` - 无需改动

---

## 六、设计原则

本项目遵循以下 Frontend Design 原则：

1. **大胆的圆角** - 16px-24px，拒绝方正
2. **无边框设计** - 用阴影区分层次
3. **图标优先** - 减少文字提示
4. **流畅动画** - 每个交互都有反馈
5. **层次分明** - 字号、间距有节奏感

---

## 七、预期效果

### Web端
- 更现代的企业管理后台
- 卡片悬浮感，层次分明
- 交互动画流畅

### IM端
- 完整的手机App体验
- 居中聊天窗口，像微信App
- 顶部导航 + 底部输入框
- 消息可滚动，悬浮感强

---

*文档结束*
