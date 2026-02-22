"""
共享数据模型定义
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class SkillStatus(str, Enum):
    """技能状态"""
    ACTIVE = "active"          # 可用
    DEPRECATED = "deprecated"  # 已弃用
    ERROR = "error"           # 有错误
    PENDING = "pending"       # 待审核


class SkillMetadata(BaseModel):
    """技能元数据"""
    name: str = Field(..., description="技能名称")
    version: str = Field(default="1.0.0", description="版本号")
    description: str = Field(default="", description="技能描述")
    author: str = Field(default="", description="作者")
    tags: List[str] = Field(default_factory=list, description="标签")
    dependencies: List[str] = Field(default_factory=list, description="依赖项")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="参数定义")
    return_type: Optional[str] = Field(default=None, description="返回类型")
    examples: List[str] = Field(default_factory=list, description="使用示例")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "excel_analyzer",
                "version": "1.0.0",
                "description": "自动分析Excel文件数据",
                "author": "Agent-A",
                "tags": ["excel", "data-analysis", "pandas"],
                "dependencies": ["pandas", "openpyxl"]
            }
        }


class Skill(BaseModel):
    """技能完整模型"""
    id: str = Field(..., description="唯一标识")
    metadata: SkillMetadata = Field(..., description="元数据")
    code: str = Field(..., description="技能代码")
    status: SkillStatus = Field(default=SkillStatus.ACTIVE, description="状态")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")
    created_by: Optional[str] = Field(default=None, description="创建者")
    usage_count: int = Field(default=0, description="使用次数")
    rating: float = Field(default=5.0, ge=0, le=5, description="评分")
    
    class Config:
        from_attributes = True


class SkillCreateRequest(BaseModel):
    """创建技能请求"""
    metadata: SkillMetadata
    code: str
    
    
class SkillUpdateRequest(BaseModel):
    """更新技能请求"""
    metadata: Optional[SkillMetadata] = None
    code: Optional[str] = None
    status: Optional[SkillStatus] = None


class SkillSearchRequest(BaseModel):
    """搜索技能请求"""
    query: str = Field(..., description="搜索关键词")
    tags: List[str] = Field(default_factory=list, description="标签过滤")
    top_k: int = Field(default=5, ge=1, le=20, description="返回数量")
    

class SkillSearchResponse(BaseModel):
    """搜索技能响应"""
    skills: List[Skill]
    total: int
    query: str


class SyncRequest(BaseModel):
    """同步请求"""
    agent_id: str = Field(..., description="Agent 标识")
    last_sync: Optional[datetime] = Field(default=None, description="上次同步时间")
    local_skills: List[str] = Field(default_factory=list, description="本地已有的技能ID")


class SyncResponse(BaseModel):
    """同步响应"""
    new_skills: List[Skill] = Field(default_factory=list, description="新增技能")
    updated_skills: List[Skill] = Field(default_factory=list, description="更新的技能")
    deleted_skills: List[str] = Field(default_factory=list, description="删除的技能")
    next_sync: datetime = Field(default_factory=datetime.utcnow, description="建议下次同步时间")


class WebSocketMessage(BaseModel):
    """WebSocket 消息"""
    type: str = Field(..., description="消息类型")
    payload: Dict[str, Any] = Field(default_factory=dict, description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")
    sender: str = Field(default="server", description="发送者")


class AgentRegistration(BaseModel):
    """Agent 注册信息"""
    agent_id: str = Field(..., description="Agent 唯一标识")
    name: str = Field(..., description="Agent 名称")
    version: str = Field(default="1.0.0", description="Agent 版本")
    capabilities: List[str] = Field(default_factory=list, description="能力列表")
    ip_address: Optional[str] = Field(default=None, description="IP 地址")
    registered_at: datetime = Field(default_factory=datetime.utcnow, description="注册时间")


class HealthCheck(BaseModel):
    """健康检查"""
    status: str = Field(default="healthy", description="状态")
    version: str = Field(..., description="版本")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")
    uptime: float = Field(default=0.0, description="运行时间（秒）")
    connected_agents: int = Field(default=0, description="已连接 Agent 数量")
    total_skills: int = Field(default=0, description="总技能数量")