#!/usr/bin/env python3
"""
基本使用示例
演示如何使用 Agent SDK 与服务器交互
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from client.agent import SkillAgent


def main():
    """主函数"""
    
    # 1. 初始化 Agent
    print("🚀 初始化 Agent...")
    agent = SkillAgent(
        server_url="http://localhost:8080",
        agent_id="demo-agent-001",
        agent_name="演示Agent"
    )
    
    # 2. 检查服务器健康状态
    print("\n📡 检查服务器状态...")
    try:
        health = agent._request("GET", "/health")
        print(f"✅ 服务器状态: {health.get('status', 'unknown')}")
        print(f"   版本: {health.get('version', 'unknown')}")
        print(f"   总技能数: {health.get('total_skills', 0)}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return
    
    # 3. 上传示例技能
    print("\n📤 上传示例技能...")
    
    skill_code = '''
import pandas as pd
from typing import Dict, Any

def analyze_csv(file_path: str) -> Dict[str, Any]:
    """
    分析 CSV 文件
    
    Args:
        file_path: CSV 文件路径
        
    Returns:
        分析结果字典
    """
    # 读取 CSV
    df = pd.read_csv(file_path)
    
    # 基础统计
    result = {
        "file_path": file_path,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": list(df.columns),
        "column_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2)
    }
    
    # 数值列统计
    numeric_columns = df.select_dtypes(include=['number']).columns
    if len(numeric_columns) > 0:
        result["numeric_summary"] = df[numeric_columns].describe().to_dict()
    
    # 缺失值统计
    missing = df.isnull().sum()
    result["missing_values"] = {col: int(count) for col, count in missing.items() if count > 0}
    
    return result


if __name__ == "__main__":
    # 测试
    import json
    result = analyze_csv("test.csv")
    print(json.dumps(result, indent=2, ensure_ascii=False))
'''
    
    try:
        result = agent.upload_skill(
            name="csv_analyzer",
            code=skill_code,
            description="自动分析 CSV 文件，返回行数、列名、数据类型、统计摘要等信息",
            author="Demo Agent",
            tags=["csv", "data-analysis", "pandas"],
            dependencies=["pandas"],
            version="1.0.0"
        )
        print(f"✅ 技能上传成功: {result.get('name', 'unknown')}")
        print(f"   ID: {result.get('id', 'unknown')}")
    except Exception as e:
        print(f"❌ 上传失败: {e}")
    
    # 4. 搜索技能
    print("\n🔍 搜索技能...")
    try:
        results = agent.search_skills(
            query="CSV数据分析",
            top_k=5
        )
        
        print(f"找到 {len(results)} 个结果:")
        for i, skill in enumerate(results, 1):
            print(f"\n  {i}. {skill.get('name', 'unknown')}")
            print(f"     描述: {skill.get('description', '无')[:60]}...")
            print(f"     作者: {skill.get('author', 'unknown')}")
            print(f"     相似度: {skill.get('similarity_score', 0):.2%}")
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
    
    # 5. 列出所有技能
    print("\n📋 列出所有技能...")
    try:
        skills = agent.list_skills()
        print(f"共有 {len(skills)} 个技能:")
        for skill in skills:
            print(f"  - {skill.get('name', 'unknown')} (by {skill.get('author', 'unknown')})")
    except Exception as e:
        print(f"❌ 列出失败: {e}")
    
    # 6. 同步技能
    print("\n🔄 同步技能...")
    try:
        sync_result = agent.sync()
        print(f"✅ 同步完成")
        print(f"   新增: {len(sync_result.get('new_skills', []))} 个")
        print(f"   更新: {len(sync_result.get('updated_skills', []))} 个")
        print(f"   删除: {len(sync_result.get('deleted_skills', []))} 个")
    except Exception as e:
        print(f"❌ 同步失败: {e}")
    
    # 结束
    print("\n✨ 演示完成！")
    print("\n更多功能:")
    print("  - 删除技能: agent.delete_skill(skill_id)")
    print("  - 获取详情: agent.get_skill(skill_id)")
    print("  - WebSocket: agent.connect_websocket()")
    print("")


if __name__ == "__main__":
    main()