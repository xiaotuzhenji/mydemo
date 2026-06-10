#!/bin/bash
# ============================================================
# 高考志愿填报助手 - 一键部署脚本
# 在你的云服务器上运行: bash deploy.sh
# ============================================================
set -e

echo "=========================================="
echo "  高考志愿填报助手 - 部署脚本"
echo "=========================================="

# 1. 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "[1/5] 安装 Docker..."
    curl -fsSL https://get.docker.com | bash
    sudo systemctl enable docker
    sudo systemctl start docker
else
    echo "[1/5] Docker 已安装"
fi

# 2. 克隆项目
echo "[2/5] 拉取项目代码..."
if [ -d "mydemo" ]; then
    cd mydemo && git pull
else
    git clone https://github.com/xiaotuzhenji/mydemo.git
    cd mydemo
fi

# 3. 配置环境变量
echo "[3/5] 配置环境变量..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ">>> 请编辑 .env 文件，填入你的 API Key:"
    echo "    vim .env"
    echo "    （填好后按回车继续）"
    read -p "按回车继续..."
else
    echo ".env 已存在，跳过"
fi

# 4. 构建并启动
echo "[4/5] 构建并启动容器..."
docker compose up -d --build

# 5. 首次构建知识库（需要等容器启动后执行）
echo "[5/5] 等待容器启动..."
sleep 5
echo "构建 RAG 知识库（首次运行需要）..."
docker compose exec -T app python rag.py || echo "知识库可能已存在，跳过"

echo ""
echo "=========================================="
echo "  部署完成！"
echo "  浏览器打开: http://$(curl -s ifconfig.me 2>/dev/null || echo '你的服务器IP'):8501"
echo ""
echo "  查看日志: docker compose logs -f"
echo "  重启服务: docker compose restart"
echo "  停止服务: docker compose down"
echo "=========================================="
