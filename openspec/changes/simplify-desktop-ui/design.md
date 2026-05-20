## Context

当前前端有三个独立标签页（CaptureView / SearchView / ChatView），各自维护输入逻辑和状态。目前端需要简化为单一通用输入终端，所有意图判断交给 Agent 处理。

后端已有完备的 `/chat` SSE 接口（token / tool_start / tool_end 事件流），以及 `/files/{path}` 文件读取接口。前端无需新增后端端点，只需在现有基础上做智能渲染。

## Goals / Non-Goals

**Goals:**
- 将三标签页合并为单一视图 MainView，只有一个通用输入框
- 输入框支持多行文本 + 文件拖拽（获取真实路径，非内容）
- 前端统一通过 `/chat` SSE 与 Agent 交互，不再直接调 `/archive` / `/search`
- 根据 SSE 事件分流渲染：上方 markdown 回答区 + 下方文件结果列表
- 每次交互无状态，关闭窗口丢弃对话
- 文件卡片支持预览（内联展开）、打开（系统默认程序）、定位（文件管理器）

**Non-Goals:**
- 不修改后端 `/chat` SSE 协议
- 不删除 `/archive` / `/search` 端点（保留给 MCP 使用）
- 不支持对话历史持久化
- 不引入新的 npm 依赖

## Decisions

### 1. 组件拆分

```
desktop/src/
├── App.tsx                  # 修改：去掉 tab，直接渲染 MainView
├── views/
│   └── MainView.tsx         # 新增：唯一视图，编排三个区域
└── components/
    ├── InputBar.tsx         # 新增：textarea + 文件 chip + 拖拽处理
    ├── AnswerPanel.tsx      # 新增：markdown 渲染回答（上方）
    └── ResultPanel.tsx      # 新增：文件卡片列表（下方）
```

旧组件 CaptureView / SearchView / ChatView 全部删除。

### 2. SSE 事件分流（核心设计）

前端不新增 SSE 事件类型，利用现有 `tool_end` 中的 `name` 字段分流：

| SSE 事件 | 前端行为 |
|---------|---------|
| `token` | 累积文本 → AnswerPanel 渲染 markdown |
| `tool_start` | 显示工具状态指示（"🔍 搜索中..."） |
| `tool_end` name=`search_index` | 解析 `output.results` → ResultPanel 文件列表 |
| `tool_end` name=`archive_file` | 显示归档成功确认 → AnswerPanel |
| `tool_end` 其他 | 仅显示工具状态指示 |
| `done` | 结束 loading 状态 |

### 3. 文件路径获取

Electron 29+ 提供 `webUtils.getPathForFile(file)` API，在 preload 中暴露：

```js
// preload.cjs 新增
const { webUtils, shell } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  isElectron: true,
  getFilePath: (file) => webUtils.getPathForFile(file),
  openPath: (path) => shell.openPath(path),
  showItemInFolder: (path) => shell.showItemInFolder(path),
});
```

拖入文件 → `window.electronAPI.getFilePath(file)` → 获得绝对路径 → 显示 chip → 发送时拼入消息。

### 4. 消息构造

- 有文件附件：`"请归档文件 {绝对路径}\n{用户输入文本}"`
- 无文件附件：直接发送用户输入原文
- Agent 自主判断是归档、搜索还是问答

### 5. 文件卡片操作

三个按钮，分别调用：

- **预览**：`GET /files/{相对路径}` 获取内容，内联展开渲染
- **打开**：`electronAPI.openPath(绝对路径)` 系统默认程序打开  
- **定位**：`electronAPI.showItemInFolder(绝对路径)` 资源管理器定位

绝对路径获取方式：修改 `ReadFileTool` 的返回数据，在 `/files/{path}` 响应中增加 `absolute_path` 字段。

### 6. 状态管理

MainView 维护的状态：

```ts
attachedFile: {name, path} | null   // 拖入的文件 chip
answer: string                       // 上方 markdown 累积
fileResults: FileResult[]            // 下方文件列表
loading: boolean                     // 是否等待 Agent 响应
toolStatus: string                   // 当前工具状态文案
```

每次发送新消息时清空 `answer` 和 `fileResults`（无状态交互）。

## Risks / Trade-offs

- **Electron webUtils 兼容性**：`webUtils.getPathForFile` 需要 Electron 29+，当前安装的 Electron 33 满足。Risk → 低。
- **Agent 准确度依赖**：用户输入意图判断完全依赖 Agent LLM，如果 Agent 误判（把"找文件"当成"聊天"），体验会下降。Mitigation → Agent system prompt 中明确指示判断规则。
- **文件路径跨平台**：Windows 和 macOS 路径格式不同，但 Electron `webUtils` 和 Node.js `path` 已处理跨平台差异。
- **大文件拖拽**：只传路径给 Agent，不读文件内容，所以文件大小不影响前端性能。Agent 侧的 parse_file 工具处理大文件可能较慢，但不阻塞前端。
