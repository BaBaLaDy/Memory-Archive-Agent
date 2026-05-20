## Context

MAA Phase 1 核心引擎已稳定运行，有 CLI 交互式通道。用户的核心场景是「快速收藏」——一键归档文档、网页、剪贴板内容到个人知识库。CLI 摩擦高，需要桌面 GUI 降低捕获阻力。

Phase 2 目标：Tauri 桌面应用作为主要用户界面，通过 HTTP 与 Python MAA 后端通信。

## Goals / Non-Goals

**Goals:**
- MAA 项目新增 HTTP API Server，暴露核心能力为 REST 端点
- Tauri 桌面项目独立构建，提供三个视图（快速捕获、搜索浏览、对话 Agent）
- 全局热键 `Ctrl+Shift+M` 唤起快速捕获窗口
- 系统托盘常驻，管理 Python 进程生命周期
- `/chat` 端点支持 SSE 流式对话，与 CLI 同等能力

**Non-Goals:**
- MCP Server（Phase 2 后续，复用 HTTP 传输层）
- Tauri 自动更新、跨平台打包（先跑通 Windows）
- 文件监听、浏览器扩展（Phase 4）
- 修改 Agent 核心逻辑

## Decisions

### 1. HTTP 框架选 FastAPI

| 方案 | 流式支持 | 依赖 | 开发体验 |
|---|---|---|---|
| FastAPI + uvicorn | SSE 原生 | 需安装 | 自动文档、类型校验 |
| 内置 http.server | 手写 SSE | 无 | 简陋 |

**选 FastAPI**：`/chat` 端点需要 SSE 流式输出，FastAPI 的 `StreamingResponse` 开箱即用。自动生成 OpenAPI 文档便于调试。后续 MCP Server 的 HTTP 传输也可复用。

### 2. Tauri 作为独立项目

AMA 是 Python 项目，Tauri 是 Rust + React 项目，技术栈完全正交。独立仓库避免构建系统冲突，分别管理依赖和版本。

通信方式：Tauri 通过 `http://127.0.0.1:8899` 调 MAA Server。Tauri 侧用 Rust `Command` API 管理 Python 子进程（启动时 `python server.py`，退出时 kill）。

### 3. MAA Server 架构

```
server.py                    # 入口：FastAPI app + uvicorn 启动
src/maa/server/
├── __init__.py
├── routes.py                # REST 端点定义
└── sse.py                   # SSE 流式辅助
```

端点设计：

| 方法 | 路径 | 功能 | 备注 |
|---|---|---|---|
| POST | `/archive` | 归档内容 | body: source_path 或 content |
| GET | `/search?q=` | 搜索索引 | 返回匹配文件列表 |
| GET | `/files/{path}` | 读取文件 | path 为知识库内相对路径 |
| GET | `/tree` | 目录树 | 返回知识库结构 |
| GET | `/projects` | 项目列表 | 返回所有项目及文件数 |
| POST | `/chat` | 对话 Agent | SSE 流式返回，body: {message} |

### 4. SSE 用于流式对话

`/chat` 端点使用 Server-Sent Events 返回 Agent 流式输出。Tauri 前端用 `EventSource` 或 `fetch` + `ReadableStream` 消费。

事件格式：
```
event: token
data: 这是流式输出的一小段

event: tool_call
data: {"name": "search_index", "args": {"query": "IMU"}}

event: tool_result
data: {"name": "search_index", "output": "..."}

event: done
data:
```

### 5. Tauri 进程管理

Tauri 启动时自动 spawn Python server 进程，退出时 kill。健康检查：定期 GET `/tree`，连续失败则提示用户重启后端。

## Risks / Trade-offs

| 风险 | 缓解 |
|---|---|
| Python 进程崩溃导致桌面不可用 | 健康检查 + UI 提示重启，不丢数据 |
| 端口 8899 被占用 | 启动时检测，备选端口 8900 |
| Tauri + Rust 学习曲线 | React 前端可独立开发，Rust 只做壳 |
| Windows 路径问题（反斜杠 vs 正斜杠） | MAA Server 统一用 Path，归一化处理 |
| SSE 长连接中断 | 前端自动重连，重发最近一条消息 |

## Migration Plan

1. 在 MAA 项目安装 `fastapi` + `uvicorn` 依赖
2. 新增 `server.py` 和 `src/maa/server/` 模块
3. 无需修改现有代码，Agent 核心保持不变
4. Tauri 项目新仓库创建，通过 `npm create tauri-app` 初始化
