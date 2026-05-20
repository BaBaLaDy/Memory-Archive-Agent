"""LangGraph Agent 图构建 -- 使用 create_react_agent"""

from langgraph.prebuilt import create_react_agent

from maa.agent.llm_setup import create_llm
from maa.agent.prompt import build_system_prompt
from maa.agent.tool_adapter import adapt_base_tool
from maa.tools.base import BaseTool


def build_agent(
    model: str,
    api_key: str | None,
    api_base: str | None,
    extra_body: dict | None,
    categories: list[str],
    tools: list[BaseTool],
    storage_root: str = "",
    env_context: dict | None = None,
):
    """构建并返回编译好的 LangGraph ReAct Agent"""
    llm = create_llm(model, api_key, api_base, extra_body)
    lc_tools = [adapt_base_tool(t) for t in tools]

    tool_defs = [t.to_definition() for t in tools]
    system_prompt = build_system_prompt(tool_defs, categories, storage_root, env_context)

    return create_react_agent(
        model=llm,
        tools=lc_tools,
        prompt=system_prompt,
        version="v1",  # v1 兼容性更好，v2 的 Send API 在 Qwen 上可能导致循环
    )
