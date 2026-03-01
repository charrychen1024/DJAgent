# 🛡️ 风控Agent助手系统 (DJAgent)

这是一个大件风控数字员工的DEMO系统，用于风险管控场景。

## 📋 项目概述

基于《风控Agent助手DEMO开发需求文档》开发，实现以下核心功能：
- ✅ 业务负责人的对话式分析和推送指令下达
- ✅ 一线人员的IM模拟端对话和文件反馈
- ✅ 大模型在数据分析、文件验证、反馈总结中的应用
- ✅ 文件系统的数据持久化

## 🏗️ 项目结构

```
DJAgent/
├── backend/                 # Flask后端
│   ├── app.py              # 主应用
│   └── requirements.txt    # 依赖
├── frontend/               # React前端
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js         # 主组件
│   │   ├── App.css        # 样式
│   │   └── index.js       # 入口
│   └── package.json       # 依赖
├── data/                   # 数据文件
│   ├── users.csv          # 用户信息
│   ├── tasks.csv          # 任务列表
│   ├── risk_data_*.csv    # 风险数据
│   └── feedback/          # 反馈数据
├── uploads/               # 上传文件
└── README.md             # 说明文档
```

## 🚀 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端服务

```bash
python app.py
```
后端服务将在 http://localhost:5000 启动

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动前端服务

```bash
npm start
```
前端服务将在 http://localhost:3000 启动

## 📊 功能说明

### 业务负责人工作区 (Web端)

- **左栏**: 用户列表 + 任务列表
- **中栏**: 智能体对话框
- **右栏**: 辅助信息展示区

### 一线人员工作区 (IM端)

- 类似微信的单栏聊天界面
- 接收任务推送和风险数据
- 通过对话完成任务反馈

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 |
| 后端 | Flask |
| 数据存储 | CSV文件 |
| API风格 | RESTful |

## 📝 API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/users | GET | 获取用户列表 |
| /api/users/:id | GET | 获取单个用户 |
| /api/tasks | GET | 获取任务列表 |
| /api/tasks | POST | 创建任务 |
| /api/tasks/:id/status | PUT | 更新任务状态 |
| /api/feedback/:task_id | GET | 获取任务反馈 |
| /api/chat | POST | AI对话 |

## 🔧 开发说明

- 当前为DEMO版本，部分功能简化实现
- 数据持久化使用CSV文件，便于演示
- 生产环境建议替换为数据库存储

## 📄 分支信息

- `main`: 主分支
- `dev`: 开发分支（当前）

---

开发者：小晨 🦊
