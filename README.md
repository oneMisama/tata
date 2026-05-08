# 🦋 Tata — AI 人格复刻聊天体

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.11+-green" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-purple" alt="license">
  <img src="https://img.shields.io/badge/status-active-success" alt="status">
</p>

<p align="center">
  <b>让 AI 模仿你最想聊天的那个人</b><br>
  上传聊天记录 → 配置人格习惯 → 获得一个会主动给你发消息的「TA」
</p>

---

## 📖 目录

- [项目简介](#-项目简介)
- [核心功能](#-核心功能)
- [使用场景](#-使用场景)
- [技术架构](#-技术架构)
- [快速开始](#-快速开始)
- [API 文档](#-api-文档)
- [商业模式](#-商业模式)
- [项目结构](#-项目结构)
- [路线图](#-路线图)
- [贡献指南](#-贡献指南)
- [免责声明](#-免责声明)
- [许可证](#-许可证)

---

## 🌟 项目简介

**Tata** 是一个基于大语言模型（LLM）的 AI 人格复刻系统。你可以：

1. **上传与某人的聊天记录**（微信、WhatsApp 等）
2. **配置这个人的说话风格、习惯、性格特征**
3. **生成一个高度还原的 AI 数字化身**
4. **与这个化身聊天**——它会用那个人的语气、习惯和情感来回应你
5. **让化身主动给你发消息**——像真人一样主动关心、分享、调侃

> 💡 "Tata" 源自印度语中"再见/回头见"的口语表达，暗示着你与想念的人，通过 AI 重逢。

---

## ✨ 核心功能

### 🎭 人格复刻引擎
| 功能 | 描述 |
|------|------|
| 📤 **聊天记录导入** | 支持微信导出、JSON 格式，自动解析时间/发送者/内容 |
| 🧬 **RAG 向量检索** | 将聊天记录嵌入向量数据库，生成回复时检索最相关的对话片段 |
| 🎯 **Prompt 注入** | 根据人格配置自动构建 System Prompt，严格约束 AI 角色行为 |
| 🎨 **风格微调** | 支持自定义说话风格、惯用词、表情习惯、语气助词等 |
| 📝 **补充说明** | 手动添加日记/性格描述，弥补聊天记录无法体现的信息 |

### 💬 智能对话
| 功能 | 描述 |
|------|------|
| ⚡ **实时对话** | 与 AI 化身实时聊天，秒级响应 |
| 🌊 **流式输出** | 支持 SSE（Server-Sent Events）流式生成 |
| 🧠 **上下文记忆** | 持久化对话历史，化身能记住你们聊过什么 |
| 🔄 **多模型支持** | 兼容 OpenAI、DeepSeek 及任何 OpenAI 兼容 API |

### ⏰ 自主消息
| 功能 | 描述 |
|------|------|
| 📅 **定时消息** | 设置 Cron 表达式，让化身在指定时间主动发消息 |
| 💡 **话题提示** | 指定话题方向（"今晚关心一下"、"分享一件趣事"） |
| 🎲 **随机话题** | 不指定话题时，化身基于人格自主决定说什么 |

### 💳 商业体系
| 层级 | 价格 | 核心权益 |
|------|------|----------|
| 🆓 **Free** | $0/月 | 50 条消息/月，1 个人格 |
| ⭐ **Pro** | $9.99/月 | 2000 条消息/月，5 个人格，定时消息，语音 |
| 🏢 **Enterprise** | $29.99/月 | 无限消息，20 个人格，API 接入，私有部署 |

> 支付集成：**Stripe** (Checkout + Webhook)

---

## 💝 使用场景

| 场景 | 描述 |
|------|------|
| 💌 **暗恋/单相思** | 不好意思直接表白？先和 AI 版的 TA 练习聊天 |
| 🌍 **异地恋** | 对方不在身边时，AI 化身给你一点陪伴感 |
| 💔 **怀念逝者** | 用留下的聊天记录，还原一个可以对话的回忆 |
| 🎭 **角色扮演** | 创建虚拟角色，和自己喜欢的设定聊天 |
| 📚 **语言学习** | 复刻母语者的聊天风格，沉浸式语伴练习 |
| 🔬 **心理学研究** | 研究不同人格配置对对话体验的影响 |

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                │
│            Chat UI │ Persona Config │ Dashboard       │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP/SSE
┌──────────────────────▼──────────────────────────────┐
│                 Backend (FastAPI)                     │
│  ┌──────────┬──────────┬──────────┬──────────────┐  │
│  │   Auth   │ Persona  │   Chat   │   Payment    │  │
│  │  Router  │  Router  │  Router  │   Router     │  │
│  └──────────┴──────────┴──────────┴──────────────┘  │
│  ┌──────────────────────────────────────────────┐    │
│  │            LLM Service (Core Engine)          │    │
│  │  - Prompt Builder (System Prompt Generator)   │    │
│  │  - RAG Retriever (ChromaDB Vector Search)     │    │
│  │  - Model Router (OpenAI / DeepSeek)           │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                   Data Layer                          │
│  ┌──────────┬──────────┬──────────┬──────────────┐  │
│  │  SQLite  │ ChromaDB │  Redis   │   Celery     │  │
│  │  (ORM)   │ (Vector) │ (Cache)  │ (Scheduler)  │  │
│  └──────────┴──────────┴──────────┴──────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| **后端框架** | FastAPI | 高性能异步 Python Web 框架 |
| **ORM** | SQLAlchemy | 数据库操作 |
| **向量数据库** | ChromaDB | 聊天记录语义检索（RAG） |
| **Embedding** | OpenAI text-embedding-3-small | 文本向量化 |
| **LLM** | OpenAI GPT-4o / DeepSeek | 对话生成 |
| **任务队列** | Celery + Redis | 定时消息调度 |
| **支付** | Stripe | 订阅付费 |
| **前端** | Next.js + Tailwind CSS | 用户界面（TODO） |
| **容器化** | Docker Compose | 一键部署 |

### 人格复刻流程

```
1. 用户上传聊天记录
   ↓
2. 解析消息格式 (微信/JSON)
   ↓
3. 存储到 SQLite + 嵌入 ChromaDB
   ↓
4. 用户配置人格参数
   (说话风格、习惯、情绪、补充说明)
   ↓
5. 构建 System Prompt
   (角色设定 + 核心规则 + 风格约束)
   ↓
6. 用户发送消息 → RAG 检索相关聊天片段
   ↓
7. LLM 结合 Prompt + 历史 + 检索结果生成回复
   ↓
8. 化身以该人格风格回复用户
```

---

## 🚀 快速开始

### 前提条件

- Python 3.11+
- Node.js 18+ (前端)
- Redis (定时消息)
- OpenAI API Key / DeepSeek API Key

### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/tata.git
cd tata
```

### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 API Key
```

### 3. Docker 一键启动（推荐）

```bash
docker-compose up -d
```

访问：
- API: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 4. 手动启动

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 前端 (TODO)
cd frontend
npm install && npm run dev
```

### 5. 快速体验

```bash
# 注册
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@tata.app","username":"test","password":"123456"}'

# 登录获取 Token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test&password=123456"

# 创建人格
curl -X POST http://localhost:8000/personas \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "小明",
    "speaking_style": "语气温和、喜欢用省略号...偶尔开点小玩笑",
    "habits": ["喜欢发猫猫表情包", "说到吃的会很兴奋", "深夜会感性"],
    "emotion_range": "温柔,幽默,偶尔emo",
    "custom_prompt": "小明是个程序员，戴眼镜，平时话不多但熟了话很多"
  }'

# 上传聊天记录
curl -X POST http://localhost:8000/personas/1/chat-logs \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@chat_history.txt"

# 聊天！
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"persona_id": 1, "message": "今天加班好累啊..."}'
```

---

## 📡 API 文档

启动服务后访问 `http://localhost:8000/docs` 查看 Swagger UI。

### 主要端点

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/auth/register` | 注册 |
| POST | `/auth/login` | 登录 |
| GET | `/auth/me` | 获取当前用户 |
| POST | `/personas` | 创建人格 |
| GET | `/personas` | 列出人格 |
| GET | `/personas/{id}` | 获取人格详情 |
| POST | `/personas/{id}/chat-logs` | 上传聊天记录 |
| DELETE | `/personas/{id}` | 删除人格 |
| POST | `/chat` | 发送消息 |
| POST | `/chat/stream` | 流式聊天 |
| GET | `/chat/{persona_id}/history` | 对话历史 |
| POST | `/schedules` | 创建定时消息 |
| GET | `/schedules` | 列出定时消息 |
| GET | `/payments/tiers` | 查看套餐 |
| POST | `/payments/checkout` | 创建支付 |
| POST | `/payments/webhook` | Stripe Webhook |

---

## 💰 商业模式

### 收入来源

| 来源 | 占比预估 | 说明 |
|------|----------|------|
| 🎫 **订阅付费** | 70% | Free/Pro/Enterprise 三级订阅 |
| 🔌 **API 接入** | 20% | 企业客户按量计费 API |
| 🏗️ **私有部署** | 10% | 一次性部署费用 + 年度维护 |

### 定价策略

```
Free ($0)       → 体验核心功能，培养用户习惯
Pro ($9.99)     → 主力收入来源，满足深度用户
Enterprise ($29.99) → 专业用户/小团队，高附加值
```

- **Free** 层级提供足够的体验让用户上瘾
- **Pro** 是主力盈利层，边际成本低
- **Enterprise** 针对企业/重度用户

### 成本控制

| 成本项 | 优化策略 |
|--------|----------|
| LLM API | 使用 DeepSeek（$0.14/百万token）作为中文主力模型，比 GPT-4o 便宜 15 倍 |
| 向量存储 | ChromaDB 本地部署，零额外成本 |
| 数据库 | SQLite 单机部署，轻量够用 |
| 消息队列 | Redis 开源免费 |

> 📊 月活 1000 付费用户预估月收入：~$10,000

---

## 📁 项目结构

```
tata/
├── README.md                    # 本文件
├── LICENSE                      # MIT 许可证
├── docker-compose.yml           # Docker 编排
├── .gitignore
├── backend/
│   ├── .env.example             # 环境变量模板
│   ├── requirements.txt         # Python 依赖
│   ├── main.py                  # FastAPI 主应用 + 所有路由
│   ├── config.py                # Pydantic Settings 配置
│   ├── models/
│   │   └── __init__.py          # SQLAlchemy 模型定义
│   └── services/
│       ├── llm_service.py       # LLM 核心引擎（Prompt + RAG）
│       └── payment_service.py   # Stripe 支付服务
├── frontend/                    # 前端（Next.js）— TODO
├── docs/
│   ├── ARCHITECTURE.md
│   └── API.md
└── scripts/
    └── seed_data.py             # 测试数据填充脚本
```

---

## 🗺️ 路线图

### v1.0 ✅ 当前版本
- [x] 用户注册/登录（JWT）
- [x] 人格创建/管理 CRUD
- [x] 聊天记录导入（微信/JSON）
- [x] RAG 向量检索对话
- [x] System Prompt 自动构建
- [x] 实时对话 + 流式输出
- [x] 定时消息（Cron）
- [x] Stripe 订阅支付
- [x] 多 LLM 支持

### v1.1 📋 计划中
- [ ] Next.js 前端 UI（聊天界面 + 人格配置面板）
- [ ] 语音消息（TTS + STT）
- [ ] 表情包/图片回复
- [ ] 化身排行榜/Gallery
- [ ] 更多聊天平台导入（QQ、Telegram、Discord）

### v2.0 🔮 未来
- [ ] 多人格群聊（多个化身同时在一个会话中）
- [ ] 化身自我进化（根据对话反馈自动微调）
- [ ] 情感分析与情绪记忆
- [ ] 移动端 App（iOS/Android）
- [ ] 本地模型支持（Ollama / llama.cpp）
- [ ] 化身 NFT/Marketplace

---

## 🤝 贡献指南

欢迎提交 PR！请遵循以下流程：

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交代码：`git commit -m 'feat: add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 发起 Pull Request

**提交规范**：使用 [Conventional Commits](https://www.conventionalcommits.org/)
- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `refactor:` 重构

---

## ⚠️ 免责声明

**Tata 是一个 AI 模拟工具，请注意以下事项：**

1. 🚫 **不得用于诈骗、冒充真人**进行违法行为
2. 🚫 **不得在未经同意的情况下**使用他人聊天记录训练模型
3. ⚠️ AI 生成的对话**不代表真实人物的观点和意图**
4. ⚠️ 本项目不鼓励替代真实人际关系，AI 只是辅助工具
5. 📜 使用者应遵守所在地区的法律法规

**隐私承诺：**
- 聊天记录仅用于训练用户本人的人格模型
- 数据存储在用户本地或私有服务器
- 不上传、不共享、不用于其他目的

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

```
MIT License

Copyright (c) 2025 Tata Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software...
```

---

<p align="center">
  <b>🦋 Tata — 让想念的人，随时陪在你身边</b><br>
  <sub>Built with ❤️ by the Tata Team</sub>
</p>
