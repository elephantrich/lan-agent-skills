#!/usr/bin/env python3
"""
LAN Agent Skills Server
FastAPI 主服务
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
import uvicorn
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from contextlib import asynccontextmanager

from shared.models import (
    SkillCreateRequest, SkillUpdateRequest, SkillSearchRequest,
    SkillSearchResponse, SyncRequest, SyncResponse, HealthCheck
)

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO",
    colorize=True
)
logger.add(
    "logs/server.log",
    rotation="00:00",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)

# 加载配置
def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent / "config.yaml"
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    # 默认配置
    return {
        "server": {"host": "0.0.0.0", "port": 8080, "api_prefix": "/api/v1"},
        "git": {"repo_path": "./data/skills-repo", "bare_mode": True},
        "vector_db": {"path": "./data/chromadb", "collection_name": "skills"},
        "security": {"allowed_hosts": ["192.168.0.0/16", "10.0.0.0/8"], "require_auth": False},
        "logging": {"level": "INFO"}
    }

config = load_config()

# 全局变量（将在 lifespan 中初始化）
git_manager = None
vector_store = None

# 应用生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global git_manager, vector_store
    
    # 启动时初始化
    logger.info("🚀 正在初始化服务器...")
    
    try:
        # 导入并初始化 Git 管理器
        from server.git_manager import GitManager
        git_config = config.get("git", {})
        git_manager = GitManager(
            repo_path=git_config.get("repo_path", "./data/skills-repo"),
            bare_mode=git_config.get("bare_mode", True)
        )
        git_manager.initialize()
        logger.info("✅ Git 管理器初始化完成")
        
        # 导入并初始化向量存储
        from server.vector_store import VectorStore
        vector_config = config.get("vector_db", {})
        vector_store = VectorStore(
            persist_directory=vector_config.get("path", "./data/chromadb"),
            collection_name=vector_config.get("collection_name", "skills"),
            embedding_model=vector_config.get("embedding_model", "all-MiniLM-L6-v2")
        )
        logger.info("✅ 向量数据库初始化完成")
        
        # 如果向量库为空，尝试从 Git 仓库重建索引
        if vector_store.collection.count() == 0:
            logger.info("🔄 正在从 Git 仓库重建索引...")
            await rebuild_index()
        
        logger.info("✨ 服务器初始化完成！")
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        raise
    
    yield
    
    # 关闭时清理
    logger.info("🛑 正在关闭服务器...")
    if vector_store:
        vector_store.persist()
        logger.info("✅ 数据已持久化")
    logger.info("👋 再见！")


async def rebuild_index():
    """从 Git 仓库重建向量索引"""
    from shared.utils import generate_skill_id
    from shared.models import Skill, SkillMetadata, SkillStatus
    
    if not git_manager or git_manager.bare_mode:
        return
    
    skills_dir = git_manager.repo_path / "skills"
    metadata_dir = git_manager.repo_path / "metadata"
    
    if not skills_dir.exists():
        return
    
    count = 0
    for skill_file in skills_dir.glob("*.py"):
        try:
            # 读取代码
            code = skill_file.read_text(encoding='utf-8')
            
            # 读取元数据
            meta_file = metadata_dir / f"{skill_file.stem}.json"
            if meta_file.exists():
                import json
                meta_dict = json.loads(meta_file.read_text(encoding='utf-8'))
                metadata = SkillMetadata(**meta_dict)
            else:
                metadata = SkillMetadata(
                    name=skill_file.stem,
                    description="",
                    author="unknown"
                )
            
            # 创建技能对象
            skill = Skill(
                id=generate_skill_id(metadata.name, metadata.author),
                metadata=metadata,
                status=SkillStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # 添加到向量数据库
            vector_store.add_skill(skill, code)
            count += 1
            
        except Exception as e:
            logger.warning(f"索引技能 {skill_file} 失败: {e}")
    
    logger.info(f"✅ 索引重建完成，共 {count} 个技能")


# 创建 FastAPI 应用
app = FastAPI(
    title="LAN Agent Skills Server",
    description="局域网 Agent 技能共享服务器",
    version="1.0.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为局域网
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 健康检查端点
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """健康检查端点"""
    import psutil
    import time
    
    # 获取启动时间
    boot_time = psutil.boot_time()
    uptime = time.time() - boot_time
    
    return HealthCheck(
        status="healthy",
        version="1.0.0",
        uptime=uptime,
        connected_agents=0,  # TODO: 实现 Agent 连接计数
        total_skills=vector_store.collection.count() if vector_store else 0
    )


# API 路由
api_prefix = config.get("server", {}).get("api_prefix", "/api/v1")

@app.get(f"{api_prefix}/skills", response_model=List[Dict[str, Any]])
async def list_skills(
    tag: Optional[str] = Query(None, description="按标签过滤"),
    author: Optional[str] = Query(None, description="按作者过滤"),
    status: Optional[str] = Query("active", description="按状态过滤")
):
    """列出所有技能"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="向量数据库未初始化")
    
    skills = vector_store.get_all_skills()
    
    # 应用过滤
    if tag:
        skills = [s for s in skills if tag in s.get("tags", [])]
    if author:
        skills = [s for s in skills if s.get("author") == author]
    if status:
        skills = [s for s in skills if s.get("status") == status]
    
    return skills


@app.get(f"{api_prefix}/skills/{{skill_id}}")
async def get_skill(skill_id: str):
    """获取单个技能详情"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="向量数据库未初始化")
    
    skill = vector_store.get_skill_by_id(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    return skill


@app.post(f"{api_prefix}/skills/search", response_model=List[Dict[str, Any]])
async def search_skills(request: SkillSearchRequest):
    """搜索技能"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="向量数据库未初始化")
    
    results = vector_store.search_skills(
        query=request.query,
        top_k=request.top_k,
        tags=request.tags,
        author=request.author,
        status=request.status
    )
    
    return results


@app.post(f"{api_prefix}/skills")
async def create_skill(request: SkillCreateRequest):
    """创建新技能"""
    if not vector_store or not git_manager:
        raise HTTPException(status_code=503, detail="服务未完全初始化")
    
    from shared.utils import generate_skill_id
    from datetime import datetime
    
    # 生成技能 ID
    skill_id = generate_skill_id(request.metadata.name, request.metadata.author)
    
    # 创建技能对象
    skill = Skill(
        id=skill_id,
        metadata=request.metadata,
        status=SkillStatus.ACTIVE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by=request.metadata.author
    )
    
    # 添加到向量数据库
    vector_store.add_skill(skill, request.code)
    
    # 添加到 Git 仓库（如果不是 bare 模式）
    if not git_manager.bare_mode:
        try:
            git_manager.add_skill(skill, request.code)
        except Exception as e:
            logger.warning(f"添加到 Git 失败: {e}")
    
    return {
        "id": skill_id,
        "name": request.metadata.name,
        "message": "技能创建成功"
    }


@app.delete(f"{api_prefix}/skills/{{skill_id}}")
async def delete_skill(skill_id: str):
    """删除技能"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="向量数据库未初始化")
    
    success = vector_store.delete_skill(skill_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")
    
    return {"message": "技能删除成功", "skill_id": skill_id}


@app.post(f"{api_prefix}/sync")
async def sync_skills(request: SyncRequest):
    """同步技能"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="向量数据库未初始化")
    
    # TODO: 实现增量同步逻辑
    all_skills = vector_store.get_all_skills()
    
    return SyncResponse(
        new_skills=[],
        updated_skills=[],
        deleted_skills=[]
    )


# 入口函数
def main():
    """启动服务器"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LAN Agent Skills Server")
    parser.add_argument("--host", default="0.0.0.0", help="主机地址")
    parser.add_argument("--port", type=int, default=8080, help="端口号")
    parser.add_argument("--reload", action="store_true", help="开发模式热重载")
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════╗
║     🤖 LAN Agent Skills Server                   ║
╠══════════════════════════════════════════════════╣
║  文档: http://{args.host}:{args.port}/docs             ║
║  API:  http://{args.host}:{args.port}{api_prefix}           ║
╚══════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "server.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=None  # 使用 loguru
    )


if __name__ == "__main__":
    main()