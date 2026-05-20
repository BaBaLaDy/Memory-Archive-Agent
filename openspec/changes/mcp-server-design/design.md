## Context

MAA 项目已有完整的 ReAct Agent 引擎（基于 LangGraph）和 17 个工具，通过 CLI、HTTP API（FastAPI）、Electron 桌面三个通道提供服务。当前的通道架构采用 `ChannelAdapter` 模式，新增通道只需实现 `receive/send/send_file` 三方法即可接入 Agent 核心。

MCP（Model Context Protocol）是 Anthropic 推出的 AI 工具间标准化协议，支持 stdio 和 HTTP 两种传输方式。MCP Python SDK 提供了 `FastMCP` 类，可以便捷地注册工具和资源。

现有 `config.json` 中已有 `channels.mcp` 配置占位（`enabled: false, port: 3000`），但未实现。

## Goals / Non-Goals

**Goals:**
- 通过 MCP 协议暴露 MAA 的核心能力（搜索、归档、读取、对话）
- 复用已有的 `AgentEngine` 和工具集，不重复实现业务逻辑
- 支持 stdio（Claude Code 等本地集成）和 HTTP（远程调用）两种传输模式
- 遵循现有 `ChannelAdapter` 架构模式

**Non-Goals:**
- 不暴露所有 17 个工具（仅暴露最核心的 5 个 MCP 工具）
- 不修改 Agent 引擎或已有工具实现
- 不实现 Feishu / Telegram 通道
- 不改变桌面应用状态

## Decisions

### 1. MCP 工具选择：精简暴露 5 个核心工具

**决策**: 不暴露全部 17 个工具，仅暴露 `search_index`、`archive_file`、`read_file`、`list_projects`、`chat` 五个。

**理由**: MCP 客户端（如 Claude Code）通常只需要核心能力。过多的工具会增加协议复杂度和 LLM 决策负担。这 5 个工具覆盖了「查、写、读、管理、对话」的完整闭环。其余工具（如 git_sync、batch_*、code_run）属于运维/高级功能，仍通过 CLI 通道使用。

**备选方案**:
- 方案 A: 暴露全部 17 个工具 — 过于臃肿，违背 MCP 精简哲学
- 方案 B: 只暴露 search 和 chat — 功能不完整，无法归档

### 2. 传输模式: stdio + HTTP 双模式

**决策**: 同时支持 stdio 和 HTTP 两种 MCP 传输模式，通过配置项 `channels.mcp.transport` 切换。

**理由**: stdio 模式是 MCP 本地集成的标准方式（Claude Code 通过 stdio 连接），HTTP 模式支持远程调用和现有 FastAPI 服务器复用。

**实现方式**:
- stdio 模式: 使用 `mcp.server.fastmcp.FastMCP` 的 `run(transport="stdio")`
- HTTP 模式: 使用 FastMCP 的 HTTP 传输层，挂载到独立端口或复用现有 FastAPI 应用

### 3. 架构: MCP Server 作为独立通道，复用 AgentEngine

**决策**: MCP Server 不作为 HTTP API 的子模块，而是独立的通道适配器（`channels/mcp.py`），内部创建自己的 `AgentEngine` 实例并复用工具注册逻辑。

**理由**:
- 遵循现有通道解耦原则：每个通道独立管理生命周期
- CLI 通道已有 `create_engine()` 工厂函数，MCP 通道可直接复用
- HTTP API 的 `server/routes.py` 也是独立创建 engine，模式一致

**文件结构**:
```
src/maa/channels/mcp.py
├── MCPChannel(ChannelAdapter)    # 通道适配器（保留接口一致性）
├── create_mcp_server()           # 创建 FastMCP 实例，注册 5 个工具
├── mcp_tool_search()             # MCP 工具函数: search_index
├── mcp_tool_archive()            # MCP 工具函数: archive_file
├── mcp_tool_read()               # MCP 工具函数: read_file
├── mcp_tool_projects()           # MCP 工具函数: list_projects
├── mcp_tool_chat()               # MCP 工具函数: chat (流式)
└── run_mcp_server()              # 入口函数
```

### 4. 依赖: 使用官方 MCP Python SDK

**决策**: 使用 `mcp`（`pip install mcp`）官方 SDK，不自建协议实现。

**理由**: 官方 SDK 提供了 `FastMCP` 高级封装，自动处理工具注册、参数校验、JSON-RPC 协议、stdio/HTTP 传输层切换。自建实现会增加维护负担且容易与官方生态不兼容。

### 5. chat 工具: 同步响应而非流式

**决策**: MCP 的 `chat` 工具返回完整文本响应，不使用 SSE 流式。

**理由**: MCP 协议的工具调用是 request-response 模式，不支持服务端推送流式数据。如果需要流式对话，客户端应通过多次调用或使用 MCP 的 Streamable HTTP 传输（SDK 支持）。首期实现采用简单同步模式，后续可扩展。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| MCP SDK 版本迭代快，API 可能变化 | 锁定 `mcp` 版本号到 pyproject.toml，定期升级测试 |
| stdio 模式下 engine 初始化较慢 | 在 `run_mcp_server()` 启动时预初始化 engine，而非首次调用时懒加载 |
| HTTP 模式端口与现有 FastAPI (8899) 冲突 | 配置默认端口 3000，与现有服务完全独立 |
| 工具参数设计与 LLM 期望不匹配 | MCP 工具参数尽量与已有 Agent 工具参数保持一致，利用 LLM 已有的调用经验 |
| 多个通道同时创建多个 AgentEngine 实例，内存占用增加 | 每个通道独立 engine 是已有模式（CLI 和 HTTP 已是如此），内存增加可接受 |
