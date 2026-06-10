# 🎓 高考志愿填报智能助手

基于 **LangChain Agent + RAG** 的 AI 高考志愿填报咨询系统。支持分数线查询、政策解读、专业分析、就业评估——Agent 自动判断该调哪个工具，先查数据再开口。

![Tech Stack](https://img.shields.io/badge/Python-3.10-blue) ![LangChain](https://img.shields.io/badge/LangChain-1.3-green) ![Streamlit](https://img.shields.io/badge/Streamlit-1.58-red) ![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek_V4_Pro-orange) ![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 📊 **分数线查询** | 181 所大学 × 13 省 × 3 年（2021-2023），5850 条真实数据 |
| 🌐 **联网搜索** | 实时获取最新招生政策、专业前景、院校动态 |
| 📚 **知识库 RAG** | 12 个主题的志愿填报知识，向量检索 + LLM 生成 |
| 💼 **就业分析** | 查毕业生去向、500 强雇主、行业薪资中位数 |
| 👤 **用户画像** | 填一次省份/分数/选科，后续回答自动个性化 |
| 💬 **多轮对话** | 自动保存历史，下次打开接着聊 |
| ⚡ **流式输出** | 打字机效果，不用等全部生成 |

## 🏗 架构

```
用户 (Streamlit UI)
  │
  ▼
Agent (LangChain create_agent)
  │
  ├── query_admission_score  ← 本地 CSV (Pandas)
  ├── web_search             ← DDGS 搜索引擎
  ├── query_knowledge_base   ← ChromaDB + BGE Embedding
  └── check_employment       ← DDGS 就业数据
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/gaokao-assistant.git
cd gaokao-assistant
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek 和硅基流动 API Key
```

> **DeepSeek API**: https://platform.deepseek.com  
> **硅基流动 API**（免费）: https://siliconflow.cn

### 5. 构建知识库（首次运行）

```bash
# 采集志愿填报知识文档
python crawler.py

# 构建 RAG 向量库
python rag.py
```

### 6. 启动应用

```bash
streamlit run app.py
```

浏览器打开 http://localhost:8501

## 📁 项目结构

```
gaokao-assistant/
├── app.py              # Streamlit Web 主程序
├── tools.py            # Agent 工具集（4 个工具）
├── rag.py              # RAG 知识库（Embedding + ChromaDB）
├── crawler.py          # 知识采集器
├── requirements.txt    # Python 依赖
├── .env.example        # 环境变量模板
├── data/
│   ├── scores.csv      # 181 所大学分数线（5850 条）
│   └── documents/      # 采集的知识文档（12 篇）
├── chroma_db/          # ChromaDB 向量库（自动生成）
└── chats/              # 对话历史（自动生成）
```

## 🛠 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 对话模型 | DeepSeek-V4-Pro | OpenAI 兼容接口 |
| Embedding | 硅基流动 BGE-large-zh-v1.5 | 中文最优，免费额度 |
| Agent 框架 | LangChain 1.3 | create_agent + Tool Calling |
| 向量数据库 | ChromaDB | 轻量持久化 |
| 前端 | Streamlit 1.58 | 纯 Python 写 Web |
| 联网搜索 | DDGS | 免费，无需 API Key |
| 数据处理 | Pandas | CSV 查询筛选 |

## 📝 License

MIT — 随便用，随便改。

---

*Made with ❤️ for 高考考生和家长*
