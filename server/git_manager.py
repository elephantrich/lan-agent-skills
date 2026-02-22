"""
Git 技能仓库管理器
负责技能的版本控制、提交历史和分支管理
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import git
from git import GitCommandError, Repo

from shared.models import Skill, SkillMetadata
from shared.utils import sanitize_filename


class GitManager:
    """
    Git 仓库管理器
    管理技能代码的版本控制
    """
    
    def __init__(self, repo_path: str, bare_mode: bool = True):
        """
        初始化 Git 管理器
        
        Args:
            repo_path: 仓库路径
            bare_mode: 是否使用 bare 模式（无工作目录）
        """
        self.repo_path = Path(repo_path).resolve()
        self.bare_mode = bare_mode
        self.repo: Optional[Repo] = None
        
    def initialize(self) -> Repo:
        """
        初始化 Git 仓库
        
        Returns:
            Repo 对象
        """
        if self.repo_path.exists():
            # 检查是否已存在 Git 仓库
            git_dir = self.repo_path / ("objects" if self.bare_mode else ".git")
            if git_dir.exists():
                print(f"📦 加载已有仓库: {self.repo_path}")
                self.repo = Repo(str(self.repo_path))
                return self.repo
        
        # 创建新仓库
        self.repo_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.bare_mode:
            print(f"📦 创建 bare 仓库: {self.repo_path}")
            self.repo = Repo.init(str(self.repo_path), bare=True)
        else:
            print(f"📦 创建普通仓库: {self.repo_path}")
            self.repo = Repo.init(str(self.repo_path))
        
        # 创建初始提交（仅普通仓库）
        if not self.bare_mode:
            self._create_initial_commit()
        
        return self.repo
    
    def _create_initial_commit(self):
        """创建初始提交"""
        # 创建 README
        readme_path = self.repo_path / "README.md"
        readme_content = """# Skills Repository

This repository contains shared skills for LAN Agent system.

## Structure

- `skills/` - Python skill files
- `metadata/` - Skill metadata in JSON format
- `docs/` - Documentation

## How to Use

See the main project documentation for usage instructions.
"""
        readme_path.write_text(readme_content, encoding='utf-8')
        
        # 创建目录结构
        (self.repo_path / "skills").mkdir(exist_ok=True)
        (self.repo_path / "metadata").mkdir(exist_ok=True)
        (self.repo_path / "docs").mkdir(exist_ok=True)
        
        # 创建 .gitignore
        gitignore_path = self.repo_path / ".gitignore"
        gitignore_content = """__pycache__/
*.pyc
*.pyo
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
.DS_Store
*.swp
*.swo
*~
.vscode/
.idea/
"""
        gitignore_path.write_text(gitignore_content, encoding='utf-8')
        
        # 提交
        self.repo.index.add(["README.md", ".gitignore", "skills/", "metadata/", "docs/"])
        self.repo.index.commit(
            "Initial commit: Setup skills repository structure",
            author=git.Actor("LAN Agent Skills", "skills@lan.local")
        )
        print("✅ 初始提交完成")
    
    def add_skill(self, skill: Skill, code: str) -> str:
        """
        添加技能到仓库
        
        Args:
            skill: 技能对象
            code: 技能代码
            
        Returns:
            提交哈希
        """
        if self.bare_mode:
            raise ValueError("Bare 仓库不能直接添加文件，请使用 clone 后的仓库")
        
        skill_name = sanitize_filename(skill.metadata.name)
        
        # 保存代码文件
        skill_path = self.repo_path / "skills" / f"{skill_name}.py"
        skill_path.write_text(code, encoding='utf-8')
        
        # 保存元数据
        import json
        meta_path = self.repo_path / "metadata" / f"{skill_name}.json"
        meta_data = {
            "id": skill.id,
            "name": skill.metadata.name,
            "version": skill.metadata.version,
            "description": skill.metadata.description,
            "author": skill.metadata.author,
            "tags": skill.metadata.tags,
            "dependencies": skill.metadata.dependencies,
            "created_at": skill.created_at.isoformat() if skill.created_at else None,
            "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
            "created_by": skill.created_by,
            "status": skill.status.value
        }
        meta_path.write_text(json.dumps(meta_data, indent=2, ensure_ascii=False), encoding='utf-8')
        
        # Git 提交
        self.repo.index.add([str(skill_path.relative_to(self.repo_path)), 
                             str(meta_path.relative_to(self.repo_path))])
        commit = self.repo.index.commit(
            f"Add skill: {skill.metadata.name} v{skill.metadata.version}",
            author=git.Actor(skill.metadata.author or "Unknown", "agent@lan.local")
        )
        
        print(f"✅ 技能已提交: {commit.hexsha[:7]}")
        return commit.hexsha
    
    def get_skill_history(self, skill_name: str) -> List[dict]:
        """
        获取技能的历史记录
        
        Args:
            skill_name: 技能名称
            
        Returns:
            提交历史列表
        """
        if self.bare_mode:
            raise ValueError("Bare 仓库不能查看历史，请使用 clone 后的仓库")
        
        skill_file = f"skills/{sanitize_filename(skill_name)}.py"
        
        history = []
        for commit in self.repo.iter_commits(paths=skill_file):
            history.append({
                "hash": commit.hexsha,
                "short_hash": commit.hexsha[:7],
                "message": commit.message.strip(),
                "author": str(commit.author),
                "date": commit.committed_datetime.isoformat(),
                "stats": {
                    "insertions": commit.stats.total["insertions"],
                    "deletions": commit.stats.total["deletions"],
                    "lines": commit.stats.total["lines"]
                }
            })
        
        return history
    
    def clone_repo(self, target_path: str, branch: str = "master") -> Repo:
        """
        克隆仓库到目标路径
        
        Args:
            target_path: 目标路径
            branch: 分支名称
            
        Returns:
            Repo 对象
        """
        target = Path(target_path).resolve()
        if target.exists():
            shutil.rmtree(target)
        
        print(f"📦 克隆仓库到: {target}")
        repo = Repo.clone_from(str(self.repo_path), str(target), branch=branch)
        return repo
    
    def create_branch(self, branch_name: str, from_branch: str = "master") -> str:
        """
        创建新分支
        
        Args:
            branch_name: 分支名称
            from_branch: 基于哪个分支
            
        Returns:
            分支名称
        """
        if self.bare_mode:
            raise ValueError("Bare 仓库不能直接创建分支")
        
        # 切换到源分支
        self.repo.git.checkout(from_branch)
        
        # 创建新分支
        new_branch = self.repo.create_head(branch_name)
        new_branch.checkout()
        
        print(f"✅ 创建分支: {branch_name} (基于 {from_branch})")
        return branch_name
    
    def merge_branch(self, source_branch: str, target_branch: str = "master", 
                    commit_message: str = None) -> str:
        """
        合并分支
        
        Args:
            source_branch: 源分支
            target_branch: 目标分支
            commit_message: 提交信息
            
        Returns:
            提交哈希
        """
        if self.bare_mode:
            raise ValueError("Bare 仓库不能直接合并分支")
        
        # 切换到目标分支
        self.repo.git.checkout(target_branch)
        
        # 合并
        if commit_message:
            self.repo.git.merge(source_branch, m=commit_message)
        else:
            self.repo.git.merge(source_branch)
        
        commit_hash = self.repo.head.commit.hexsha
        print(f"✅ 合并 {source_branch} 到 {target_branch}: {commit_hash[:7]}")
        return commit_hash
    
    def get_stats(self) -> dict:
        """
        获取仓库统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            "total_commits": 0,
            "total_files": 0,
            "branches": [],
            "skills_count": 0,
            "size_mb": 0
        }
        
        try:
            # 提交数
            stats["total_commits"] = len(list(self.repo.iter_commits("HEAD")))
            
            # 分支
            stats["branches"] = [str(b) for b in self.repo.branches]
            
            # 文件数（仅统计 skills 目录）
            skills_dir = self.repo_path / "skills"
            if skills_dir.exists():
                stats["skills_count"] = len(list(skills_dir.glob("*.py")))
            
            # 仓库大小
            import subprocess
            result = subprocess.run(
                ["du", "-sm", str(self.repo_path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                stats["size_mb"] = int(result.stdout.split()[0])
                
        except Exception as e:
            print(f"获取统计信息失败: {e}")
        
        return stats