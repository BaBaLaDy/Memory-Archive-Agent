"""BaseTool 到 LangChain StructuredTool 适配器"""

import json
from typing import Any

from pydantic import BaseModel, Field, create_model, BeforeValidator
from typing_extensions import Annotated

from langchain_core.tools import StructuredTool

from maa.tools.base import BaseTool, ToolResult


def _json_type_to_python(json_type: str) -> type:
    """JSON Schema 类型 → Python 类型映射"""
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
    }
    return mapping.get(json_type, str)


def _coerce_json_string(value: Any) -> Any:
    """如果值是 JSON 字符串则解析为原生类型，否则原样返回。
    修复 Qwen 等模型将 array/object 参数序列化为 JSON 字符串的问题。
    """
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if (stripped.startswith("[") and stripped.endswith("]")) or \
       (stripped.startswith("{") and stripped.endswith("}")):
        try:
            return json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            pass
    return value


def _build_args_schema(tool_name: str, parameters: dict) -> type[BaseModel]:
    """从 JSON Schema parameters 动态创建 Pydantic BaseModel"""
    properties = parameters.get("properties", {})
    required = set(parameters.get("required", []))

    fields: dict[str, tuple[type, Any]] = {}
    for prop_name, prop_schema in properties.items():
        prop_type_str = prop_schema.get("type", "string")
        description = prop_schema.get("description", "")

        if prop_type_str == "array":
            items = prop_schema.get("items", {})
            item_type_str = items.get("type", "string")
            inner_type = _json_type_to_python(item_type_str)
            python_type = Annotated[list[inner_type], BeforeValidator(_coerce_json_string)]
        elif prop_type_str == "object":
            python_type = Annotated[dict, BeforeValidator(_coerce_json_string)]
        else:
            python_type = _json_type_to_python(prop_type_str)

        if prop_name in required:
            fields[prop_name] = (python_type, Field(description=description))
        else:
            fields[prop_name] = (python_type | None, Field(default=None, description=description))

    model_name = f"{tool_name}_args"
    return create_model(model_name, **fields)


def adapt_base_tool(base_tool: BaseTool) -> StructuredTool:
    """将 AMA BaseTool 转换为 LangChain StructuredTool，带完整的 args_schema"""

    args_schema = _build_args_schema(base_tool.name, base_tool.parameters)

    def _execute(**kwargs) -> str:
        result: ToolResult = base_tool.execute(**kwargs)
        return result.to_json()

    _execute.__name__ = base_tool.name

    return StructuredTool.from_function(
        func=_execute,
        name=base_tool.name,
        description=base_tool.description,
        args_schema=args_schema,
    )
