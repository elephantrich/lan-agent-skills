# 🤖 LAN Agent Skills - 局域网 Agent 技能共享系统

一个安全、高效的局域网内 Agent 技能共享与协同工作平台。支持多 Agent 之间的技能发现、同步与调用，数据完全在局域网内流转，确保企业数据安全。

## ✨ 核心特性

- 🔒 **完全离线**：所有数据在局域网内流转，不连接外网
- 🔄 **双向同步**：Agent 可以上传技能，也可以发现/下载新技能
- 🚀 **实时更新**：WebSocket 推送机制，技能更新实时通知
- 🧠 **语义搜索**：基于向量的技能搜索，支持自然语言查询
- 📦 **版本控制**：Git 管理技能版本，支持回滚与审计
- 🐳 **容器化部署**：Docker Compose 一键启动

## 🏗️ 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                         局域网                              │
│                                                             │
│   ┌──────────────────┐          ┌──────────────────┐        │
│   │    服务器         │◄────────►│    Agent 1       │        │
│   │  (技能注册中心)    │  Git/Sync │  (技能上传/下载)  │        │
│   │                  │          │                  │        │
│   │  ┌────────────┐  │◄────────►│    Agent 2       │        │
│   │  │  Git Repo  │  │ WebSocket│  (技能消费者)     │        │
│   │  │  技能仓库   │  │ 实时推送 │                  │        │
│   │  └────────────┘  │◄────────►│    Agent N       │        │
│   │  ┌────────────┐  │          │                  │        │
│   │  │ChromaDB    │  │          └──────────────────┘        │
│   │  │向量数据库  │  │                                     │
│   │  └────────────┘  │                                     │
│   └──────────────────┘                                     │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 方式一：Docker Compose 一键部署（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/lan-agent-skills.git
cd lan-agent-skills

# 2. 启动所有服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f
```

### 方式二：本地 Python 运行

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务器
python server/main.py

# 4. 在另一台机器上启动 Agent
python client/agent.py
```

## 📖 使用指南

### 1. 服务器配置

编辑 `server/config.yaml`：

```yaml
server:
  host: "0.0.0.0"
  port: 8080
  websocket_port: 8765

git:
  repo_path: "/data/skills-repo"
  remote_url: null  # 本地仓库，不连接外网

vector_db:
  path: "/data/chromadb"
  collection_name: "skills"

security:
  allowed_hosts: ["192.168.0.0/16", "10.0.0.0/8"]
  require_auth: false  # 内网环境可关闭
```

### 2. Agent 上传技能

```python
from client.agent import SkillAgent

agent = SkillAgent(server_url="http://192.168.1.100:8080")

# 上传新技能
agent.upload_skill(
    name="excel_analyzer",
    code='''
import pandas as pd

def analyze_excel(file_path):
    df = pd.read_excel(file_path)
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "summary": df.describe()
    }
''',
    description="自动分析Excel文件，返回行数、列名和统计摘要",
    tags=["excel", "data-analysis", "pandas"]
)
```

### 3. Agent 发现并调用技能

```python
# 搜索技能
results = agent.search_skills("分析Excel文件")
print(results)
# [{'name': 'excel_analyzer', 'description': '...', 'score': 0.95}]

# 加载并使用技能
skill = agent.load_skill("excel_analyzer")
result = skill.analyze_excel("/path/to/data.xlsx")
```

### 4. 实时同步（WebSocket）

```python
# Agent 自动接收新技能通知
@agent.on_skill_update
def handle_new_skill(skill_info):
    print(f"🆕 发现新技能: {skill_info['name']}")
    print(f"描述: {skill_info['description']}")
    
    # 自动加载
    agent.load_skill(skill_info['name'])

# 保持 WebSocket 连接
agent.connect_websocket("ws://192.168.1.100:8765")
```

## 🔧 项目结构

```
lan-agent-skills/
├── 📁 server/                  # 服务器端
│   ├── main.py                 # FastAPI 主程序
│   ├── git_manager.py          # Git 仓库管理
│   ├── vector_store.py         # ChromaDB 向量数据库
│   ├── websocket_server.py     # WebSocket 实时推送
│   ├── auth.py                 # 认证模块
│   └── config.yaml             # 配置文件
│
├── 📁 client/                  # 客户端（Agent）
│   ├── agent.py                # Agent SDK 主类
│   ├── skill_uploader.py       # 技能上传工具
│   ├── skill_loader.py         # 技能加载器
│   ├── websocket_client.py     # WebSocket 客户端
│   └── examples/               # 使用示例
│
├── 📁 shared/                  # 共享模块
│   ├── models.py               # 数据模型
│   ├── utils.py                # 工具函数
│   └── constants.py            # 常量定义
│
├── 📁 scripts/                 # 部署脚本
│   ├── setup_server.sh         # 服务器初始化
│   ├── setup_client.sh         # 客户端初始化
│   └── docker/
│       ├── Dockerfile.server
│       ├── Dockerfile.client
│       └── docker-compose.yml
│
├── 📁 tests/                   # 测试
│   ├── test_git_manager.py
│   ├── test_vector_store.py
│   └── test_websocket.py
│
├── README.md                   # 本文件
├── requirements.txt            # Python 依赖
└── LICENSE                     # 开源协议
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_git_manager.py -v

# 带覆盖率报告
pytest --cov=server --cov=client tests/
```

## 🚀 生产环境部署建议

1. **使用 Docker Swarm 或 Kubernetes** 进行集群部署
2. **配置 Nginx 反向代理** 处理 HTTPS 和负载均衡
3. **定期备份 Git 仓库和 ChromaDB** 数据
4. **设置监控告警**（Prometheus + Grafana）
5. **配置防火墙规则** 限制仅局域网访问

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

---

## 📧 联系方式

- 项目主页：https://github.com/YOUR_USERNAME/lan-agent-skills
- 问题反馈：https://github.com/YOUR_USERNAME/lan-agent-skills/issues

---

**如果这个项目对你有帮助，请给我们一个 ⭐ Star！**