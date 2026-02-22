#!/bin/bash
# 服务器初始化脚本

set -e

echo "🚀 正在初始化 LAN Agent Skills Server..."

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "📦 Python 版本: $python_version"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "📦 安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 创建必要目录
echo "📁 创建目录结构..."
mkdir -p data/skills-repo
mkdir -p data/chromadb
mkdir -p logs
mkdir -p uploads

# 初始化 Git 仓库（如果不是 bare 模式）
if [ ! -d "data/skills-repo/.git" ] && [ ! -d "data/skills-repo/objects" ]; then
    echo "📦 初始化 Git 仓库..."
    cd data/skills-repo
    git init --bare
    cd ../..
fi

echo ""
echo "✅ 初始化完成！"
echo ""
echo "启动服务器:"
echo "  python server/main.py"
echo ""
echo "或使用 uvicorn:"
echo "  uvicorn server.main:app --host 0.0.0.0 --port 8080"
echo ""