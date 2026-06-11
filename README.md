# 🎓 高考志愿填报智能助手

基于 **LangChain Agent + RAG** 的 AI 高考志愿填报咨询系统。5 个工具自动协作，先查数据再开口。

[![Python](https://img.shields.io/badge/Python-3.10-blue)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-1.3-green)](https://langchain.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.58-red)](https://streamlit.io)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek_V4_Pro-orange)](https://platform.deepseek.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)](Dockerfile)

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 📊 **本地分数线** | 48 所重点大学 × 10 省 × 2024+2023 年，13,165 条专业级数据，99% 含位次 |
| 🌐 **实时分数线** | 掌上高考官方 API，覆盖近 3000 所大学、31 省 |
| 📚 **知识库 RAG** | 12 类志愿填报知识，ChromaDB 向量检索 + LLM 生成 |
| 🔍 **联网搜索** | 实时获取招生政策、专业前景、院校动态 |
| 💼 **就业分析** | 查毕业生去向、500 强雇主、行业薪资 |
| 👤 **用户画像** | 填一次省份/分数/选科，回答自动个性化 |
| 💬 **多轮对话** | 自动保存/恢复历史对话 |
| ⚡ **流式交互** | 打字机效果 + 实时步骤提示（分析→查询→回答） |

## 🏗 架构

```
用户 (Streamlit UI)
  │
  ▼
Agent (LangChain create_agent) ── 5 个工具
  │
  ├── query_admission_score  ← 本地 CSV (Pandas, 13,165 条)
  ├── query_live_score       ← 掌上高考 API (3000+ 大学实时)
  ├── query_knowledge_base   ← ChromaDB + BGE Embedding (12 篇知识)
  ├── web_search             ← DDGS 搜索引擎
  └── check_employment       ← DDGS 就业数据
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/xiaotuzhenji/mydemo.git
cd mydemo
```

### 2. 环境配置

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env：
#   DEEPSEEK_API_KEY=你的Key（DeepSeek 对话模型）
#   EMBEDDING_API_KEY=你的Key（硅基流动，免费）
```

> **DeepSeek API**: https://platform.deepseek.com  
> **硅基流动 API**（免费额度）: https://siliconflow.cn

### 3. 构建知识库（首次）

```bash
python crawler.py   # 采集知识文档
python rag.py       # 构建向量库
```

### 4. 启动

```bash
streamlit run app.py
```

浏览器打开 http://localhost:8501

### Docker 部署

```bash
cp .env.example .env  # 编辑填入 API Key
docker compose up -d --build
docker compose exec app python rag.py  # 首次构建知识库
```

## 📁 项目结构

```
mydemo/
├── app.py                # Streamlit 主程序
├── tools.py              # Agent 工具集（5 个工具）
├── rag.py                # RAG 知识库
├── crawler.py            # 知识采集（DDGS 搜索）
├── crawler_score.py      # 分数线采集（掌上高考 API）
├── deploy.sh             # 一键部署脚本
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example          # 环境变量模板
├── .gitignore
├── data/
│   ├── scores_detail.csv # 48 所大学专业级分数线（13,165 条）
│   └── documents/        # 采集的知识文档（12 篇）
├── chroma_db/            # ChromaDB 向量库（自动生成）
└── chats/                # 对话历史（自动生成）
```

## 🛠 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 对话模型 | DeepSeek-V4-Pro | OpenAI 兼容接口 |
| Embedding | 硅基流动 BGE-large-zh-v1.5 | 中文最优，免费额度 |
| Agent 框架 | LangChain 1.3 | create_agent + Tool Calling |
| 向量数据库 | ChromaDB | 轻量持久化 |
| 分数线数据 | 掌上高考公开 API + 本地 CSV | 实时 + 缓存双层 |
| 前端 | Streamlit 1.58 | 纯 Python Web |
| 联网搜索 | DDGS | 免费，无需 Key |
| 部署 | Docker + docker-compose | 一键启动 |

## 📝 License

MIT — 随便用，随便改。

---

*Made with ❤️ for 高考考生和家长*
