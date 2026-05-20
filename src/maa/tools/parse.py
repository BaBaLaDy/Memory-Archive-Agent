import os
from pathlib import Path

from .base import BaseTool, ToolResult
from maa.tools import read_file


class ParseFileTool(BaseTool):
    """解析本地文件内容 (基于 MarkItDown)"""

    name = "parse_file"
    description = "提取本地文件（.md, .txt, .pdf, .docx, .xlsx, .pptx 等）的文本内容和元信息，将其转换为 Markdown 格式"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "要解析的文件路径"},
        },
        "required": ["file_path"],
    }

    # MarkItDown 支持的格式极其广泛
    SUPPORTED_EXTENSIONS = {
        ".md", ".txt", ".csv", ".json", ".xml", ".html", 
        ".pdf", ".docx", ".xlsx", ".pptx",
        ".png", ".jpg", ".jpeg"  # 如果配置了 LLM，甚至可以做图片 OCR，这里作为备用
    }

    def execute(self, file_path: str) -> ToolResult:
        path = Path(file_path)
        if not path.exists():
            return ToolResult(success=False, error=f"文件不存在: {file_path}")

        ext = path.suffix.lower()
        try:
            content = read_file(path)
            return ToolResult(
                success=True,
                data={
                    "content": content,
                    "filename": path.name,
                    "type": ext,
                    "size": os.path.getsize(path),
                },
            )
        except ImportError:
            return ToolResult(success=False, error="markitdown 未安装，请运行 pip install markitdown")
        except Exception as e:
            return ToolResult(success=False, error=f"文件解析失败: {str(e)}")


