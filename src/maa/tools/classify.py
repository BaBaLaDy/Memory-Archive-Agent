import json
import re
from pathlib import Path
from maa.tools.base import BaseTool, ToolResult
from maa.tools import read_file



class ClassifyContentTool(BaseTool):
    """分析内容并判断归档位置，支持跨文件夹关联"""

    name = "classify_content"
    description = (
        "分析待归档内容的语义，结合当前知识库目录树和各文件夹 .index.md 描述，"
        "判断应归档到哪个已有文件夹或建议新建文件夹。"
        "支持发现跨文件夹的语义关联（related_existing）。"
        "调用前必须先使用 list_tree 获取 tree_context。"
        "提供 source_path 时工具自己读取文件前 2000 字符（推荐，避免再调 parse_file）；"
        "或直接提供 content_summary 文本。二选一，优先 source_path。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "source_path": {
                "type": "string",
                "description": "待归档的源文件路径（推荐，工具自己读取前 2000 字符用于分类）",
            },
            "content_summary": {
                "type": "string",
                "description": "待归档内容的摘要文本（仅在无源文件时使用，如 URL 抓取结果）",
            },
            "tree_context": {
                "type": "string",
                "description": "list_tree 工具返回的目录树 JSON 字符串",
            },
            "original_filename": {
                "type": "string",
                "description": "原始文件名（优先从 source_path 自动提取）",
            },
        },
        "required": ["tree_context"],
    }

    def execute(
        self,
        tree_context: str,
        source_path: str = "",
        content_summary: str = "",
        original_filename: str = "",
    ) -> ToolResult:
        from pathlib import Path
        from maa.agent.prompt import build_classify_prompt
        from maa.agent.llm_setup import create_llm
        from maa.config import load_config

        if not tree_context.strip():
            return ToolResult(
                success=False,
                error="缺少目录树上下文：请先使用 list_tree 工具获取知识库结构，再调用 classify_content",
            )

        # 优先从源文件读取内容，统一走 MarkItDown 解析
        if source_path:
            sp = Path(source_path)
            if not sp.exists():
                return ToolResult(success=False, error=f"源文件不存在: {source_path}")
            try:
                content_summary = read_file(sp)[:2000]
            except ImportError:
                return ToolResult(success=False, error="markitdown 未安装，无法解析文件")
            except Exception as e:
                return ToolResult(success=False, error=f"文件解析失败: {str(e)}")

            if not original_filename:
                original_filename = sp.name

        if not content_summary.strip():
            return ToolResult(
                success=False,
                error="未提供内容：请提供 source_path 或 content_summary",
            )

        # 截断过长的内容
        if len(content_summary) > 2000:
            content_summary = content_summary[:2000]

        # 构建分类 prompt
        classify_prompt = build_classify_prompt(
            tree_context=tree_context,
            content_summary=content_summary,
            original_filename=original_filename,
        )

        # 创建 LLM 实例并调用
        config = load_config()
        try:
            llm = create_llm(
                model=config.llm_model,
                api_key=config.api_key if config.api_key else None,
                api_base=config.api_base if config.api_base else None,
                extra_body=config.extra_body or None,
            )
            from langchain_core.messages import HumanMessage
            response = llm.invoke([HumanMessage(content=classify_prompt)])
            raw = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            # LLM 调用失败，降级到 inbox
            return self._fallback_classification(original_filename)

        # 解析 JSON
        result = self._parse_json_response(raw)
        if result is None:
            return self._fallback_classification(original_filename)

        # 验证必填字段
        required_fields = ["target_path", "is_new_folder", "title", "tags", "category"]
        for field in required_fields:
            if field not in result:
                return ToolResult(
                    success=False,
                    error=f"分类结果缺少必填字段: {field}，原始响应: {raw[:300]}",
                )

        return ToolResult(success=True, data=result)

    @staticmethod
    def _parse_json_response(raw: str) -> dict | None:
        """解析 LLM 返回的 JSON，处理常见格式问题"""
        raw = raw.strip()
        # 尝试去掉 Markdown 代码块标记
        if raw.startswith("```"):
            # 找到第一个换行后到最后一个 ```
            lines = raw.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines)

        # 尝试提取 JSON 对象
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _fallback_classification(original_filename: str = "") -> ToolResult:
        """分类失败时的安全降级方案"""
        title = original_filename.rsplit(".", 1)[0] if original_filename else "未命名归档"
        return ToolResult(
            success=True,
            data={
                "target_path": f"inbox/{original_filename or 'untitled.md'}",
                "is_new_folder": False,
                "title": title,
                "tags": [],
                "category": "inbox",
                "project": None,
                "summary": "（自动降级：分类 LLM 调用失败，暂存 inbox）",
                "related_existing": [],
            },
        )
