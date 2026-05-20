import json
from pathlib import Path

from .models import IndexEntry, ProjectMap, ProjectEntry


def _read_file(path: Path) -> str:
    """统一文件读取，走 MarkItDown 解析"""
    from markitdown import MarkItDown
    return MarkItDown().convert(str(path)).text_content


GLOBAL_INDEX_VERSION = 1


def _strip_frontmatter(text: str) -> str:
    """去掉 Markdown frontmatter，返回正文"""
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        return text
    parts = stripped.split("---\n", 2)
    if len(parts) >= 3:
        return parts[2]
    return text


def generate_summary(file_path: Path) -> str:
    """从文件中提取摘要：读前 200 字符，去除 frontmatter 和空白"""
    try:
        content = _read_file(file_path)
        if not content.strip():
            return ""
        body = _strip_frontmatter(content).strip()
        if not body:
            return ""
        return body[:200].strip()
    except Exception:
        return ""


def load_global_index(repo_root: Path) -> dict:
    """加载 .maa/index.json"""
    index_path = repo_root / ".ama" / "index.json"
    if not index_path.exists():
        return {"version": GLOBAL_INDEX_VERSION, "entries": []}
    with open(index_path, encoding="utf-8") as f:
        return json.load(f)


def save_global_index(repo_root: Path, data: dict) -> None:
    """保存 .maa/index.json"""
    index_path = repo_root / ".ama" / "index.json"
    index_path.parent.mkdir(exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def search_global_index(repo_root: Path, query: str) -> list[dict]:
    """在全局索引中搜索匹配的条目"""
    query_lower = query.lower().strip()
    # 空查询或单字符查询拒绝搜索（单字符会匹配几乎所有条目）
    if len(query_lower) < 2:
        return []
    index = load_global_index(repo_root)
    results = []
    for entry in index.get("entries", []):
        searchable = f'{entry.get("title", "")} {" ".join(entry.get("tags", []))} {entry.get("summary", "")} {entry.get("path", "")}'.lower()
        # 也加入文件名部分（不带路径）
        path = entry.get("path", "")
        filename = path.replace("\\", "/").split("/")[-1] if path else ""
        searchable += f" {filename}"
        if query_lower in searchable:
            results.append(entry)
    return results


def add_to_global_index(repo_root: Path, entry: IndexEntry) -> None:
    """添加条目到全局索引"""
    index = load_global_index(repo_root)
    entries = index.setdefault("entries", [])
    existing_paths = {e["path"] for e in entries}
    if entry.path not in existing_paths:
        entries.append(entry.to_dict())
        save_global_index(repo_root, index)


FOLDER_INDEX_TEMPLATE = """---
folder: {folder}
tags: {tags}
description: {description}
last_updated: {last_updated}
---

# {title}

## 相关文件
{file_links}
"""


def load_folder_index(folder_path: Path) -> dict | None:
    """读取文件夹 .index.md 的 frontmatter"""
    index_file = folder_path / ".index.md"
    if not index_file.exists():
        return None
    content = _read_file(index_file)
    if not content.startswith("---"):
        return None
    end = content.index("---", 3)
    import re
    frontmatter = content[3:end]
    data = {}
    for line in frontmatter.strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                items = [x.strip().strip('"') for x in val[1:-1].split(",") if x.strip()]
                data[key.strip()] = items
            else:
                data[key.strip()] = val.strip('"')
    return data


def update_folder_index(folder_path: Path, title: str, tags: list[str], description: str, files: list[str]) -> None:
    """更新文件夹 .index.md"""
    from datetime import date

    folder_rel = str(folder_path)
    file_links = "\n".join(f"- [[{f}]] - {f}" for f in files)
    content = FOLDER_INDEX_TEMPLATE.format(
        folder=folder_rel,
        tags=tags,
        description=description,
        last_updated=str(date.today()),
        title=title,
        file_links=file_links,
    )
    index_file = folder_path / ".index.md"
    index_file.write_text(content, encoding="utf-8")


# ---- Project Map 操作 ----

PROJECT_MAP_FILE = ".maa/project_map.json"


def load_project_map(repo_root: Path) -> ProjectMap:
    """加载 .maa/project_map.json"""
    map_path = repo_root / PROJECT_MAP_FILE
    if not map_path.exists():
        return ProjectMap(version=1)
    with open(map_path, encoding="utf-8") as f:
        data = json.load(f)
    return ProjectMap.from_dict(data)


def save_project_map(repo_root: Path, project_map: ProjectMap) -> None:
    """保存 .maa/project_map.json"""
    map_path = repo_root / PROJECT_MAP_FILE
    map_path.parent.mkdir(exist_ok=True)
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(project_map.to_dict(), f, ensure_ascii=False, indent=2)


def add_to_project_map(
    repo_root: Path,
    project_key: str,
    file_path: str,
    project_name: str = "",
    tags: list[str] | None = None,
    description: str = "",
) -> None:
    """将文件添加到项目映射，项目不存在则自动创建"""
    from datetime import date

    project_map = load_project_map(repo_root)
    today = str(date.today())

    if project_key in project_map.projects:
        entry = project_map.projects[project_key]
        if file_path not in entry.files:
            entry.files.append(file_path)
        entry.updated_at = today
        if tags:
            for tag in tags:
                if tag not in entry.tags:
                    entry.tags.append(tag)
    else:
        entry = ProjectEntry(
            name=project_name or project_key,
            description=description,
            tags=tags or [],
            files=[file_path],
            created_at=today,
            updated_at=today,
        )
        project_map.projects[project_key] = entry

    save_project_map(repo_root, project_map)
