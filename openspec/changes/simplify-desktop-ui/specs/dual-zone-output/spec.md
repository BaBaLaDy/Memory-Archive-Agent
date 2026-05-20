## ADDED Requirements

### Requirement: 上方回答区渲染 Agent markdown
系统 SHALL 在输入框上方区域渲染 Agent 的文本回答，支持 markdown 格式（标题、列表、代码块、链接等）。

#### Scenario: Agent 回答时流式渲染
- **WHEN** Agent 通过 SSE 发送 `token` 事件
- **THEN** 每个 token 内容累积到上方回答区，实时以 markdown 格式渲染

#### Scenario: Agent 回答包含代码块
- **WHEN** Agent 回答中包含 markdown 代码块（```...```）
- **THEN** 回答区正确渲染代码块，含语法高亮

#### Scenario: 新消息清除旧回答
- **WHEN** 用户发送新消息
- **THEN** 上方回答区清空，准备展示新回答

### Requirement: 下方结果区渲染文件列表
系统 SHALL 在输入框下方渲染文件搜索结果列表，每个文件以卡片形式展示，包含文件名、路径和操作按钮。

#### Scenario: 搜索到文件时显示卡片列表
- **WHEN** Agent 的 `tool_end` 事件中 tool name 为 `search_index` 且 output 包含 results
- **THEN** 下方渲染文件卡片列表，每张卡片显示：文件名、相对路径、标签

#### Scenario: 无搜索结果时显示空状态
- **WHEN** Agent 返回 search_index 结果中 results 为空数组
- **THEN** 下方显示 "未找到匹配的文档" 提示

### Requirement: 文件卡片预览
系统 SHALL 支持用户点击文件卡片的「预览」按钮，通过 `GET /files/{path}` 获取文件内容并在卡片下方内联展开。

#### Scenario: 展开文件预览
- **WHEN** 用户点击文件卡片的「预览」按钮
- **THEN** 调用 `/files/{path}` 获取内容，卡片展开显示文件全文内容

#### Scenario: 收起文件预览
- **WHEN** 用户再次点击已展开卡片的「预览」按钮
- **THEN** 内联预览收起，卡片恢复原状

### Requirement: 文件卡片打开与定位
系统 SHALL 为每个文件卡片提供「打开」和「定位」按钮，分别用系统默认程序打开文件和打开文件所在文件夹。

#### Scenario: 用默认程序打开文件
- **WHEN** 用户点击文件卡片的「打开」按钮
- **THEN** 调用 `electronAPI.openPath(绝对路径)`，系统默认程序打开文件

#### Scenario: 在文件管理器中定位
- **WHEN** 用户点击文件卡片的「定位」按钮
- **THEN** 调用 `electronAPI.showItemInFolder(绝对路径)`，打开文件管理器并选中文件

### Requirement: 工具状态指示
系统 SHALL 在输入框附近显示当前正在执行的工具状态，让用户了解 Agent 正在做什么。

#### Scenario: 显示搜索状态
- **WHEN** Agent 调用 search_index 工具（收到 `tool_start` 事件）
- **THEN** 状态指示显示 "🔍 搜索中..."

#### Scenario: 显示归档状态
- **WHEN** Agent 调用 archive_file 工具
- **THEN** 状态指示显示 "📂 归档中..."

#### Scenario: Agent 完成时清除状态
- **WHEN** 收到 SSE `done` 事件
- **THEN** 工具状态指示消失
