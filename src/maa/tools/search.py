from pathlib import Path

from .base import BaseTool, ToolResult
from maa.tools import read_file


class SearchIndexTool(BaseTool):
    """搜索知识库：索引优先，deep 模式交叉验证文件系统"""

    name = "search_index"
    description = (
        "搜索知识库中的文件。默认只查全局索引（快但可能不全）。"
        "设置 deep=True 时同时搜索文件系统（grep 文件名和内容），"
        "返回时标注每条结果的来源（index / filesystem）和是否在索引中。"
        "deep 模式用于：怀疑索引过期时交叉验证、确认文件实际存在。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "deep": {
                "type": "boolean",
                "description": "是否深度搜索文件系统（默认 false，仅查索引；true 时也 grep 文件名和 .md 文件内容前 500 行）",
            },
        },
        "required": ["query"],
    }

    def execute(self, query: str, deep: bool = False) -> ToolResult:
        from maa.storage.repo import RepoManager
        from maa.storage import index as idx
        from maa.config import load_config

        config = load_config()
        repo = RepoManager(config.storage_root)

        # 1. 索引搜索（始终执行）
        index_results = idx.search_global_index(repo.root, query)

        # 过滤掉文件已被删除的过期条目
        valid_results: list[dict] = []
        stale_paths: list[str] = []
        for r in index_results:
            r["path"] = r.get("path", "").replace("\\", "/")
            r["absolute_path"] = str(repo.resolve_path(r["path"]))
            full = repo.resolve_path(r["path"])
            if full.exists():
                valid_results.append(r)
            else:
                stale_paths.append(r["path"])

        if not deep:
            return ToolResult(success=True, data={
                "results": valid_results,
                "count": len(valid_results),
                "source": "index_only",
                "stale_skipped": len(stale_paths),
            })

        # 2. deep 模式：追加文件系统搜索
        indexed_paths = {e.get("path", "").replace("\\", "/") for e in valid_results}
        fs_results: list[dict] = []
        query_lower = query.lower()

        for md_file in repo.root.rglob("*.md"):
            # 跳过系统文件
            if ".ama" in md_file.parts or md_file.name == ".index.md":
                continue

            rel = str(md_file.relative_to(repo.root)).replace("\\", "/")

            # 文件名匹配
            name_match = query_lower in md_file.name.lower()

            # 内容前 500 行匹配（grep 等效）
            content_match = False
            if not name_match:
                try:
                    head = "\n".join(read_file(md_file).splitlines()[:500])
                    content_match = query_lower in head.lower()
                except Exception:
                    pass

            if name_match or content_match:
                in_index = rel in indexed_paths
                fs_results.append({
                    "path": rel,
                    "title": md_file.stem.replace("-", " "),
                    "source": "index" if in_index else "filesystem",
                    "in_index": in_index,
                    "match_type": "filename" if name_match else "content",
                })

        # 合并：索引结果标记为 in_index=True，文件系统结果补充
        # 统一用 / 做 key，避免 Windows \ 和 / 导致的重复
        merged: dict[str, dict] = {}
        for e in valid_results:
            p = e.get("path", "").replace("\\", "/")
            merged[p] = {**e, "source": "index", "in_index": True}

        for fs in fs_results:
            p = fs["path"].replace("\\", "/")
            if p not in merged:
                merged[p] = fs
            # 已在索引中的不再重复

        combined = sorted(merged.values(), key=lambda x: x["path"])
        missing = sum(1 for v in combined if not v.get("in_index", False))
        for r in combined:
            r["absolute_path"] = str(repo.resolve_path(r["path"]))

        return ToolResult(success=True, data={
            "results": combined,
            "count": len(combined),
            "source": "index + filesystem",
            "missing_from_index": missing,
            "stale_skipped": len(stale_paths),
            "hint": f"发现 {missing} 个文件在磁盘但不在索引中，可能需要 sync_index 修复" if missing else "",
        })


class ReadFileTool(BaseTool):
    """读取归档文件内容"""

    name = "read_file"
    description = "读取存储库中指定文件的内容"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "相对于存储根目录的文件路径"},
        },
        "required": ["file_path"],
    }

    def execute(self, file_path: str) -> ToolResult:
        from maa.storage.repo import RepoManager
        from maa.config import load_config

        config = load_config()
        repo = RepoManager(config.storage_root)
        full = repo.resolve_path(file_path)
        if not full.exists():
            return ToolResult(success=False, error=f"文件不存在: {file_path}")
        content = read_file(full)
        return ToolResult(success=True, data={
            "content": content,
            "path": file_path,
            "absolute_path": str(full),
        })


class ListProjectsTool(BaseTool):
    """列出项目文件夹"""

    name = "list_projects"
    description = "列出存储库中的项目文件夹，可按分类筛选"
    parameters = {
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "可选的分类过滤（projects, research, personal）"},
        },
    }

    def execute(self, category: str | None = None) -> ToolResult:
        from maa.storage.repo import RepoManager
        from maa.config import load_config

        config = load_config()
        repo = RepoManager(config.storage_root)
        categories = [category] if category else ["projects", "research", "personal"]

        projects = []
        for cat in categories:
            cat_path = repo.root / cat
            if cat_path.exists():
                for item in cat_path.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        projects.append({"path": f"{cat}/{item.name}", "category": cat})

        return ToolResult(success=True, data={"projects": projects, "count": len(projects)})
