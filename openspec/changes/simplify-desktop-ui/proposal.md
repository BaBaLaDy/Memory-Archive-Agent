## Why

当前桌面前端有三个独立标签页（快速捕获、搜索浏览、对话 Agent），每个页面有自己的输入逻辑和状态管理，前端参与了过多的归档/搜索逻辑。实际上 Agent 已经具备处理所有这些操作的能力，前端应该只作为统一的输入输出终端，类似 Google 搜索框——用户只需表达意图，Agent 完成剩余工作。

## What Changes

- 将三个标签页合并为单一视图，仅包含一个通用输入框和两个输出区域（上方回答区、下方结果区）
- 所有用户输入（打字、拖拽文件、粘贴路径）统一通过 `/chat` SSE 接口发送给 Agent
- 前端不再直接调用 `/archive` 或 `/search` 接口，这两个接口保留给未来 MCP 使用
- 输入框支持拖拽 PDF/MD 等文件，通过 Electron API 获取真实文件路径（非文件内容）传给 Agent
- 前端根据 SSE 事件类型分流渲染：`token` → 上方 markdown 回答区，`tool_end`（search_index）→ 下方文件结果列表
- 每次交互无状态，关闭窗口后对话历史丢弃
- 增强 Electron preload，暴露 `getFilePath`、`openPath`、`showItemInFolder` 三个 API

## Capabilities

### New Capabilities

- `unified-input-bar`: 单一通用输入框，支持多行文本输入、文件拖拽、粘贴，Enter 发送 / Shift+Enter 换行，文件以 chip 形式显示并可移除
- `agent-driven-workflow`: 前端不再区分归档/搜索/对话三种模式，所有输入统一发给 Agent，由 Agent 自主判断意图并调用对应工具
- `dual-zone-output`: 上方区域渲染 Agent 的 markdown 回答（归档确认、知识问答），下方区域渲染文件搜索结果（可点击预览/打开/定位）

### Modified Capabilities

（无现有 spec 需修改）

## Impact

- 前端：废弃 CaptureView / SearchView / ChatView 三个组件，新建 MainView + InputBar + AnswerPanel + ResultPanel
- Electron：preload.cjs 新增 getFilePath / openPath / showItemInFolder API
- 后端：`/chat` 接口无需改动，`/archive` 和 `/search` 保留不动
