## ADDED Requirements

### Requirement: 统一通过 Agent 处理所有用户输入
系统 SHALL 将所有用户输入（文本、文件路径、URL）通过 POST `/chat` SSE 接口发送给 Agent，由 Agent 自主判断意图并调用相应工具处理。

#### Scenario: Agent 判断归档意图
- **WHEN** 用户发送 "请归档文件 /Users/xxx/document.pdf"
- **THEN** Agent 调用 parse_file → classify_content → archive_file 工具链完成归档

#### Scenario: Agent 判断搜索意图
- **WHEN** 用户发送 "找关于实习的文档"
- **THEN** Agent 调用 search_index 工具搜索，返回匹配的文件列表

#### Scenario: Agent 判断问答意图
- **WHEN** 用户发送 "什么是 React hooks？"
- **THEN** Agent 直接生成 markdown 格式的回答，不调用文件操作工具

#### Scenario: Agent 收到路径但文件不存在
- **WHEN** 用户发送的路径指向不存在的文件
- **THEN** Agent 返回错误提示，说明文件不存在

### Requirement: 前端不区分操作模式
前端 SHALL NOT 在发送前判断用户意图（如"这是归档还是搜索"），所有意图判断由 Agent 完成。

#### Scenario: 同一输入框提交不同类型请求
- **WHEN** 用户先后发送 "归档 /path/to/file.md" 和 "找关于机器学习的文档" 和 "解释一下闭包"
- **THEN** 三条消息均通过相同的 `/chat` 接口发送，前端对三条消息的处理方式完全相同

### Requirement: 无状态交互
每次发送消息 SHALL 为一次独立交互，不携带之前的对话上下文。关闭窗口或收回托盘后，所有对话记录丢弃。

#### Scenario: 每次发送为独立交互
- **WHEN** 用户发送完第一条消息并收到回复后，再发送第二条消息
- **THEN** 第二条消息不包含第一条的对话历史，Agent 将其作为全新请求处理

#### Scenario: 关闭窗口丢弃历史
- **WHEN** 用户关闭桌面窗口（隐藏到托盘）
- **THEN** 之前的回答和文件结果清空，重新打开窗口时显示空白状态

### Requirement: 保留专用端点
`/archive` 和 `/search` 端点 SHALL 继续保留，供未来 MCP Server 等场景使用，但前端不再直接调用。

#### Scenario: 专用端点仍可独立调用
- **WHEN** 外部客户端直接 POST `/archive` 或 GET `/search`
- **THEN** 端点正常响应，行为不受前端重构影响
