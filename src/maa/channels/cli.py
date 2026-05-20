import asyncio
import sys

from maa.channels.base import ChannelAdapter, AgentInput
from maa.agent.engine import AgentEngine, StreamEventType
from maa.config import load_config, validate_config
from maa.storage.repo import RepoManager
from maa.tools.parse import ParseFileTool
from maa.tools.firecrawl import FirecrawlScrapeTool, FirecrawlSearchTool
from maa.tools.archive import ArchiveFileTool, UpdateIndexTool, SyncIndexTool
from maa.tools.search import SearchIndexTool, ReadFileTool, ListProjectsTool
from maa.tools.sync import GitSyncTool, GitStatusTool, GitRemoteInfoTool, PullToLocalTool
from maa.tools.code_run import CodeRunTool
from maa.tools.tree import ListTreeTool, ListDirTool
from maa.tools.classify import ClassifyContentTool
from maa.tools.batch import ScanDirectoryTool, BatchClassifyTool, BatchArchiveTool


class CLIChannel(ChannelAdapter):
    """CLI 交互式通道"""

    def receive(self, raw_input) -> AgentInput:
        return AgentInput(text=raw_input)

    def send(self, agent_output: str) -> None:
        print(f"\n{agent_output}\n")

    def send_file(self, file_path: str) -> None:
        print(f"[文件] {file_path}")


def create_engine(config) -> AgentEngine:
    """创建并注册所有工具的 Agent 引擎"""
    engine = AgentEngine(
        model=config.llm_model,
        api_key=config.api_key if config.api_key else None,
        api_base=config.api_base if config.api_base else None,
        extra_body=config.extra_body or None,
        categories=config.categories,
        storage_root=config.storage_root,
    )

    tools = [
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
    for tool in tools:
        engine.register_tool(tool)

    return engine


async def run_repl(config_path: str | None = None) -> None:
    """启动 CLI 交互式 REPL（异步，支持流式输出）"""
    config = load_config(config_path)
    errors = validate_config(config)
    if errors:
        print("配置错误：")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    # 确保仓库已初始化
    repo = RepoManager(config.storage_root)
    repo.ensure_initialized()

    channel = CLIChannel()
    engine = create_engine(config)

    print("=" * 50)
    print("  Memory Archive Agent (MAA) - CLI")
    print("  输入 'quit', 'exit' 或 'q' 退出")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        if not user_input:
            continue

        print()  # 空行，准备流式输出
        try:
            async for event in engine.run_stream(user_input, debug=True):
                if event.type == StreamEventType.TOKEN:
                    print(event.data, end="", flush=True)
                elif event.type == StreamEventType.MODEL_START:
                    d = event.data
                    if d and "tool_call" in d:
                        tc = d["tool_call"]
                        print(f"\n[模型决定调用: {tc['name']}({tc['args']})]", flush=True)
                    else:
                        print("\n[模型思考中...]", flush=True)
                elif event.type == StreamEventType.TOOL_START:
                    d = event.data
                    if d and "args_hint" in d:
                        print(f"\n[调用工具: {d['name']}]", flush=True)
                    else:
                        args = d.get("input", {}) if d else {}
                        args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                        print(f"\n[调用工具: {d['name']}({args_str})]", flush=True)
                elif event.type == StreamEventType.TOOL_END:
                    d = event.data
                    output = d.get("output", "") if d else ""
                    status = "✓" if "错误" not in output else "✗"
                    print(f"[{status} 工具完成: {d['name']}]", flush=True)
                    if output:
                        # 显示工具返回的关键信息
                        print(f"  => {output[:500]}", flush=True)
                elif event.type == StreamEventType.ERROR:
                    print(f"\n[错误: {event.data}]", flush=True)
            print()  # 回复结束换行
        except Exception as e:
            channel.send(f"错误: {e}")
