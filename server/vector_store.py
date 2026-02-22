"""
向量数据库存储管理器
基于 ChromaDB 实现技能的语义搜索
"""
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from shared.models import Skill, SkillMetadata


class VectorStore:
    """
    向量数据库管理器
    管理技能的语义索引和搜索
    """
    
    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "skills",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        初始化向量数据库
        
        Args:
            persist_directory: 持久化目录
            collection_name: 集合名称
            embedding_model: 嵌入模型名称
        """
        self.persist_directory = Path(persist_directory).resolve()
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        
        # 确保目录存在
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # 初始化 ChromaDB 客户端
        self.client = chromadb.Client(
            Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=str(self.persist_directory),
                anonymized_telemetry=False
            )
        )
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # 初始化嵌入模型
        print(f"📥 加载嵌入模型: {embedding_model}...")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        
        print(f"✅ 向量数据库已加载: {self.persist_directory}")
        print(f"   集合: {self.collection_name}")
        print(f"   文档数: {self.collection.count()}")
    
    def _build_document_content(self, skill: Skill, code: str) -> str:
        """
        构建用于嵌入的文档内容
        
        Args:
            skill: 技能对象
            code: 代码
            
        Returns:
            文档内容
        """
        parts = [
            f"Name: {skill.metadata.name}",
            f"Description: {skill.metadata.description}",
            f"Tags: {', '.join(skill.metadata.tags)}",
            f"Code:\n{code[:2000]}"  # 限制代码长度
        ]
        return "\n\n".join(parts)
    
    def add_skill(
        self,
        skill: Skill,
        code: str,
        embedding: Optional[List[float]] = None
    ) -> str:
        """
        添加技能到向量数据库
        
        Args:
            skill: 技能对象
            code: 技能代码
            embedding: 预计算的嵌入向量（可选）
            
        Returns:
            文档 ID
        """
        # 构建文档内容
        document_content = self._build_document_content(skill, code)
        
        # 计算嵌入
        if embedding is None:
            embedding = self.embedding_model.encode(document_content).tolist()
        
        # 元数据
        metadata = {
            "skill_id": skill.id,
            "name": skill.metadata.name,
            "version": skill.metadata.version,
            "description": skill.metadata.description,
            "author": skill.metadata.author,
            "tags": ",".join(skill.metadata.tags),
            "dependencies": ",".join(skill.metadata.dependencies),
            "status": skill.status.value,
            "created_at": skill.created_at.isoformat() if skill.created_at else "",
            "updated_at": skill.updated_at.isoformat() if skill.updated_at else ""
        }
        
        # 添加到集合
        doc_id = f"skill_{skill.id}"
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[document_content]
        )
        
        # 持久化
        self.persist()
        
        print(f"✅ 技能已索引: {skill.metadata.name} (ID: {doc_id})")
        return doc_id
    
    def update_skill(
        self,
        skill: Skill,
        code: str
    ) -> str:
        """
        更新技能
        
        Args:
            skill: 技能对象
            code: 技能代码
            
        Returns:
            文档 ID
        """
        doc_id = f"skill_{skill.id}"
        
        # 先删除旧版本
        try:
            self.collection.delete(ids=[doc_id])
        except Exception:
            pass
        
        # 添加新版本
        return self.add_skill(skill, code)
    
    def delete_skill(self, skill_id: str) -> bool:
        """
        删除技能
        
        Args:
            skill_id: 技能 ID
            
        Returns:
            是否成功
        """
        doc_id = f"skill_{skill_id}"
        
        try:
            self.collection.delete(ids=[doc_id])
            self.persist()
            print(f"✅ 技能已删除: {doc_id}")
            return True
        except Exception as e:
            print(f"❌ 删除技能失败: {e}")
            return False
    
    def search_skills(
        self,
        query: str,
        top_k: int = 5,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索技能
        
        Args:
            query: 搜索关键词
            top_k: 返回结果数量
            tags: 标签过滤
            author: 作者过滤
            status: 状态过滤
            
        Returns:
            搜索结果列表
        """
        # 计算查询的嵌入向量
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # 构建过滤条件
        where_filter = {}
        if tags:
            where_filter["tags"] = {"$contains": ",".join(tags)}
        if author:
            where_filter["author"] = author
        if status:
            where_filter["status"] = status
        
        # 执行搜索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter if where_filter else None,
            include=["metadatas", "documents", "distances"]
        )
        
        # 格式化结果
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                document = results["documents"][0][i] if results["documents"] else ""
                distance = results["distances"][0][i] if results["distances"] else 0.0
                
                # 计算相似度分数 (0-1, 1 表示最相似)
                similarity_score = 1 - distance
                
                formatted_results.append({
                    "id": doc_id,
                    "skill_id": metadata.get("skill_id", ""),
                    "name": metadata.get("name", ""),
                    "version": metadata.get("version", ""),
                    "description": metadata.get("description", ""),
                    "author": metadata.get("author", ""),
                    "tags": metadata.get("tags", "").split(",") if metadata.get("tags") else [],
                    "status": metadata.get("status", "active"),
                    "similarity_score": round(similarity_score, 4),
                    "document": document[:500] + "..." if len(document) > 500 else document
                })
        
        return formatted_results
    
    def get_all_skills(self) -> List[Dict[str, Any]]:
        """
        获取所有技能
        
        Returns:
            所有技能的列表
        """
        results = self.collection.get(
            include=["metadatas", "documents"]
        )
        
        skills = []
        if results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i] if results["metadatas"] else {}
                
                skills.append({
                    "id": doc_id,
                    "skill_id": metadata.get("skill_id", ""),
                    "name": metadata.get("name", ""),
                    "version": metadata.get("version", ""),
                    "description": metadata.get("description", ""),
                    "author": metadata.get("author", ""),
                    "tags": metadata.get("tags", "").split(",") if metadata.get("tags") else [],
                    "status": metadata.get("status", "active")
                })
        
        return skills
    
    def get_skill_by_id(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取技能
        
        Args:
            skill_id: 技能 ID
            
        Returns:
            技能信息，如果不存在返回 None
        """
        doc_id = f"skill_{skill_id}"
        
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=["metadatas", "documents"]
            )
            
            if results["ids"] and len(results["ids"]) > 0:
                metadata = results["metadatas"][0]
                document = results["documents"][0]
                
                return {
                    "id": doc_id,
                    "skill_id": metadata.get("skill_id", ""),
                    "name": metadata.get("name", ""),
                    "version": metadata.get("version", ""),
                    "description": metadata.get("description", ""),
                    "author": metadata.get("author", ""),
                    "tags": metadata.get("tags", "").split(",") if metadata.get("tags") else [],
                    "dependencies": metadata.get("dependencies", "").split(",") if metadata.get("dependencies") else [],
                    "status": metadata.get("status", "active"),
                    "created_at": metadata.get("created_at", ""),
                    "updated_at": metadata.get("updated_at", ""),
                    "document": document
                }
        except Exception as e:
            print(f"获取技能失败: {e}")
        
        return None
    
    def persist(self):
        """
        持久化数据到磁盘
        """
        try:
            self.client.persist()
        except Exception as e:
            print(f"持久化失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息
        """
        return {
            "total_documents": self.collection.count(),
            "collection_name": self.collection_name,
            "persist_directory": str(self.persist_directory),
            "embedding_model": self.embedding_model_name
        }