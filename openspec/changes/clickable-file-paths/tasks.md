## 1. 后端 — ToolResult JSON 序列化

- [x] 1.1 `src/maa/tools/base.py`：ToolResult 新增 `to_json()` 方法，返回合法 JSON 字符串（含 success/data/error 字段）
- [x] 1.2 `src/maa/agent/engine.py`：`tool_end` 事件改用 `output.to_json()` 序列化，去掉 500 字符截断

> 依赖：1.1 → 1.2

## 2. 后端 — 搜索结果补全绝对路径

- [x] 2.1 `src/maa/tools/search.py`：`search_index` 的 execute 方法中，为每个结果补 `absolute_path` 字段（通过 `RepoManager.resolve_path`）
- [x] 2.2 `src/maa/tools/search.py`：`read_file` 的 `ToolResult.data` 字典中增加 `absolute_path` 字段

> 无依赖，与第 1 组并行

## 3. 后端 — Prompt 添加 [file:] 约定

- [x] 3.1 `src/maa/agent/prompt.py`：在 `build_system_prompt` 的"回复格式"部分添加 `[file:相对路径]` 使用说明

> 无依赖，与第 1、2 组并行

## 4. 前端 — 修复 fileResults 解析

- [x] 4.1 `desktop/src/App.tsx`：修改 `tool_end` 中 `search_index` 的解析逻辑，适配新的 JSON 格式（`{success, data: {results}}`），恢复前端的文件卡片渲染

> 依赖：1.2（新数据格式已到位）

## 5. 前端 — [file:] 链接渲染

- [x] 5.1 `desktop/src/App.tsx`：在 `md()` 函数中增加 `[file:路径]` 的识别和替换逻辑，渲染为可点击的 `<a>` 标签
- [x] 5.2 `desktop/src/App.tsx`：为 `<a>` 标签添加点击事件处理，调用 `electronAPI.openPath` 打开文件。已知存储根目录可通过 `API` 地址或 electronAPI 获取

> 依赖：2.1（搜索结果带 absolute_path，前端可参考路径解析模式）
