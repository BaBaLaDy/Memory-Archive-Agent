"""HTTP API 路由定义"""

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

# ---- 请求模型 ----

class ArchiveRequest(BaseModel):
    source_path: str = ""
    content: str = ""
    url: str = ""
    title: str = ""
    note: str = ""


class ChatRequest(BaseModel):
    message: str
    language: str | None = None


# ---- 引擎懒加载 ----

_engine = None
_tools: dict[str, object] = {}

def _init():
    """延迟初始化引擎和工具"""
    global _engine, _tools
    if _engine is not None:
        return

    from maa.config import load_config
    from maa.agent.engine import AgentEngine
    from maa.tools.parse import ParseFileTool
    from maa.tools.firecrawl import FirecrawlScrapeTool, FirecrawlSearchTool
    from maa.tools.archive import ArchiveFileTool, UpdateIndexTool, SyncIndexTool
    from maa.tools.search import SearchIndexTool, ReadFileTool, ListProjectsTool
    from maa.tools.sync import GitSyncTool, GitStatusTool, GitRemoteInfoTool, PullToLocalTool
    from maa.tools.code_run import CodeRunTool
    from maa.tools.tree import ListTreeTool, ListDirTool
    from maa.tools.classify import ClassifyContentTool
    from maa.tools.batch import ScanDirectoryTool, BatchClassifyTool, BatchArchiveTool

    config = load_config()

    # 确保存储仓库已初始化（含 git init）
    from maa.storage.repo import RepoManager
    repo = RepoManager(config.storage_root)
    repo.ensure_initialized()

    engine = AgentEngine(
        model=config.llm_model,
        api_key=config.api_key if config.api_key else None,
        api_base=config.api_base if config.api_base else None,
        extra_body=config.extra_body or None,
        categories=config.categories,
        storage_root=config.storage_root,
    )

    tool_instances = [
        ParseFileTool(),
        FirecrawlScrapeTool(),
        FirecrawlSearchTool(),
        ListTreeTool(),
        ListDirTool(),
        ClassifyContentTool(),
        ScanDirectoryTool(),
        BatchClassifyTool(),
        BatchArchiveTool(),
        ArchiveFileTool(),
        UpdateIndexTool(),
        SyncIndexTool(),
        SearchIndexTool(),
        ReadFileTool(),
        ListProjectsTool(),
        GitSyncTool(),
        GitStatusTool(),
        GitRemoteInfoTool(),
        PullToLocalTool(),
        CodeRunTool(),
    ]
    for t in tool_instances:
        engine.register_tool(t)
        _tools[t.name] = t

    _engine = engine


# ---- 端点 ----

@router.get("/tools")
async def list_tools():
    """获取所有可用工具列表（供前端 / 命令提示使用）"""
    _init()
    return [
        {"name": name, "description": tool.description}
        for name, tool in _tools.items()
    ]

@router.post("/archive")
async def archive(req: ArchiveRequest):
    """归档内容：source_path、content 或 url 三选一"""
    _init()

    # 1. 获取目录树上下文
    tree_result = _tools["list_tree"].execute()
    tree_context = tree_result.data if tree_result.success else ""

    # 2. 分类
    classify_kwargs = {"tree_context": str(tree_context)}

    if req.source_path:
        sp = Path(req.source_path)
        if not sp.exists():
            raise HTTPException(status_code=400, detail=f"文件不存在: {req.source_path}")
        classify_kwargs["source_path"] = str(sp)
    elif req.content:
        classify_kwargs["content_summary"] = req.content[:2000]
        if req.title:
            classify_kwargs["content_summary"] = f"标题: {req.title}\n\n{req.content[:2000]}"
    elif req.url:
        # URL 场景：先抓取内容，再分类
        extract_result = _tools["extract_content"].execute(url=req.url)
        if not extract_result.success:
            raise HTTPException(status_code=400, detail=f"无法抓取网页: {extract_result.error}")
        content_data = extract_result.data
        classify_kwargs["content_summary"] = str(content_data)[:2000]
    else:
        raise HTTPException(status_code=400, detail="请提供 source_path、content 或 url 之一")

    classify_result = _tools["classify_content"].execute(**classify_kwargs)
    if not classify_result.success:
        raise HTTPException(status_code=500, detail=f"分类失败: {classify_result.error}")

    cd = classify_result.data

    # 3. 归档
    archive_kwargs = {
        "target_path": cd.get("target_path", "inbox/untitled.md"),
        "title": cd.get("title", req.title or "未命名"),
        "tags": cd.get("tags", []),
        "category": cd.get("category", "inbox"),
        "project": cd.get("project", ""),
    }
    if req.source_path:
        archive_kwargs["source_path"] = req.source_path
    elif req.content:
        archive_kwargs["content"] = req.content
    elif req.url:
        archive_kwargs["content"] = str(extract_result.data)

    archive_result = _tools["archive_file"].execute(**archive_kwargs)

    # 4. 更新索引
    folder = "/".join(archive_kwargs["target_path"].split("/")[:-1]) or "inbox"
    project_name = cd.get("project", "")
    _tools["update_index"].execute(
        folder_path=folder,
        tags=archive_kwargs["tags"],
        project=project_name,
    )

    return {
        "success": archive_result.success,
        "path": archive_result.data.get("path", archive_kwargs["target_path"]) if archive_result.success else None,
        "category": archive_kwargs["category"],
        "action": archive_result.data.get("action", "created") if archive_result.success else None,
        "error": archive_result.error if not archive_result.success else None,
    }


@router.get("/search")
async def search(q: str = Query(..., min_length=1, description="搜索关键词")):
    """搜索知识库索引"""
    _init()
    result = _tools["search_index"].execute(query=q)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.data


@router.get("/files/{path:path}")
async def read_file(path: str):
    """读取知识库中的文件内容"""
    _init()
    result = _tools["read_file"].execute(file_path=path)
    if not result.success:
        raise HTTPException(status_code=404, detail=f"文件不存在: {path}")
    return result.data


@router.get("/tree")
async def tree():
    """获取知识库目录树"""
    _init()
    result = _tools["list_tree"].execute()
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.data


@router.get("/projects")
async def projects():
    """获取项目列表"""
    _init()
    result = _tools["list_projects"].execute()
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.data


@router.get("/config")
async def get_config():
    """获取配置信息（storage_root 等）"""
    from maa.config import load_config
    from pathlib import Path
    config = load_config()
    storage_root = str(Path(config.storage_root).expanduser().resolve())
    return {"storage_root": storage_root}


def _safe_resolve(storage_root: str, path: str):
    """将路径解析到 storage_root 下，跨平台安全检查。
    返回 (absolute_target, ok, error_detail)。
    """
    import os
    root = os.path.normcase(os.path.abspath(os.path.expanduser(storage_root)))
    target = os.path.normcase(os.path.abspath(os.path.expanduser(path)))
    # Windows 路径不区分大小写，使用 normcase 归一化后比较
    if not target.startswith(root):
        return target, False, "禁止操作知识库外的路径"
    if not os.path.exists(target):
        return target, False, f"文件不存在: {path}"
    return target, True, ""


def _open_file_with_os(target: str):
    """跨平台用系统默认程序打开文件"""
    import os
    import subprocess
    import sys
    if sys.platform == "win32":
        os.startfile(target)
    elif sys.platform == "darwin":
        subprocess.run(["open", target])
    else:
        subprocess.run(["xdg-open", target])


def _reveal_file_with_os(target: str):
    """跨平台在文件管理器中定位文件"""
    import os
    import subprocess
    import sys
    if sys.platform == "win32":
        subprocess.run(["explorer", f"/select,{target}"])
    elif sys.platform == "darwin":
        subprocess.run(["open", "-R", target])
    else:
        subprocess.run(["xdg-open", os.path.dirname(target)])


@router.get("/open-file")
async def open_file(path: str = Query(..., description="文件绝对路径")):
    """用系统默认程序打开文件"""
    from maa.config import load_config
    config = load_config()
    target, ok, detail = _safe_resolve(config.storage_root, path)
    if not ok:
        raise HTTPException(status_code=403 if "禁止" in detail else 404, detail=detail)
    try:
        _open_file_with_os(target)
        return {"ok": True, "path": target}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reveal-file")
async def reveal_file(path: str = Query(..., description="文件绝对路径")):
    """在文件管理器中定位文件"""
    from maa.config import load_config
    config = load_config()
    target, ok, detail = _safe_resolve(config.storage_root, path)
    if not ok:
        raise HTTPException(status_code=403 if "禁止" in detail else 404, detail=detail)
    try:
        _reveal_file_with_os(target)
        return {"ok": True, "path": target}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(req: ChatRequest):
    """流式对话 Agent（SSE）"""
    _init()
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    from maa.server.sse import stream_event_to_sse
    from maa.agent.engine import StreamEventType

    async def event_generator():
        try:
            async for event in _engine.run_stream(req.message, language=req.language, debug=False):
                sse_text = stream_event_to_sse(event)
                yield sse_text
            # 发送完成事件
            yield f"event: done\ndata: \n\n"
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
