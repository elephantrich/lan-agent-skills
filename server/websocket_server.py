"""
WebSocket 服务器
用于实时推送技能更新
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Callable, Optional

import websockets
from websockets.server import WebSocketServerProtocol
from loguru import logger

from shared.models import WebSocketMessage


class WebSocketServer:
    """
    WebSocket 服务器
    管理 Agent 连接和实时消息推送
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        heartbeat_interval: int = 30
    ):
        """
        初始化 WebSocket 服务器
        
        Args:
            host: 监听地址
            port: 监听端口
            heartbeat_interval: 心跳间隔（秒）
        """
        self.host = host
        self.port = port
        self.heartbeat_interval = heartbeat_interval
        
        # 连接的客户端
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.client_info: Dict[str, dict] = {}
        
        # 消息处理器
        self.message_handlers: Dict[str, Callable] = {}
        
        # 服务器实例
        self.server = None
        self.running = False
        
        logger.info(f"🌐 WebSocket 服务器初始化完成: {host}:{port}")
    
    async def start(self):
        """启动服务器"""
        if self.running:
            logger.warning("WebSocket 服务器已经在运行")
            return
        
        self.running = True
        
        # 启动服务器
        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=self.heartbeat_interval,
            ping_timeout=10
        )
        
        logger.info(f"✅ WebSocket 服务器已启动: ws://{self.host}:{self.port}")
        
        # 保持运行
        await self.server.wait_closed()
    
    async def stop(self):
        """停止服务器"""
        if not self.running:
            return
        
        self.running = False
        
        # 关闭所有客户端连接
        close_tasks = []
        for client_id, client in self.clients.items():
            close_tasks.append(client.close())
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # 关闭服务器
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("🛑 WebSocket 服务器已停止")
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """
        处理新连接
        
        Args:
            websocket: WebSocket 连接
            path: 连接路径
        """
        # 生成客户端 ID
        client_id = f"client_{id(websocket)}_{datetime.utcnow().timestamp()}"
        
        # 注册客户端
        self.clients[client_id] = websocket
        self.client_info[client_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "remote_address": websocket.remote_address,
            "path": path
        }
        
        logger.info(f"🔗 新连接: {client_id} ({websocket.remote_address})")
        
        try:
            # 发送欢迎消息
            await self._send_to_client(
                client_id,
                "connected",
                {
                    "client_id": client_id,
                    "server_time": datetime.utcnow().isoformat(),
                    "message": "Welcome to LAN Agent Skills Server"
                }
            )
            
            # 监听消息
            async for message in websocket:
                await self._handle_message(client_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 连接关闭: {client_id}")
        except Exception as e:
            logger.error(f"❌ 连接错误 ({client_id}): {e}")
        finally:
            # 注销客户端
            self._unregister_client(client_id)
    
    def _unregister_client(self, client_id: str):
        """注销客户端"""
        if client_id in self.clients:
            del self.clients[client_id]
        if client_id in self.client_info:
            del self.client_info[client_id]
        logger.info(f"🗑️  注销客户端: {client_id}")
    
    async def _handle_message(self, client_id: str, message: str):
        """
        处理客户端消息
        
        Args:
            client_id: 客户端 ID
            message: 消息内容
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type", "unknown")
            payload = data.get("payload", {})
            
            logger.debug(f"📨 收到消息 ({client_id}): {msg_type}")
            
            # 处理不同类型的消息
            if msg_type == "ping":
                await self._send_to_client(client_id, "pong", {"time": datetime.utcnow().isoformat()})
                
            elif msg_type == "register":
                # 更新客户端信息
                agent_name = payload.get("agent_name", "unknown")
                self.client_info[client_id]["agent_name"] = agent_name
                logger.info(f"📝 注册 Agent: {agent_name} ({client_id})")
                
                await self._send_to_client(client_id, "registered", {
                    "client_id": client_id,
                    "agent_name": agent_name
                })
                
            elif msg_type in self.message_handlers:
                # 调用自定义处理器
                handler = self.message_handlers[msg_type]
                await handler(client_id, payload)
                
            else:
                logger.warning(f"⚠️ 未知消息类型: {msg_type}")
                await self._send_to_client(client_id, "error", {
                    "message": f"Unknown message type: {msg_type}"
                })
                
        except json.JSONDecodeError:
            logger.error(f"❌ JSON 解析失败: {message[:100]}")
            await self._send_to_client(client_id, "error", {
                "message": "Invalid JSON format"
            })
        except Exception as e:
            logger.error(f"❌ 消息处理错误: {e}")
            await self._send_to_client(client_id, "error", {
                "message": str(e)
            })
    
    async def _send_to_client(self, client_id: str, msg_type: str, payload: dict):
        """
        发送消息给指定客户端
        
        Args:
            client_id: 客户端 ID
            msg_type: 消息类型
            payload: 消息内容
        """
        if client_id not in self.clients:
            logger.warning(f"⚠️ 客户端不存在: {client_id}")
            return
        
        try:
            message = WebSocketMessage(
                type=msg_type,
                payload=payload,
                sender="server"
            )
            
            await self.clients[client_id].send(message.model_dump_json())
            logger.debug(f"📤 发送消息 ({client_id}): {msg_type}")
            
        except Exception as e:
            logger.error(f"❌ 发送消息失败 ({client_id}): {e}")
    
    async def broadcast(self, msg_type: str, payload: dict, exclude: str = None):
        """
        广播消息给所有客户端
        
        Args:
            msg_type: 消息类型
            payload: 消息内容
            exclude: 排除的客户端 ID
        """
        tasks = []
        for client_id in self.clients:
            if client_id != exclude:
                tasks.append(self._send_to_client(client_id, msg_type, payload))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"📢 广播消息: {msg_type} -> {len(tasks)} 个客户端")
    
    def register_handler(self, msg_type: str, handler: Callable):
        """
        注册消息处理器
        
        Args:
            msg_type: 消息类型
            handler: 处理函数
        """
        self.message_handlers[msg_type] = handler
        logger.info(f"📝 注册处理器: {msg_type}")
    
    def get_stats(self) -> dict:
        """
        获取服务器统计信息
        
        Returns:
            统计信息
        """
        return {
            "connected_clients": len(self.clients),
            "total_connections": len(self.client_info),
            "running": self.running,
            "address": f"{self.host}:{self.port}",
            "registered_handlers": list(self.message_handlers.keys())
        }