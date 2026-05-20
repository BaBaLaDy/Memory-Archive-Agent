from pathlib import Path
from datetime import date

from .base import BaseTool, ToolResult
from maa.tools import read_file



def _strip_frontmatter(text: str) -> str:
    """去掉 Markdown frontmatter，返回正文"""
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        return text
    parts = stripped.split("---\n", 2)
    if len(parts) >= 3:
        return parts[2]
    return text


def _compute_overlap_and_delta(old_body: str, new_body: str) -> tuple[float, list[str]]:
    """计算重叠率和新行列表，用于去重决策"""
    old_lines = set(old_body.splitlines())
    new_lines = new_body.splitlines()

    if not new_lines:
        return 0.0, []

    delta = [line for line in new_lines if line not in old_lines]
    overlap = 1.0 - len(delta) / len(new_lines)
    return overlap, delta


class ArchiveFileTool(BaseTool):
    """写入 Markdown 归档文件 -- source_path 和 content 二选一，优先 source_path"""

    name = "archive_file"
    description = (
        "将文件内容写入 Markdown 归档文件，自动添加 frontmatter。"
        "提供 source_path 时直接读取源文件（推荐，避免传大量内容）；"
        "提供 content 时使用传入的文本内容。二选一，优先 source_path。"
        "文件名始终保留原始文件名，不重命名。"
        "目标路径已存在同名文件时，按内容重叠率自动决策："
        "≥85% 增量追加（仅追加新行）、40-85% 全文追加、<40% 拒绝并建议改名。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "source_path": {"type": "string", "description": "要归档的源文件路径（推荐，工具自己读取，避免传大量内容）"},
            "content": {"type": "string", "description": "文件正文内容（仅在无源文件时使用，如归档网页抓取结果）"},
            "target_path": {"type": "string", "description": "相对于存储根目录的目标路径，如 projects/my-project/notes.md"},
            "title": {"type": "string", "description": "文件标题"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "标签列表"},
            "category": {"type": "string", "description": "分类：projects, research, personal, inbox"},
            "project": {"type": "string", "description": "所属项目名称"},
            "original_title": {"type": "string", "description": "原始文件名（可选）"},
        },
        "required": ["target_path", "title"],
    }

    def execute(
        self,
        target_path: str,
        title: str,
        source_path: str = "",
        content: str = "",
        tags: list[str] | None = None,
        category: str = "inbox",
        project: str | None = None,
        original_title: str = "",
    ) -> ToolResult:
        from maa.storage.repo import RepoManager
        from maa.config import load_config

        config = load_config()
        repo = RepoManager(config.storage_root)

        # --- 路径安全校验 ---
        full_path = repo.resolve_path(target_path)
        root_resolved = repo.root.resolve()

        # 1. 必须在存储根目录内
        if not str(full_path.resolve()).startswith(str(root_resolved)):
            return ToolResult(
                success=False,
                error=f"安全拒绝：目标路径 {target_path} 在存储根目录之外",
            )
        # 2. 禁止直接写入 .maa/ 系统目录
        if ".ama" in full_path.resolve().parts:
            return ToolResult(
                success=False,
                error="安全拒绝：禁止直接写入 .ama 系统目录，请使用 update_index 工具更新索引",
            )

        # 优先从源文件读取，统一走 MarkItDown 解析
        if source_path:
            sp = Path(source_path)
            if not sp.exists():
                return ToolResult(success=False, error=f"源文件不存在: {source_path}")
            try:
                content = read_file(sp)
            except ImportError:
                return ToolResult(success=False, error="markitdown 未安装，无法解析文件")
            except Exception as e:
                return ToolResult(success=False, error=f"文件解析失败: {str(e)}")

            if not content.strip():
                return ToolResult(success=False, error=f"无法从此文件提取文本内容: {source_path}")
            if not original_title:
                original_title = sp.name

        if not content:
            return ToolResult(success=False, error="未提供内容：请提供 source_path 或 content")

        full_path.parent.mkdir(parents=True, exist_ok=True)
        tags = tags or []

        # --- 同名文件冲突处理（三段式策略）---
        if full_path.exists():
            existing = read_file(full_path)
            existing_body = _strip_frontmatter(existing)
            new_body = _strip_frontmatter(content)

            overlap, delta = _compute_overlap_and_delta(existing_body, new_body)

            # 完全重复 → 跳过
            if overlap >= 0.95:
                return ToolResult(
                    success=True,
                    data={
                        "path": target_path,
                        "action": "skipped",
                        "reason": "内容完全重复，无需归档",
                    },
                )

            # 高度重叠（≥85%）→ 只追加增量行，避免冗余
            if overlap >= 0.85:
                delta_block = (
                    f"\n\n---\n\n"
                    f"> 📎 增量更新 | {date.today()} | +{len(delta)} 行新内容\n\n"
                    + "\n".join(delta)
                )
                with full_path.open("a", encoding="utf-8") as f:
                    f.write(delta_block)
                return ToolResult(
                    success=True,
                    data={
                        "path": target_path,
                        "action": "delta_appended",
                        "new_lines": len(delta),
                        "overlap": f"{overlap:.0%}",
                    },
                )

            # 中度重叠（40-85%）→ 全文追加，保留新文件完整性
            if overlap >= 0.40:
                append_block = (
                    f"\n\n---\n\n"
                    f"> 📎 同主题补充 | {date.today()} | 追加全文\n\n"
                    + new_body
                )
                with full_path.open("a", encoding="utf-8") as f:
                    f.write(append_block)
                return ToolResult(
                    success=True,
                    data={
                        "path": target_path,
                        "action": "appended",
                        "overlap": f"{overlap:.0%}",
                        "warning": "内容部分重复，已追加全文到现有文件末尾",
                    },
                )

            # 低重叠（<40%）→ 同名异内容，拒绝并建议改名
            alt_name = f"{full_path.stem}-{date.today()}{full_path.suffix}"
            alt_target = f"{target_path.rsplit('/', 1)[0]}/{alt_name}" if "/" in target_path else alt_name
            return ToolResult(
                success=False,
                error=(
                    f"同名文件已存在但内容差异大（重叠率 {overlap:.0%}），"
                    f"不覆盖、不合并。建议使用 target_path: {alt_target}"
                ),
            )

        # --- 新文件：正常写入 ---
        frontmatter = (
            "---\n"
            "type: memory_archive_agent\n"
            f"category: {category}\n"
            f"project: {project or ''}\n"
            f"tags: [{', '.join(tags)}]\n"
            f"created_at: {date.today()}\n"
            f"original_title: {original_title or title}\n"
            "---\n\n"
            f"# {title}\n\n"
        )

        full_path.write_text(frontmatter + content, encoding="utf-8")
        return ToolResult(success=True, data={"path": target_path})


class UpdateIndexTool(BaseTool):
    """更新双层索引 + 项目映射"""

    name = "update_index"
    description = "更新指定文件夹的 .index.md、全局 .maa/index.json 索引，同时同步 .maa/project_map.json 项目映射"
    parameters = {
        "type": "object",
        "properties": {
            "folder_path": {"type": "string", "description": "要更新索引的文件夹路径（相对于存储根目录）"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "文件夹级标签（可选）"},
            "description": {"type": "string", "description": "文件夹描述（可选）"},
            "project": {"type": "string", "description": "项目名称（可选，用于更新 project_map.json）"},
        },
        "required": ["folder_path"],
    }

    def execute(
        self,
        folder_path: str,
        tags: list[str] | None = None,
        description: str = "",
        project: str = "",
    ) -> ToolResult:
        from maa.storage.repo import RepoManager
        from maa.storage import index as idx
        from maa.storage.models import IndexEntry
        from maa.config import load_config

        config = load_config()
        repo = RepoManager(config.storage_root)
        folder = repo.resolve_path(folder_path)

        if not folder.exists():
            return ToolResult(success=False, error=f"文件夹不存在: {folder_path}")

        tags = tags or []
        md_files = list(folder.glob("*.md"))
        file_names = [f.name for f in md_files if f.name != ".index.md"]

        title = folder_path.split("/")[-1].title()
        desc = description or f"{title} 相关文档"
        idx.update_folder_index(folder, title, tags, desc, file_names)

        for mf in md_files:
            if mf.name == ".index.md":
                continue
            rel = mf.relative_to(repo.root)
            summary = idx.generate_summary(mf)
            entry = IndexEntry(
                path=str(rel),
                title=mf.stem.replace("-", " ").title(),
                tags=tags,
                category=folder_path.split("/")[0] if "/" in folder_path else folder_path,
                project=folder_path.split("/")[1] if len(folder_path.split("/")) > 1 else None,
                created_at=str(date.today()),
                summary=summary,
            )
            idx.add_to_global_index(repo.root, entry)

        # 同步 project_map：如果有项目名，将文件注册到项目映射
        if project:
            project_key = project.lower().replace(" ", "-")
            for mf in md_files:
                if mf.name == ".index.md":
                    continue
                rel = str(mf.relative_to(repo.root))
                idx.add_to_project_map(
                    repo.root,
                    project_key=project_key,
                    file_path=rel,
                    project_name=project,
                    tags=tags,
                )

        return ToolResult(success=True, data={"folder": folder_path, "files": file_names})


class SyncIndexTool(BaseTool):
    """扫描文件夹，对比索引，修复遗漏或不一致的条目"""

    name = "sync_index"
    description = (
        "扫描指定文件夹（或整个知识库）中所有文件，对比全局索引，"
        "自动添加缺失的条目，同时清理文件已被删除的过期条目。"
        "用于修复索引不同步问题：search_index 查不到实际存在的文件、或查到已删除的文件。"
        "设置 dry_run=True 时只检测不修复，返回不一致清单。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "folder_path": {
                "type": "string",
                "description": "要检查的文件夹路径（相对于存储根目录）。留空则扫描整个知识库。",
            },
            "dry_run": {
                "type": "boolean",
                "description": "仅检测不修复（默认 false），返回不一致清单供确认",
            },
        },
    }

    def execute(self, folder_path: str = "", dry_run: bool = False) -> ToolResult:
        from maa.storage.repo import RepoManager
        from maa.storage import index as idx
        from maa.storage.models import IndexEntry
        from maa.config import load_config

        config = load_config()
        repo = RepoManager(config.storage_root)

        # 确定扫描范围
        if folder_path:
            scan_root = repo.resolve_path(folder_path)
            if not scan_root.exists():
                return ToolResult(success=False, error=f"文件夹不存在: {folder_path}")
        else:
            scan_root = repo.root

        # 加载当前索引（路径统一用 /，兼容 Windows \\ 差异）
        global_index = idx.load_global_index(repo.root)
        indexed_paths = {e.get("path", "").replace("\\", "/") for e in global_index.get("entries", [])}

        # 扫描所有文件
        missing: list[dict] = []
        present: list[str] = []
        actual_paths: set[str] = set()  # 磁盘上实际存在的所有文件路径
        scanned = 0

        NON_MD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".docx", ".xlsx", ".pptx"}

        for md_file in scan_root.rglob("*.md"):
            # 跳过系统文件和索引文件
            if ".ama" in md_file.parts or md_file.name == ".index.md" or ".git" in md_file.parts:
                continue

            rel = str(md_file.relative_to(repo.root)).replace("\\", "/")
            scanned += 1

            actual_paths.add(rel)
            if rel not in indexed_paths:
                # 提取 frontmatter 信息用于索引条目
                category = rel.split("/")[0] if "/" in rel else "inbox"
                project = rel.split("/")[1] if len(rel.split("/")) > 1 else None

                # 尝试从文件内容提取标题
                title = md_file.stem.replace("-", " ").replace("_", " ")
                try:
                    first_lines = "\n".join(read_file(md_file).splitlines()[:10])
                    for line in first_lines.split("\n"):
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break
                except Exception:
                    pass

                missing.append({
                    "path": rel,
                    "title": title,
                    "category": category,
                    "project": project,
                    "file_type": "md",
                })
            else:
                present.append(rel)

        # 扫描非 .md 文件
        for ext in NON_MD_EXTENSIONS:
            for f in scan_root.rglob(f"*{ext}"):
                if ".ama" in f.parts or ".git" in f.parts:
                    continue
                rel = str(f.relative_to(repo.root)).replace("\\", "/")
                scanned += 1
                actual_paths.add(rel)
                if rel not in indexed_paths:
                    category = rel.split("/")[0] if "/" in rel else "inbox"
                    project = rel.split("/")[1] if len(rel.split("/")) > 1 else None
                    file_type = ext.lstrip(".").lower()
                    size_kb = f.stat().st_size // 1024
                    missing.append({
                        "path": rel,
                        "title": f.stem.replace("-", " ").replace("_", " ").title(),
                        "category": category,
                        "project": project,
                        "file_type": file_type,
                        "size_kb": size_kb,
                    })
                else:
                    present.append(rel)

        if not dry_run:
            # 添加缺失条目到全局索引
            from datetime import date
            today = str(date.today())
            for m in missing:
                full = repo.resolve_path(m["path"])
                file_type = m.get("file_type", "md")
                if file_type == "md":
                    summary = idx.generate_summary(full)
                else:
                    size_kb = m.get("size_kb", full.stat().st_size // 1024)
                    summary = f"[{file_type.upper()}] {m['title']}，大小 {size_kb}KB"
                entry = IndexEntry(
                    path=m["path"],
                    title=m["title"],
                    tags=[],
                    category=m["category"],
                    project=m.get("project"),
                    created_at=today,
                    summary=summary,
                    file_type=file_type,
                )
                idx.add_to_global_index(repo.root, entry)

            # 修复已有条目中的空 summary（仅针对 .md 文件）
            global_index = idx.load_global_index(repo.root)
            repaired = 0
            for e in global_index.get("entries", []):
                if not e.get("summary") and e.get("path"):
                    rel_path = e["path"].replace("\\", "/")
                    if rel_path.endswith(".md"):
                        full = repo.resolve_path(e["path"])
                        if full.exists():
                            new_summary = idx.generate_summary(full)
                            if new_summary:
                                e["summary"] = new_summary
                                repaired += 1
            if repaired > 0:
                idx.save_global_index(repo.root, global_index)

            # 清理过期条目：扫描范围内的文件已被删除的条目
            scan_prefix = folder_path.replace("\\", "/").rstrip("/") + "/" if folder_path else ""
            stale: list[str] = []
            fresh_entries: list[dict] = []
            for e in global_index.get("entries", []):
                p = e.get("path", "").replace("\\", "/")
                in_scope = not scan_prefix or p.startswith(scan_prefix)
                if not in_scope or p in actual_paths:
                    fresh_entries.append(e)
                else:
                    stale.append(p)

            if stale:
                global_index["entries"] = fresh_entries
                idx.save_global_index(repo.root, global_index)

        else:
            # dry_run 模式：检测过期条目（同样限定扫描范围）
            scan_prefix = folder_path.replace("\\", "/").rstrip("/") + "/" if folder_path else ""
            stale: list[str] = []
            for e in global_index.get("entries", []):
                p = e.get("path", "").replace("\\", "/")
                in_scope = not scan_prefix or p.startswith(scan_prefix)
                if in_scope and p not in actual_paths:
                    stale.append(p)

        return ToolResult(success=True, data={
            "scanned": scanned,
            "in_index": len(present),
            "missing": len(missing),
            "stale": len(stale),
            "action": "detected" if dry_run else "repaired",
            "missing_files": missing[:50],
            "stale_files": stale[:50],
        })
