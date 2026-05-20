# Tauri Desktop App

基于 Tauri 2.0 的桌面应用，提供快速捕获、搜索浏览、对话 Agent 三个核心视图。

## ADDED Requirements

### Requirement: 全局热键唤起

应用 SHALL 注册全局快捷键 `Ctrl+Shift+M`，无论当前焦点在哪个应用，按下后立即弹出快速捕获窗口。

#### Scenario: 应用在后台时热键唤起
- **WHEN** 用户在其他应用中按下 `Ctrl+Shift+M`
- **THEN** 快速捕获窗口弹出到最前，获得焦点

#### Scenario: 应用退出后热键释放
- **WHEN** 用户退出 Memory Archive Desktop
- **THEN** 全局热键被释放，不再拦截 `Ctrl+Shift+M`

### Requirement: 系统托盘

应用 SHALL 在系统托盘显示图标，右键菜单包含「显示窗口」「快速捕获」「退出」选项。

#### Scenario: 托盘右键退出
- **WHEN** 用户右键托盘图标选择「退出」
- **THEN** 应用关闭所有窗口、停止 Python 后端进程、释放热键、退出

#### Scenario: 托盘左键恢复窗口
- **WHEN** 用户左键点击托盘图标
- **THEN** 显示主窗口

### Requirement: Python 进程管理

应用启动时 SHALL 自动启动 MAA HTTP Server（`python server.py`），退出时关闭。启动失败时提示用户检查 Python 环境。

#### Scenario: 正常启动
- **WHEN** Tauri 应用启动
- **THEN** Python MAA Server 在后台启动，连接到 `http://127.0.0.1:8899`

#### Scenario: Python 未安装或 server.py 缺失
- **WHEN** 无法启动 Python 进程
- **THEN** 应用显示错误提示：「无法启动 MAA 后端，请确认 Python 环境和 MAA 项目路径配置正确」

#### Scenario: Python 进程意外崩溃
- **WHEN** MAA Server 进程意外退出
- **THEN** 应用在 UI 中显示红色状态指示「后端离线」，并提供「重新启动」按钮

### Requirement: 快速捕获视图

快速捕获视图 SHALL 支持三种输入方式：拖拽文件、粘贴剪贴板内容、粘贴链接。用户点击「归档」后发送到 MAA 后端处理。

#### Scenario: 拖拽文件归档
- **WHEN** 用户拖拽一个或多个文件到捕获区域
- **THEN** 显示文件名和类型预览，用户可添加备注，点击「归档」后文件内容发送到 `/archive`，显示归档结果（路径、分类）

#### Scenario: 粘贴文本内容归档
- **WHEN** 用户在捕获区域按 `Ctrl+V` 粘贴文本
- **THEN** 显示内容预览，用户可添加标题和备注，点击「归档」后发送到 `/archive`

#### Scenario: 粘贴链接归档
- **WHEN** 用户粘贴一个 URL 到捕获区域
- **THEN** 识别为链接，显示链接预览，用户确认后发送到 `/archive`（带 `url` 参数）

#### Scenario: 空内容点击归档
- **WHEN** 捕获区域为空时点击「归档」
- **THEN** 按钮无响应，提示「请先拖入文件或粘贴内容」

#### Scenario: 显示最近归档
- **WHEN** 快速捕获视图打开
- **THEN** 下方显示最近 5 条归档记录（从 `/tree` 获取最新文件）

### Requirement: 搜索浏览视图

搜索浏览视图 SHALL 提供关键词搜索、按项目浏览、点击文件查看内容的完整搜索体验。

#### Scenario: 关键词搜索
- **WHEN** 用户在搜索框输入关键词并回车
- **THEN** 调用 `/search?q=关键词`，展示匹配文件列表（标题、路径、标签）

#### Scenario: 按项目浏览
- **WHEN** 用户切换到「项目」标签
- **THEN** 调用 `/projects` 获取所有项目，以文件夹树形结构展示，每项显示文件数

#### Scenario: 查看文件内容
- **WHEN** 用户点击搜索结果中的文件
- **THEN** 调用 `/files/{path}` 获取文件内容，在右侧预览区域渲染 Markdown

#### Scenario: 空搜索结果
- **WHEN** 搜索无结果
- **THEN** 显示「未找到相关内容」，建议更换关键词

### Requirement: 对话 Agent 视图

对话 Agent 视图 SHALL 提供与 CLI 同等能力的聊天界面，支持流式输出和工具调用过程展示。

#### Scenario: 发送消息流式回复
- **WHEN** 用户输入消息并发送
- **THEN** 通过 SSE 连接 `/chat`，实时展示 Agent 的流式回复，文字逐字出现

#### Scenario: 展示工具调用过程
- **WHEN** Agent 在对话中调用工具（如 search_index）
- **THEN** 界面显示工具名称和参数（可折叠），调用完成后显示结果摘要

#### Scenario: 对话历史
- **WHEN** 用户在对话视图中发送多条消息
- **THEN** 对话历史在当前会话中保留，以聊天气泡形式展示

#### Scenario: 后端离线时发消息
- **WHEN** MAA Server 离线时用户尝试发送消息
- **THEN** 显示错误提示「后端服务离线，请检查后重试」

### Requirement: 主窗口

应用 SHALL 有一个主窗口，通过标签栏在「快速捕获」「搜索浏览」「对话 Agent」三个视图间切换。

#### Scenario: 窗口切换
- **WHEN** 用户点击标签栏的「搜索浏览」
- **THEN** 界面切换到搜索视图，搜索框获得焦点

#### Scenario: 窗口最小尺寸
- **WHEN** 用户调整窗口大小
- **THEN** 窗口最小为 400x500 像素，确保三个视图的内容均可完整显示

#### Scenario: 热键呼出默认为捕获视图
- **WHEN** 通过热键唤起窗口
- **THEN** 窗口自动切换到「快速捕获」标签
