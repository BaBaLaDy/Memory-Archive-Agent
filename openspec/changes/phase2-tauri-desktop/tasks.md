## 1. MAA HTTP Server（Python 侧）

- [x] 1.1 添加 fastapi + uvicorn 依赖到 pyproject.toml
- [x] 1.2 创建 `src/maa/server/` 模块（routes.py + sse.py），sse.py 负责将 StreamEvent 转为 SSE 文本
- [x] 1.3 创建 `server.py` 入口，实现全部 6 个 REST 端点：POST /archive、GET /search、POST /chat（SSE 流式）、GET /tree、GET /files/{path}、GET /projects
- [x] 1.4 扩展 `AgentEngine.run_stream()` 返回的 StreamEvent 以包含最终完成标记（done 事件），供 SSE 用

## 2. Tauri 项目初始化（新仓库）

- [x] 2.1 创建 Tauri 2.0 + React + TypeScript 项目脚手架
- [x] 2.2 实现 Rust 侧的 Python 子进程管理：启动 `python server.py`、退出时 kill、端口健康检查
- [x] 2.3 实现全局热键 `Ctrl+Shift+M` 注册

## 3. 快速捕获视图

- [x] 3.1 构建捕获视图 UI：拖拽区域、文本粘贴区域、链接输入框、备注栏、归档按钮
- [x] 3.2 实现文件拖拽解析（Tauri API 读文件路径）、剪贴板读取、URL 识别
- [x] 3.3 对接 POST /archive 接口，展示归档结果和最近归档列表

## 4. 搜索浏览视图

- [x] 4.1 构建搜索视图 UI：搜索框、结果列表（标题/路径/标签）、文件内容预览面板
- [x] 4.2 对接 GET /search 和 GET /files/{path} 接口，支持按项目列表浏览

## 5. 对话 Agent 视图

- [x] 5.1 构建聊天 UI：消息列表（聊天气泡）、输入框、发送按钮
- [x] 5.2 实现 SSE 客户端（EventSource），对接 POST /chat，展示流式回复和工具调用过程

## 6. 集成与收尾

- [x] 6.1 实现系统托盘图标与右键菜单（显示窗口 / 退出）
- [x] 6.2 实现主窗口标签栏切换（快速捕获 / 搜索浏览 / 对话 Agent）
- [x] 6.3 端到端集成测试：热键唤起 → 拖入文件 → 归档 → 搜索确认 →

 对话框验证
