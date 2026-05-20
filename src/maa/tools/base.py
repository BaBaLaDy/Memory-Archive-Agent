import json
from dataclasses import dataclass


@dataclass
class ToolResult:
    """工具执行的标准化结果"""
    success: bool
    data: str | dict | list | None = None
    error: str = ""

    def to_json(self) -> str:
        """序列化为合法 JSON 字符串，供前端解析"""
        payload = {"success": self.success}
        if self.data is not None:
            payload["data"] = self.data
        if self.error:
            payload["error"] = self.error
        return json.dumps(payload, ensure_ascii=False)


class BaseTool:
    """所有工具的基类"""

    name: str = ""
    description: str = ""
    parameters: dict = {}

    def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError

    def to_definition(self) -> dict:
        """格式化为 OpenAI/LiteLLM 标准的 tool definition"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
