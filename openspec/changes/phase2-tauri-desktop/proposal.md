## Why

AMA 当前只有 CLI 通道，但用户的核心场景是「看到好内容 → 一键收藏」——快速捕获文档、网页、剪贴板内容到个人知识库。CLI 每次需要打开终端、敲路径，摩擦太高，不适合作为日常快速收藏入口。

## What Changes

- **新增 HTTP API Server**：在 MAA 项目内添加一个轻量 HTTP 服务，暴露 `/archive`、`/search`、`/chat`、`/tree`、`/files/*`、`/projects` 端点，供桌面应用调用
- **新增 Tauri 桌面应用**：独立项目，技术栈 Tauri 2.0 + React + TypeScript，通过 HTTP 与 MAA Server 通信
- **全局热键唤起**：`Ctrl+Shift+M` 弹出快速捕获窗口
- **三个视图**：快速捕获（拖拽/粘贴/链接归档）、搜索浏览（关键词搜索 + 项目浏览 + 文件阅读）、对话 Agent（流式聊天，CLI 同等能力）
- **进程管理**：Tauri 管理 Python MAA Server 的启动和退出

## Capabilities

### New Capabilities

- `http-api-server`: MAA HTTP API 服务，将 Agent 核心能力暴露为 REST 端点，支持 SSE 流式对话
- `tauri-desktop-app`: Tauri 桌面应用，包括全局热键、系统托盘、快速捕获窗口、搜索浏览、对话 Agent 三个视图

### Modified Capabilities

无（Phase 1 核心不变）

## Impact

**MAA 项目（Python）**：
- 新增 `src/maa/server.py` — HTTP API Server
- 新增依赖 `fastapi` + `uvicorn` — 用于 HTTP 服务和 SSE 流式支持
- 轻量改造 `src/maa/agent/engine.py` — 暴露流式调用的函数接口（当前只用于流式打印）

**新项目（Tauri）**：
- 新建 `memory-archive-desktop` 仓库 — Tauri + React + TypeScript
- 不与 MAA Python 项目混合，通过 localhost HTTP 通信
