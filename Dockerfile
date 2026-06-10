# 高考志愿填报助手 Docker 镜像
FROM python:3.10-slim

WORKDIR /app

# 替换为阿里云 apt 镜像源（国内加速）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（用阿里云 PyPI 镜像加速）
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 复制项目文件
COPY app.py tools.py rag.py crawler.py ./
COPY data/ ./data/

RUN mkdir -p chroma_db chats

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
