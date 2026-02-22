#!/bin/bash
# 客户端（Agent）初始化脚本

set -e

echo "🤖 正在初始化 LAN Agent Skills Client..."

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
mkdir -p data/local-skills
mkdir -p data/cache
mkdir -p logs

echo ""
echo "✅ 初始化完成！"
echo ""
echo "使用示例:"
echo ""
echo "  from client.agent import SkillAgent"
echo ""
echo "  agent = SkillAgent("
echo "      server_url='http://server-ip:8080',"
echo "      agent_name='my-agent'"
echo "  )"
echo ""
echo "  # 搜索技能"
echo "  skills = agent.search_skills('数据分析')"
echo ""
echo "  # 上传技能"
echo "  agent.upload_skill("
echo "      name='excel_analyzer',"
echo "      code=skill_code,"
echo "      description='分析 Excel 文件'"
echo "  )"
echo ""