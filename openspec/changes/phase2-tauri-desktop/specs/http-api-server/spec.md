# HTTP API Server

MAA 核心引擎的 HTTP API 服务，以 REST 端点暴露归档、搜索、对话、浏览能力。

## ADDED Requirements

### Requirement: Server 启动与生命周期

HTTP Server SHALL 在 `python server.py` 启动后监听 `127.0.0.1:8899`，仅本地访问，不暴露网络端口。

#### Scenario: 服务正常启动
- **WHEN** 用户执行 `python server.py`
- **THEN** 服务在 `127.0.0.1:8899` 启动，输出 `Uvicorn running on http://127.0.0.1:8899`

#### Scenario: 端口被占用
- **WHEN** 端口 8899 已被占用
- **THEN** 服务自动尝试 8900 端口并输出警告

### Requirement: 归档端点

`POST /archive` SHALL 接收归档请求，调用 Agent 引擎的 classify → archive → update_index 流程，返回归档结果。

#### Scenario: 通过源文件路径归档
- **WHEN** 发送 `{"source_path": "/path/to/file.md"}`
- **THEN** 服务读取文件、自动分类、写入知识库、更新索引，返回 `{"success": true, "path": "projects/xxx/file.md", "category": "projects"}`

#### Scenario: 通过文本内容归档
- **WHEN** 发送 `{"content": "文本内容...", "title": "我的笔记"}`
- **THEN** 服务分类内容、写入知识库、更新索引，返回存储路径

#### Scenario: 通过 URL 归档
- **WHEN** 发送 `{"url": "https://example.com/article"}`
- **THEN** 服务抓取网页内容、分类、写入知识库、更新索引

### Requirement: 搜索端点

`GET /search?q=<query>` SHALL 在全局索引中搜索匹配的文件，返回文件列表。

#### Scenario: 搜索到结果
- **WHEN** 发送 `GET /search?q=IMU`
- **THEN** 返回 `{"results": [{"path": "research/imu/motion.md", "title": "...", "tags": [...]}], "count": N}`

#### Scenario: 无匹配结果
- **WHEN** 发送 `GET /search?q=不存在的关键词`
- **THEN** 返回 `{"results": [], "count": 0}`

### Requirement: 文件读取端点

`GET /files/{path}` SHALL 读取知识库内指定文件的内容。path 为知识库内相对路径（URL 编码）。

#### Scenario: 读取已存在文件
- **WHEN** 发送 `GET /files/projects/immersive-avatar/unity-ik-notes.md`
- **THEN** 返回文件完整 Markdown 内容（含 frontmatter）

#### Scenario: 文件不存在
- **WHEN** 发送 `GET /files/不存在的文件.md`
- **THEN** 返回 404 和错误信息

### Requirement: 目录树端点

`GET /tree` SHALL 返回知识库完整目录树结构，包含每个文件夹的 `.index.md` 内容。

#### Scenario: 获取目录树
- **WHEN** 发送 `GET /tree`
- **THEN** 返回知识库完整目录树 JSON 结构

### Requirement: 项目列表端点

`GET /projects` SHALL 返回所有项目列表及每个项目的文件数和标签。

#### Scenario: 获取项目列表
- **WHEN** 发送 `GET /projects`
- **THEN** 返回 `{"projects": [{"name": "immersive-avatar", "files": 3, "tags": ["unity", "ik"]}]}`

### Requirement: 流式对话端点

`POST /chat` SHALL 接收用户消息，通过 SSE 流式返回 Agent 的思考和回复。

#### Scenario: 普通对话
- **WHEN** 发送 `{"message": "帮我找 IMU 相关的笔记"}`
- **THEN** 服务通过 SSE 流式返回 Agent 的工具调用过程和最终回复，事件类型包括 `token`、`tool_call`、`tool_result`、`done`

#### Scenario: 归档指令
- **WHEN** 发送 `{"message": "帮我把这个文件归档: /path/to/doc.pdf"}`
- **THEN** Agent 自动执行 classify → archive → index 流程，SSE 实时汇报进度

#### Scenario: 空消息
- **WHEN** 发送 `{"message": ""}`
- **THEN** 返回 400 错误
