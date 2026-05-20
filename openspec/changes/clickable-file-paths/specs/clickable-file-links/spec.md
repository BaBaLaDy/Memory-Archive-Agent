## ADDED Requirements

### Requirement: 文件路径可点击打开

系统 SHALL 在 LLM 文本回复中识别 `[file:相对路径]` 格式的文件引用，并将其渲染为可点击的链接。用户点击链接时，系统 SHALL 通过 Electron API 打开该文件。

#### Scenario: 回复中包含单个文件引用
- **WHEN** LLM 回复包含 `[file:projects/my-agent/设计文档.md]`
- **THEN** 前端将该文本渲染为可点击的链接，显示为 `设计文档.md`
- **THEN** 用户点击后，Electron 使用系统默认程序打开该文件的绝对路径

#### Scenario: 回复中包含多个文件引用
- **WHEN** LLM 回复包含多个 `[file:路径1]` 和 `[file:路径2]`
- **THEN** 每个引用独立渲染为可点击链接

#### Scenario: 回复中无文件引用
- **WHEN** LLM 回复不包含任何 `[file:...]` 标记
- **THEN** 文本正常渲染，无异常行为

### Requirement: 结构化文件卡片正常渲染

系统 SHALL 正确解析 `search_index` 工具的返回结果，渲染文件卡片（含预览、打开、定位按钮）。文件卡片 SHALL 包含 `absolute_path` 以确保按钮可用。

#### Scenario: 搜索返回多个文件
- **WHEN** Agent 调用 `search_index` 并返回 3 个匹配文件
- **THEN** 前端展示 3 张文件卡片，每张显示标题、相对路径、标签
- **THEN** 每张卡片的"打开"按钮可正确打开文件
- **THEN** 每张卡片的"定位"按钮可在文件管理器中定位文件
- **THEN** 每张卡片的"预览"按钮可展开显示文件前 2000 字符

#### Scenario: 搜索无结果
- **WHEN** Agent 调用 `search_index` 返回空结果
- **THEN** 前端不展示文件卡片区域

### Requirement: ToolResult 正确序列化为 JSON

系统 SHALL 在 SSE `tool_end` 事件中将 ToolResult 数据序列化为合法 JSON，使前端可可靠解析。

#### Scenario: 工具执行成功
- **WHEN** 任意工具执行成功返回 ToolResult(success=True, data={...})
- **THEN** SSE `tool_end` 事件的 data 字段为合法 JSON 字符串 `{"success": true, "data": {...}}`

#### Scenario: 工具执行失败
- **WHEN** 任意工具执行失败返回 ToolResult(success=False, error="...")
- **THEN** SSE `tool_end` 事件的 data 字段为合法 JSON 字符串 `{"success": false, "error": "..."}`
