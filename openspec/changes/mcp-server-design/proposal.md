## Why

当前项目已有 CLI、HTTP API、Electron 桌面三个通道，但缺少让外部 AI 工具（Claude Code、Cursor 等）直接访问长期记忆的能力。MCP（Model Context Protocol）是 AI 工具间标准化上下文交换的协议，实现 MCP Server 通道后，任何支持 MCP 的客户端都能将 MAA 作为持久知识层调用，大幅扩展项目的使用场景。

## What Changes

- 新增 `channels/mcp.py`，实现 MCP Server 通道，遵循现有 `ChannelAdapter` 模式
- 暴露 5 个 MCP 工具：`search_index`、`archive_file`、`read_file`、`list_projects`、`chat`（SSE 流式对话）
- 复用已有的 `AgentEngine` 和工具集，不重复实现业务逻辑
- 配置文件 `config.json` 中 `channels.mcp` 从 `enabled: false` 改为可配置启用
- 支持 stdio 和 HTTP 两种 MCP 传输模式

## Capabilities

### New Capabilities

- `mcp-server`: MCP Server 通道，提供标准 MCP 协议接口，暴露搜索、归档、读取、项目列表、对话能力
- `mcp-tool-definitions`: MCP 工具定义规范，描述每个 MCP 工具的参数、返回值、调用约束

### Modified Capabilities

<!-- 无已有需求变更 -->

## Impact

- **涉及文件**: `src/maa/channels/mcp.py`（新建）、`src/maa/config.py`（支持 MCP 配置读取）、`config.json`（默认启用配置）
- **涉及模块**: channels 层（新增 MCP 通道适配器）、server 层（可选复用 HTTP 传输）
- **依赖**: 新增 `mcp` Python SDK（`pip install mcp`）
- **API 影响**: 不影响已有 CLI / HTTP API / 桌面端接口
- **存储影响**: 不涉及存储结构变更

## 目标

- 外部 MCP 客户端能通过标准协议调用 MAA 的搜索、归档、对话能力
- 复用已有 AgentEngine，不重复实现业务逻辑
- 支持 stdio（本地集成）和 HTTP（远程调用）两种传输模式

## 非目标

- 不修改 Agent 核心引擎或已有工具实现
- 不重构现有通道架构
- 不实现 Feishu / Telegram 通道（Phase 3）
- 不改变 Tauri 桌面应用状态
