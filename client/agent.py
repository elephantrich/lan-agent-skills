#!/usr/bin/env python3
"""
LAN Agent Skills Client
Agent SDK 主类
"""
import os
import sys
import json
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

import httpx
import websockets
from websockets.exceptions import ConnectionClosed

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.models import (
    Skill, SkillMetadata, SkillCreateRequest,
    SkillSearchRequest, SyncRequest, WebSocketMessage
)
from shared.utils import generate_skill_id, validate_skill_code


class SkillAgent:
    """
    Agent SDK 主类
    用于与 Skills Server 交互
    """
    
    def __init__(
        self,
        server_url: str = "http://localhost:8080",
        agent_id: Optional[str] = None,
        agent_name: str = "unnamed-agent",
        api_key: Optional[str] = None
    ):
        """
        初始化 Agent
        
        Args:
            server_url: 服务器 URL
            agent_id: Agent 唯一标识（可选，自动生成）
            agent_name: Agent 名称
            api_key: API 密钥（如果需要认证）
        """
        self.server_url = server_url.rstrip('/')
        self.agent_id = agent_id or self._generate_agent_id()
        self.agent_name = agent_name
        self.api_key = api_key
        
        # 客户端配置
        self.timeout = 30.0
        self.max_retries = 3
        
        # WebSocket
        self.ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        self.ws_connection = None
        self.ws_running = False
        self._ws_handlers: Dict[str, List[Callable]] = {}
        
        # 本地缓存
        self._skills_cache: Dict[str, Dict] = {}
        self._last_sync: Optional[datetime] = None
        
        # 创建 HTTP 客户端
        self._client = httpx.Client(
            timeout=self.timeout,
            headers=self._get_headers()
        )
        
        print(f"🤖 Agent 初始化完成: {self.agent_name} ({self.agent_id[:8]})")
        print(f"   服务器: {self.server_url}")
    
    def _generate_agent_id(self) -> str:
        """生成 Agent ID"""
        import uuid
        import hashlib
        import socket
        
        # 基于机器信息和随机数生成
        hostname = socket.gethostname()
        random_part = uuid.uuid4().hex[:8]
        content = f"{hostname}:{random_part}:{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "X-Agent-ID": self.agent_id,
            "X-Agent-Name": self.agent_name
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法
            path: API 路径
            **kwargs: 其他参数
            
        Returns:
            响应数据
        """
        url = f"{self.server_url}{path}"
        
        for attempt in range(self.max_retries):
            try:
                response = self._client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise Exception(f"资源不存在: {path}")
                elif e.response.status_code == 409:
                    raise Exception(f"资源已存在: {path}")
                else:
                    raise Exception(f"HTTP 错误 {e.response.status_code}: {e.response.text}")
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise Exception(f"请求失败 ({self.max_retries} 次尝试): {e}")
                time.sleep(1)
    
    # ==================== 技能管理 API ====================
    
    def upload_skill(
        self,
        name: str,
        code: str,
        description: str = "",
        author: str = "",
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        version: str = "1.0.0"
    ) -> Dict[str, Any]:
        """
        上传新技能
        
        Args:
            name: 技能名称
            code: 技能代码
            description: 描述
            author: 作者
            tags: 标签
            dependencies: 依赖项
            version: 版本
            
        Returns:
            创建结果
        """
        # 验证代码
        valid, error = validate_skill_code(code)
        if not valid:
            raise ValueError(f"代码验证失败: {error}")
        
        # 构建请求
        metadata = SkillMetadata(
            name=name,
            version=version,
            description=description,
            author=author or self.agent_name,
            tags=tags or [],
            dependencies=dependencies or []
        )
        
        request = SkillCreateRequest(
            metadata=metadata,
            code=code
        )
        
        # 发送请求
        result = self._request(
            "POST",
            "/api/v1/skills",
            json=request.model_dump()
        )
        
        print(f"✅ 技能上传成功: {name}")
        return result
    
    def search_skills(
        self,
        query: str,
        top_k: int = 5,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索技能
        
        Args:
            query: 搜索关键词
            top_k: 返回结果数量
            tags: 标签过滤
            
        Returns:
            搜索结果
        """
        request = SkillSearchRequest(
            query=query,
            top_k=top_k,
            tags=tags or []
        )
        
        results = self._request(
            "POST",
            "/api/v1/skills/search",
            json=request.model_dump()
        )
        
        return results
    
    def list_skills(
        self,
        tag: Optional[str] = None,
        author: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出所有技能
        
        Args:
            tag: 标签过滤
            author: 作者过滤
            
        Returns:
            技能列表
        """
        params = {}
        if tag:
            params["tag"] = tag
        if author:
            params["author"] = author
        
        results = self._request(
            "GET",
            "/api/v1/skills",
            params=params
        )
        
        return results
    
    def get_skill(self, skill_id: str) -> Dict[str, Any]:
        """
        获取单个技能详情
        
        Args:
            skill_id: 技能 ID
            
        Returns:
            技能详情
        """
        result = self._request(
            "GET",
            f"/api/v1/skills/{skill_id}"
        )
        
        return result
    
    def delete_skill(self, skill_id: str) -> Dict[str, Any]:
        """
        删除技能
        
        Args:
            skill_id: 技能 ID
            
        Returns:
            删除结果
        """
        result = self._request(
            "DELETE",
            f"/api/v1/skills/{skill_id}"
        )
        
        print(f"✅ 技能已删除: {skill_id}")
        return result
    
    def sync(self) -> Dict[str, Any]:
        """
        与服务器同步技能
        
        Returns:
            同步结果
        """
        request = SyncRequest(
            agent_id=self.agent_id,
            last_sync=self._last_sync,
            local_skills=list(self._skills_cache.keys())
        )
        
        result = self._request(
            "POST",
            "/api/v1/sync",
            json=request.model_dump()
        )
        
        self._last_sync = datetime.utcnow()
        
        print(f"✅ 同步完成: 新增 {len(result.get('new_skills', []))} 个技能")
        return result
    
    # ==================== WebSocket 实时通信 ====================
    
    def on_skill_update(self, handler: Callable):
        """
        注册技能更新处理器
        
        Args:
            handler: 处理函数，接收 skill_info 参数
        """
        if "skill_update" not in self._ws_handlers:
            self._ws_handlers["skill_update"] = []
        self._ws_handlers["skill_update"].append(handler)
        
        return handler  # 支持装饰器用法
    
    async def connect_websocket(self, ws_url: str = None):
        """
        连接 WebSocket
        
        Args:
            ws_url: WebSocket URL，默认从服务器 URL 推断
        """
        if ws_url is None:
            ws_url = f"{self.ws_url}:8765"
        
        self.ws_running = True
        
        while self.ws_running:
            try:
                async with websockets.connect(ws_url) as websocket:
                    self.ws_connection = websocket
                    print(f"✅ WebSocket 已连接: {ws_url}")
                    
                    # 发送注册信息
                    await websocket