import os
import json
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolResult


class ScanDirectoryTool(BaseTool):
    """扫描文件夹以提取待归档文件的元数据和摘要（批量处理第一步）"""

    name = "scan_directory"
    description = (
        "扫描目标文件夹，提取支持的文档文件（.md, .txt, .pdf, .docx, .xlsx, .pptx 等）的列表、大小，"
        "并读取前 1000 个字符的摘要，生成 JSON 列表，供 batch_classify 使用。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "directory_path": {"type": "string", "description": "要扫描的本地绝对或相对文件夹路径"},
            "max_files": {"type": "integer", "description": "最多扫描的文件数，默认 100", "default": 100},
        },
        "required": ["directory_path"],
    }

    def execute(self, directory_path: str, max_files: int = 100) -> ToolResult:
        from maa.tools.parse import ParseFileTool
        
        target_dir = Path(directory_path)
        if not target_dir.exists() or not target_dir.is_dir():
            return ToolResult(success=False, error=f"目标文件夹不存在或不是目录: {directory_path}")

        parser = ParseFileTool()
        scanned_files = []
        
        for file_path in target_dir.rglob("*"):
            if not file_path.is_file():
                continue
                
            # Skip hidden files/directories
            if any(part.startswith(".") for part in file_path.parts):
                continue
                
            if file_path.suffix.lower() not in parser.SUPPORTED_EXTENSIONS:
                continue

            if len(scanned_files) >= max_files:
                break

            parse_res = parser.execute(str(file_path))
            if parse_res.success and "content" in parse_res.data:
                content = parse_res.data["content"]
                snippet = content[:1000] + ("..." if len(content) > 1000 else "")
                scanned_files.append({
                    "source_path": str(file_path.absolute()),
                    "filename": file_path.name,
                    "type": parse_res.data["type"],
                    "size": parse_res.data["size"],
                    "snippet": snippet
                })
            else:
                scanned_files.append({
                    "source_path": str(file_path.absolute()),
                    "filename": file_path.name,
                    "error": parse_res.error or "解析失败"
                })

        return ToolResult(
            success=True, 
            data={
                "directory": str(target_dir.absolute()),
                "total_scanned": len(scanned_files),
                "files": scanned_files
            }
        )


class BatchClassifyTool(BaseTool):
    """批量分类规划工具（批量处理第二步）"""

    name = "batch_classify"
    description = (
        "对扫描出的文件列表进行批量分类规划。结合当前目录树，将文件映射到相应的归档路径。"
        "LLM 将自动识别相似或重复文件，并在目标路径(target_path)和标题(title)中添加后缀进行区分，无需用户干预。"
        "必须先使用 list_tree 获得 tree_context，以及 scan_directory 获得 scanned_files_json。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "scanned_files_json": {
                "type": "string", 
                "description": "scan_directory 返回的 JSON 字符串（通常包含多条文件摘要）"
            },
            "tree_context": {
                "type": "string",
                "description": "list_tree 返回的当前知识库目录树"
            },
        },
        "required": ["scanned_files_json", "tree_context"],
    }

    def execute(self, scanned_files_json: str, tree_context: str) -> ToolResult:
        from maa.agent.llm_setup import create_llm
        from maa.config import load_config
        from langchain_core.messages import HumanMessage

        if not tree_context.strip():
            return ToolResult(success=False, error="缺少目录树上下文：请先使用 list_tree 获取知识库结构")

        try:
            files_data = json.loads(scanned_files_json)
        except json.JSONDecodeError:
            return ToolResult(success=False, error="scanned_files_json 格式错误，无法解析为 JSON")

        # 构造 prompt
        prompt = f"""
你是一个专业的文件整理助手。请根据当前的知识库目录树，为以下一批新文档制定归档计划。

当前知识库目录树：
```
{tree_context}
```

待归档文档列表（含摘要）：
```json
{json.dumps(files_data, ensure_ascii=False, indent=2)}
```

**任务与规则：**
1. 仔细阅读每个文档的 snippet，判断其应归档到哪个已有的文件夹。如果没有合适的，可以建议在根目录下创建新文件夹。
2. 目标路径 `target_path` 必须包含扩展名，并且是相对存储根目录的路径（如 `projects/alpha/design.md`）。
3. **重要：自动去重与后缀处理**。如果发现多个文档内容相似或将要分配到相同的 `target_path`：
   - 你**必须**在 `target_path` 的文件名和 `title` 中自动添加区分后缀（例如 `-v1`, `-v2`, `-part1`, `-草稿` 等）。
   - 不要把决策交给用户，你直接决定最终唯一的 `target_path`。
4. 请以 JSON 数组格式返回结果，**仅输出 JSON，不要输出任何额外的解释**。格式如下：

[
  {{
    "source_path": "源文件绝对路径",
    "target_path": "相对知识库根目录的目标路径，带后缀区分",
    "title": "文档标题（也可以带后缀）",
    "category": "归档类别(如 projects, inbox 等)",
    "tags": ["tag1", "tag2"]
  }}
]
"""
        config = load_config()
        try:
            llm = create_llm(
                model=config.llm_model,
                api_key=config.api_key if config.api_key else None,
                api_base=config.api_base if config.api_base else None,
                extra_body=config.extra_body or None,
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            raw = response.content if hasattr(response, "content") else str(response)
            
            # 清理 markdown code block
            raw = raw.strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
                
            plan = json.loads(raw.strip())
            return ToolResult(success=True, data={"plan": plan})
            
        except Exception as e:
            return ToolResult(success=False, error=f"批量分类规划失败: {str(e)}")


class BatchArchiveTool(BaseTool):
    """批量归档执行工具（批量处理第三步）"""

    name = "batch_archive"
    description = "接收 batch_classify 生成的 JSON 规划，一键执行归档和索引更新。"
    parameters = {
        "type": "object",
        "properties": {
            "plan_json": {
                "type": "string",
                "description": "batch_classify 返回的 plan JSON 数组字符串"
            }
        },
        "required": ["plan_json"],
    }

    def execute(self, plan_json: str) -> ToolResult:
        from maa.tools.archive import ArchiveFileTool
        
        try:
            plan = json.loads(plan_json)
        except json.JSONDecodeError:
            return ToolResult(success=False, error="plan_json 格式错误，无法解析为 JSON")
            
        if not isinstance(plan, list):
            return ToolResult(success=False, error="plan 必须是 JSON 数组")

        archiver = ArchiveFileTool()
        results = []
        success_count = 0
        
        for item in plan:
            source = item.get("source_path")
            target = item.get("target_path")
            title = item.get("title")
            
            if not source or not target or not title:
                results.append({"source": source, "error": "缺少 source_path, target_path 或 title"})
                continue
                
            res = archiver.execute(
                target_path=target,
                title=title,
                source_path=source,
                tags=item.get("tags", []),
                category=item.get("category", "inbox"),
                project=item.get("project")
            )
            
            if res.success:
                success_count += 1
                results.append({"source": source, "target": target, "status": "success", "detail": res.data})
            else:
                results.append({"source": source, "target": target, "status": "failed", "error": res.error})
                
        # 执行批量归档后，可建议用户使用 sync_index 工具来更新全局索引，或者直接调用
        return ToolResult(
            success=True,
            data={
                "total": len(plan),
                "success": success_count,
                "failed": len(plan) - success_count,
                "details": results,
                "message": "归档完成。建议使用 sync_index 工具同步知识库索引。"
            }
        )
