# 高考志愿填报助手 Docker 镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（ChromaDB 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY app.py tools.py rag.py crawler.py ./
COPY data/ ./data/

# ChromaDB 和 chats 目录在运行时创建
RUN mkdir -p chroma_db chats

# 暴露 Streamlit 默认端口
EXPOSE 8501

# 启动命令
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
