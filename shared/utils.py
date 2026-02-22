"""
共享工具函数
"""
import hashlib
import re
import uuid
from datetime import datetime
from typing import Optional


def generate_skill_id(name: str, author: str = "") -> str:
    """
    生成技能唯一ID
    
    Args:
        name: 技能名称
        author: 作者
        
    Returns:
        唯一ID字符串
    """
    timestamp = datetime.utcnow().isoformat()
    content = f"{name}:{author}:{timestamp}:{uuid.uuid4()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全的文件名
    """
    # 移除非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除控制字符
    filename = ''.join(char for char in filename if ord(char) >= 32)
    # 限制长度
    filename = filename[:200]
    # 确保不为空
    if not filename or filename == '.':
        filename = 'skill'
    return filename


def validate_skill_code(code: str, language: str = "python") -> tuple[bool, Optional[str]]:
    """
    验证技能代码是否有效
    
    Args:
        code: 代码字符串
        language: 编程语言
        
    Returns:
        (是否有效, 错误信息)
    """
    if not code or not code.strip():
        return False, "代码不能为空"
    
    if language == "python":
        try:
            compile(code, '<string>', 'exec')
            return True, None
        except SyntaxError as e:
            return False, f"Python 语法错误: {e}"
    
    # 其他语言暂不支持语法检查
    return True, None


def extract_imports(code: str, language: str = "python") -> list[str]:
    """
    从代码中提取导入的依赖
    
    Args:
        code: 代码字符串
        language: 编程语言
        
    Returns:
        依赖列表
    """
    imports = []
    
    if language == "python":
        # 匹配 import 语句
        import_pattern = r'^(?:from\s+(\S+)\s+import|import\s+(\S+))'
        for line in code.split('\n'):
            match = re.match(import_pattern, line.strip())
            if match:
                module = match.group(1) or match.group(2)
                # 获取顶层包名
                top_module = module.split('.')[0]
                if top_module not in ['os', 'sys', 'typing', 'datetime', 'json', 're']:
                    imports.append(top_module)
    
    return list(set(imports))


def format_skill_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 字节数
        
    Returns:
        格式化后的字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def parse_semantic_version(version: str) -> tuple[int, int, int]:
    """
    解析语义化版本号
    
    Args:
        version: 版本字符串，如 "1.2.3"
        
    Returns:
        (major, minor, patch) 元组
    """
    parts = version.split('.')
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return (major, minor, patch)