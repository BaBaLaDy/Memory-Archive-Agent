from pathlib import Path
from maa.tools.base import BaseTool, ToolResult
from maa.storage.index import load_folder_index
from maa.storage.repo import CATEGORIES


class ListTreeTool(BaseTool):
    """扫描知识库目录树，获取完整结构 + 各文件夹 .index.md 摘要"""

    name = "list_tree"
    description = (
        "扫描知识库目录树，返回完整结构快照 + 各子文件夹的 .index.md 内容摘要。"
        "用于在归档前了解已有项目/研究/知识结构，是分类决策的前置工具。"
        "可选择性按分类过滤。纯只读操作，不修改任何文件。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "include_indexes": {
                "type": "boolean",
                "description": "是否包含各文件夹的 .index.md 内容（默认 true）",
            },
            "category_filter": {
                "type": "string",
                "description": "可选：按分类过滤（projects/research/personal）",
            },
        },
    }

    def execute(
        self,
        include_indexes: bool = True,
        category_filter: str | None = None,
    ) -> ToolResult:
        from maa.config import load_config
        from maa.storage.repo import RepoManager

        config = load_config()
        repo = RepoManager(config.storage_root)

        categories = [category_filter] if category_filter else [c for c in CATEGORIES if c != "inbox"]
        tree: dict = {}

        for cat in categories:
            cat_path = repo.root / cat
            if not cat_path.exists():
                tree[cat] = {}
                continue

            cat_data: dict = {}
            for item in sorted(cat_path.iterdir()):
                if not item.is_dir() or item.name.startswith("."):
                    continue

                folder_info: dict = {}
                folder_info["path"] = f"{cat}/{item.name}"

                # 读取该文件夹的 .index.md
                if include_indexes:
                    index_data = load_folder_index(item)
                    if index_data:
                        folder_info["index"] = index_data
                    else:
                        folder_info["index"] = None

                # 列出文件夹内的 .md 文件
                md_files = [
                    f.name
                    for f in sorted(item.glob("*.md"))
                    if f.name != ".index.md"
                ]
                folder_info["files"] = md_files

                cat_data[item.name] = folder_info

            # 如果分类下没有子目录但有直接文件，也展示出来
            if not cat_data:
                direct_files = [
                    f.name
                    for f in sorted(cat_path.glob("*.md"))
                    if f.name != ".index.md"
                ]
                direct_non_md: list[dict] = []
                for f in sorted(cat_path.iterdir()):
                    if f.is_file() and not f.name.startswith(".") and f.suffix.lower() not in (".md",):
                        direct_non_md.append({
                            "name": f.name,
                            "type": f.suffix.lstrip("."),
                            "size_kb": f.stat().st_size // 1024,
                        })
                if direct_files or direct_non_md:
                    cat_data["_direct_files"] = {
                        "path": cat,
                        "files": direct_files,
                        "other_files": direct_non_md,
                    }

            tree[cat] = cat_data

        return ToolResult(success=True, data=tree)


class ListDirTool(BaseTool):
    """列出任意目录的内容（纯 Python，跨平台，不需 shell）"""

    name = "list_dir"
    description = (
        "列出指定目录的内容（文件和子目录），返回名称、类型、大小和修改时间。"
        "纯 Python 实现，跨平台兼容，不依赖 shell 命令（ls/dir）。"
        "用于探索本地文件系统、验证路径是否存在、查看目录内容。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要列出的目录绝对路径，如 D:/InternWork/ 或 ~/MemoryArchive/",
            },
            "pattern": {
                "type": "string",
                "description": "可选：glob 模式过滤，如 *.md 只显示 Markdown 文件",
            },
        },
        "required": ["path"],
    }

    def execute(self, path: str, pattern: str = "") -> ToolResult:
        from pathlib import Path
        from datetime import datetime

        p = Path(path).expanduser()
        if not p.exists():
            return ToolResult(success=False, error=f"路径不存在: {path}")
        if not p.is_dir():
            return ToolResult(success=False, error=f"不是目录: {path}")

        entries: list[dict] = []
        targets = sorted(p.glob(pattern)) if pattern else sorted(p.iterdir())

        for item in targets:
            try:
                stat = item.stat()
                entries.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except OSError:
                entries.append({"name": item.name, "type": "unknown", "size": 0, "modified": ""})

        parent = str(p)
        return ToolResult(success=True, data={
            "path": parent,
            "count": len(entries),
            "entries": entries[:200],  # 最多 200 条
        })
