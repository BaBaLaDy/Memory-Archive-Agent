"""ReAct Agent 引擎，基于 LangGraph create_react_agent + 流式输出"""

import asyncio
import sys
import platform
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage

from maa.agent.graph import build_agent
from maa.tools.base import BaseTool


class StreamEventType(Enum):
    TOKEN = "token"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    MODEL_START = "model_start"  # LLM 开始推理
    ERROR = "error"


@dataclass
class StreamEvent:
    """流式输出事件"""
    type: StreamEventType
    data: str | dict | None = None


class AgentEngine:
    """ReAct Agent，基于 LangGraph create_react_agent，支持流式输出"""

    def __init__(
        self,
        model: str = "qwen3.6-plus",
        api_key: str | None = None,
        api_base: str | None = None,
        categories: list[str] | None = None,
        extra_body: dict | None = None,
        storage_root: str = "",
    ):
        self.model = model
        self.categories = categories or ["projects", "research", "personal", "inbox"]
        self.storage_root = storage_root
        self._tools: list[BaseTool] = []
        self._api_key = api_key
        self._api_base = api_base
        self._extra_body = extra_body
        self._agent = None  # CompiledGraph，延迟构建

    def register_tool(self, tool: BaseTool) -> None:
        self._tools.append(tool)

    def _ensure_agent(self):
        """延迟构建 agent，确保所有工具已注册"""
        if self._agent is None:
            self._agent = build_agent(
                model=self.model,
                api_key=self._api_key,
                api_base=self._api_base,
                extra_body=self._extra_body,
                categories=self.categories,
                tools=self._tools,
                storage_root=self.storage_root,
                env_context=self._build_env_context(),
            )

    @staticmethod
    def _build_env_context() -> dict:
        """收集当前运行环境信息，注入 prompt 供 Agent 自主决策"""
        import subprocess as sp

        shell_info = "bash/zsh"
        if sys.platform == "win32":
            try:
                result = sp.run(
                    ["powershell", "-Command", "$PSVersionTable.PSVersion"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    shell_info = "CMD 和 PowerShell"
                else:
                    shell_info = "CMD"
            except Exception:
                shell_info = "CMD"

        return {
            "os_name": f"{platform.system()} {platform.release()}",
            "shell_info": shell_info,
            "python_version": sys.version.split()[0],
        }

    async def run_stream(self, user_input: str, language: str | None = None, debug: bool = False) -> AsyncGenerator[StreamEvent, None]:
        """执行一轮对话，流式产出 StreamEvent。debug=True 时输出模型消息详情。"""
        self._ensure_agent()

        if language:
            user_input += f"\n\n[System Instruction: Please respond in {language}.]"

        try:
            async for event in self._agent.astream_events(
                {"messages": [HumanMessage(content=user_input)]},
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_chat_model_start":
                    if debug:
                        yield StreamEvent(type=StreamEventType.MODEL_START, data=None)

                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        content = chunk.content
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    yield StreamEvent(type=StreamEventType.TOKEN, data=block.get("text", ""))
                        else:
                            yield StreamEvent(type=StreamEventType.TOKEN, data=str(content))
                    # debug: 显示 tool_calls 片段（模型在流式输出工具调用参数）
                    if debug and hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                        for tc in chunk.tool_call_chunks:
                            if tc.get("name"):
                                yield StreamEvent(
                                    type=StreamEventType.TOOL_START,
                                    data={"name": tc["name"], "args_hint": "(流式构建参数...)"},
                                )

                elif kind == "on_chat_model_end":
                    # debug: 显示模型最终返回的完整消息
                    if debug:
                        output = event["data"].get("output", {})
                        if hasattr(output, "tool_calls") and output.tool_calls:
                            for tc in output.tool_calls:
                                yield StreamEvent(
                                    type=StreamEventType.MODEL_START,
                                    data={"tool_call": {"name": tc.get("name"), "args": tc.get("args", {})}},
                                )

                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    try:
                        safe_input = {k: str(v)[:200] for k, v in tool_input.items()}
                    except Exception:
                        safe_input = str(tool_input)
                    yield StreamEvent(
                        type=StreamEventType.TOOL_START,
                        data={"name": tool_name, "input": safe_input},
                    )

                elif kind == "on_tool_end":
                    tool_name = event["name"]
                    output = event["data"].get("output", "")
                    # LangGraph astream_events v2 返回的 output 是 ToolMessage 对象，
                    # 需要提取 .content 才能被 JSON 序列化
                    if hasattr(output, "content"):
                        output = output.content
                    if not isinstance(output, str):
                        output = str(output)
                    yield StreamEvent(
                        type=StreamEventType.TOOL_END,
                        data={"name": tool_name, "output": output},
                    )

        except Exception as e:
            yield StreamEvent(type=StreamEventType.ERROR, data=str(e))

    def run(self, user_input: str) -> str:
        """同步执行一轮对话（兼容旧接口），返回最终文本"""
        return asyncio.run(self._run_sync(user_input))

    async def _run_sync(self, user_input: str) -> str:
        tokens: list[str] = []
        async for event in self.run_stream(user_input):
            if event.type == StreamEventType.TOKEN and isinstance(event.data, str):
                tokens.append(event.data)
        return "".join(tokens)
