"""Memory Archive Agent Tools"""

from pathlib import Path

from .base import BaseTool, ToolResult


def read_file(path: Path) -> str:
    """统一文件读取，走 MarkItDown 解析，支持所有格式（md/txt/pdf/docx/xlsx/pptx 等）"""
    from markitdown import MarkItDown
    return MarkItDown().convert(str(path)).text_content


from .parse import ParseFileTool
from .firecrawl import FirecrawlScrapeTool, FirecrawlSearchTool
from .archive import ArchiveFileTool, UpdateIndexTool, SyncIndexTool
from .search import SearchIndexTool, ReadFileTool, ListProjectsTool
from .sync import GitSyncTool, GitStatusTool, GitRemoteInfoTool, PullToLocalTool
from .code_run import CodeRunTool
from .tree import ListTreeTool, ListDirTool
from .classify import ClassifyContentTool
from .batch import ScanDirectoryTool, BatchClassifyTool, BatchArchiveTool

__all__ = [
    "BaseTool",
    "ToolResult",
    "ParseFileTool",
    "FirecrawlScrapeTool",
    "FirecrawlSearchTool",
    "ArchiveFileTool",
    "UpdateIndexTool",
    "SyncIndexTool",
    "SearchIndexTool",
    "ReadFileTool",
    "ListProjectsTool",
    "GitSyncTool",
    "GitStatusTool",
    "GitRemoteInfoTool",
    "PullToLocalTool",
    "CodeRunTool",
    "ListTreeTool",
    "ListDirTool",
    "ClassifyContentTool",
    "ScanDirectoryTool",
    "BatchClassifyTool",
    "BatchArchiveTool",
]
