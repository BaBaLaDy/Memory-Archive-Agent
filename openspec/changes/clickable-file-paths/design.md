## Context

当前桌面端（[App.tsx](desktop/src/App.tsx)）通过 SSE 接收 Agent 流式输出，在 `tool_end` 事件中解析 `search_index` 工具返回的结果来渲染文件卡片。但存在两个关键 bug：

1. **tool_end 数据格式问题**：`engine.py` 对 ToolResult 调用 `str()` 得到 Python repr 字符串（如 `ToolResult(success=True, data={...})`），前端 `JSON.parse()` 无法解析，导致 `fileResults` 永远为空
2. **搜索结果缺绝对路径**：`search_global_index` 返回的 IndexEntry 只含相对路径，前端"打开"和"定位"按钮回退到相对路径时 Electron API 无法正确打开文件

此外，LLM 文本回复中引用的文件路径（如 `` `projects/xxx/doc.md` ``）是纯文本，用户无法直接点击打开。

## Goals / Non-Goals

**Goals:**
- 修复 `tool_end` 事件中 ToolResult 的序列化，使前端能正确解析文件列表
- 搜索结果补全 `absolute_path`，确保前端"打开/定位"按钮可用
- 在 system prompt 中约定 `[file:相对路径]` 输出格式
- 前端 Markdown 渲染器识别 `[file:路径]` 并转为可点击链接

**Non-Goals:**
- 不改变 Agent 的工具调用逻辑
- 不改变 SSE 协议的整体结构
- 不新增前端依赖

## Decisions

### 决策 1：ToolResult 序列化方式

**选择**：在 [base.py](src/maa/tools/base.py) 的 `ToolResult` dataclass 中新增 `to_json()` 方法，返回合法 JSON 字符串。`engine.py` 的 `tool_end` 事件使用此方法而非 `str()`。

**替代方案**：在 engine.py 中针对每个事件类型单独处理序列化。**拒绝原因**：逻辑分散，不同工具返回不同结构时维护成本高。

### 决策 2：文件路径约定格式

**选择**：使用 `[file:相对路径]` 格式。LLM 在 system prompt 中被指示使用此格式引用文件。

**替代方案 A**：`file://绝对路径` —— **拒绝原因**：绝对路径在不同机器上不同，不便于跨设备协作；暴露本地文件系统路径。

**替代方案 B**：前端启发式正则匹配 `` `**.md` `` —— **拒绝原因**：可能漏判或误判，不精确。

**替代方案 C**：自定义 SSE 事件类型 `file_results` —— **未选但保留**：这是更彻底的方案，但涉及前后端协议变更。当前阶段优先最小修改，后续可演进至此方案。

### 决策 3：absolute_path 的生成位置

**选择**：在 `search_index` 和 `read_file` 工具中生成 `absolute_path`，由工具直接补充到返回数据中。工具内部通过 `RepoManager.resolve_path()` 将相对路径转为绝对路径。

**替代方案**：在 `tool_end` 事件处理时由 engine 统一补全。**拒绝原因**：engine 不应感知存储细节，工具层更自然。

### 决策 4：前端打开文件的实现

**选择**：前端检测到 `[file:路径]` 时渲染为 `<a>` 标签，点击时调用 `electronAPI.openPath(absolutePath)`。`absolutePath` 由前端拼接（已知 storageRoot + 相对路径），或者后端在搜索结果中已提供。

**替代方案**：前端发送 `/resolve-path?rel=xxx` 请求获取绝对路径。**拒绝原因**：增加一次网络往返，搜索结果已经带了 `absolute_path`，无需额外请求。

## Risks / Trade-offs

- **[低风险] Prompt 膨胀**：system prompt 增加 `[file:]` 约定，增加约 3-5 行文本。影响很小
- **[低风险] LLM 不遵循格式**：部分 LLM 可能忽略 `[file:]` 格式。缓解：前端同时保留启发式正则匹配作为 fallback
- **[无风险] 向后兼容**：`ToolResult.to_json()` 是新增方法，不影响现有 `str()` 调用
