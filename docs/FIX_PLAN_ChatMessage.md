# DJAgent Web端对话消息样式优化修复计划

## 问题描述
- **问题**: Web端对话消息气泡文本间隔太大，内容不紧凑
- **参考**: IM端（盼来移动端/微信风格）的对话消息格式

## 问题分析

### 当前 ChatMessage.css 存在的可能问题
1. **间距过大**:
   - `.chat-message` 有 `gap: 6px`
   - `.message-body` 有 `gap: 4px`
   - 多层嵌套导致视觉间隔过大

2. **换行问题**:
   - CLAUDE.md 中记录了之前的修复经验：`word-break: break-word` 导致字符级别断行
   - 需要使用 `word-wrap: break-word` 代替

3. **容器宽度问题**:
   - 需要确保宽度正确传递，避免 max-width 计算错误

### 参考的 IM 风格特点（微信/移动端风格）
- 消息气泡紧凑，padding 适中
- 文本行高合理，不松散
- 气泡圆角和边框简洁
- 用户消息右对齐，Agent消息左对齐

## 修复方案

### 1. CSS 修复 (ChatMessage.css)

**需要调整的样式**:
- `gap` 值：减小消息间距
- `padding` 值：优化气泡内边距
- `line-height`：调整行高使内容更紧凑
- `word-wrap`：确保正确换行

### 2. 具体修改项

#### 2.1 消息容器间距
```css
/* 当前 */
.chat-message {
  gap: 6px;
}

/* 建议修改为 */
.chat-message {
  gap: 4px;
}
```

#### 2.2 消息体间距
```css
/* 当前 */
.message-body {
  gap: 4px;
}

/* 建议修改为 */
.message-body {
  gap: 2px;
}
```

#### 2.3 气泡内边距
```css
/* 当前 */
.message-text {
  padding: 12px 16px;
}

/* 建议修改为 - 更紧凑 */
.message-text {
  padding: 8px 12px;
}
```

#### 2.4 行高优化
```css
.text-content {
  line-height: 1.5;  /* 可调整到 1.4 或 1.45 */
}

.markdown-content {
  line-height: 1.5;  /* 可调整到 1.4 或 1.45 */
}
```

#### 2.5 确保正确换行（防止字符级别断行）
```css
.message-content {
  word-wrap: break-word;  /* 保持这个，删除 word-break: break-word */
}
```

## 实现步骤

1. **修改 ChatMessage.css**:
   - 调整间距和 padding 值
   - 优化行高
   - 确保换行逻辑正确

2. **测试验证**:
   - 启动前端 `npm run dev`
   - 验证消息显示效果

## 参考资源

- CLAUDE.md 中的 CSS 陷阱记录
- 微信/IM 风格的消息设计
- Anthropic 官方 Claude Agent SDK 规范（保持代码质量）