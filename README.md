# 🤖 LAN Agent Skills - Multi-Agent Skill Sharing Platform

A secure and efficient **Local Area Network (LAN) based multi-agent skill sharing and collaboration platform**. This system enables AI agents to discover, share, and synchronize skills within a private network, ensuring complete data privacy and security.

## ✨ Key Features

- 🔒 **Fully Offline**: All data stays within your LAN, no external internet connection required
- 🔄 **Bidirectional Sync**: Agents can both upload new skills and discover/download existing ones
- 🚀 **Real-time Updates**: WebSocket-based push notifications for instant skill updates
- 🧠 **Semantic Search**: Vector-based semantic search supporting natural language queries
- 📦 **Version Control**: Git-based skill versioning with rollback and audit capabilities
- 🐳 **Containerized Deployment**: One-click deployment with Docker Compose

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Local Area Network                        │
│                                                              │
│   ┌──────────────────┐          ┌──────────────────┐        │
│   │     Server       │◄────────►│     Agent 1      │        │
│   │ (Skill Registry) │  Git/Sync│ (Upload/Download) │        │
│   │                  │          │                  │        │
│   │  ┌────────────┐  │◄────────►│     Agent 2      │        │
│   │  │  Git Repo  │  │ WebSocket│   (Consumer)     │        │
│   │  │  (Bare)    │  │  Push    │                  │        │
│   │  └────────────┘  │◄────────►│     Agent N      │        │
│   │  ┌────────────┐  │          │                  │        │
│   │  │  ChromaDB  │  │          └──────────────────┘        │
│   │  │Vector Store│  │                                       │
│   │  └────────────┘  │                                       │
│   └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/elephantrich/lan-agent-skills.git
cd lan-agent-skills

# 2. Start all services
docker-compose up -d

# 3. View logs
docker-compose logs -f
```

### Option 2: Local Python Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server
python server/main.py

# 4. Start agent on another machine
python client/agent.py
```

## 📖 Usage Guide

### 1. Server Configuration

Edit `server/config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8080
  websocket_port: 8765

git:
  repo_path: "/data/skills-repo"
  remote_url: null  # Local repo, no external network

vector_db:
  path: "/data/chromadb"
  collection_name: "skills"

security:
  allowed_hosts: ["192.168.0.0/16", "10.0.0.0/8"]
  require_auth: false  # Disable for LAN environment
```

### 2. Agent Uploading Skills

```python
from client.agent import SkillAgent

agent = SkillAgent(server_url="http://192.168.1.100:8080")

# Upload a new skill
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
    description="Automatically analyze Excel files, returning row count, column names, and statistical summary",
    tags=["excel", "data-analysis", "pandas"]
)
```

### 3. Agent Discovering and Using Skills

```python
# Search for skills
results = agent.search_skills("Excel data analysis")
print(results)
# [{'name': 'excel_analyzer', 'description': '...', 'score': 0.95}]

# Load and use the skill
skill = agent.load_skill("excel_analyzer")
result = skill.analyze_excel("/path/to/data.xlsx")
```

### 4. Real-time Sync (WebSocket)

```python
# Agent automatically receives new skill notifications
@agent.on_skill_update
def handle_new_skill(skill_info):
    print(f"🆕 New skill discovered: {skill_info['name']}")
    print(f"Description: {skill_info['description']}")
    
    # Auto-load
    agent.load_skill(skill_info['name'])

# Keep WebSocket connection
agent.connect_websocket("ws://192.168.1.100:8765")
```

## 🔧 Project Structure

```
lan-agent-skills/
├── 📁 server/                  # Server-side
│   ├── main.py                 # FastAPI main application
│   ├── git_manager.py          # Git repository management
│   ├── vector_store.py         # ChromaDB vector database
│   ├── websocket_server.py     # WebSocket real-time push
│   ├── auth.py                 # Authentication module
│   └── config.yaml             # Configuration file
│
├── 📁 client/                  # Client-side (Agent)
│   ├── agent.py                # Agent SDK main class
│   ├── skill_uploader.py       # Skill upload utility
│   ├── skill_loader.py         # Skill loader
│   ├── websocket_client.py     # WebSocket client
│   └── examples/               # Usage examples
│
├── 📁 shared/                  # Shared modules
│   ├── models.py               # Data models
│   ├── utils.py                # Utility functions
│   └── constants.py            # Constants
│
├── 📁 scripts/                 # Deployment scripts
│   ├── setup_server.sh         # Server initialization
│   ├── setup_client.sh         # Client initialization
│   └── docker/
│       ├── Dockerfile.server
│       ├── Dockerfile.client
│       └── docker-compose.yml
│
├── 📁 tests/                   # Tests
│   ├── test_git_manager.py
│   ├── test_vector_store.py
│   └── test_websocket.py
│
├── README.md                   # This file
├── README.zh.md                # Chinese version
├── requirements.txt            # Python dependencies
└── LICENSE                     # License
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_git_manager.py -v

# With coverage report
pytest --cov=server --cov=client tests/
```

## 🚀 Production Deployment Recommendations

1. **Use Docker Swarm or Kubernetes** for cluster deployment
2. **Configure Nginx reverse proxy** for HTTPS and load balancing
3. **Regular backups** of Git repository and ChromaDB data
4. **Set up monitoring alerts** (Prometheus + Grafana)
5. **Configure firewall rules** to restrict LAN access only

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

## 🤝 Contributing

Welcome to submit Issues and Pull Requests!

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📧 Contact

- Project Homepage: https://github.com/elephantrich/lan-agent-skills
- Issue Feedback: https://github.com/elephantrich/lan-agent-skills/issues

---

**If this project helps you, please give us a ⭐ Star!**