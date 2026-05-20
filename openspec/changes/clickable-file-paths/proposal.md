## Why

用户在桌面端询问 Agent 知识库文档时，LLM 回复中的文件路径是纯文本无法点击，且结构化文件卡片因数据格式问题经常渲染失败。用户无法便捷地预览、打开或定位文件，严重影响了知识库的可用性。

## What Changes

- **后端修复**：`tool_end` 事件改用合法 JSON 输出 ToolResult 数据，去掉 500 字符截断；搜索和读取结果补齐 `absolute_path` 字段
- **约定格式**：Agent 的 system prompt 中约定 `[file:相对路径]` 格式，LLM 在回复中引用文件时使用此格式
- **前端识别**：Markdown 渲染器识别 `[file:路径]` 语法，转换为可点击的文件链接，点击时通过 Electron API 打开文件或定位到文件夹
- **文件卡片增强**：修复 `fileResults` 解析逻辑，确保预览/打开/定位按钮正常工作

## Capabilities

### New Capabilities

- `clickable-file-links`: LLM 回复中的文件路径可点击打开，前端识别约定格式并调用系统能力打开文件

### Modified Capabilities

_无 —— 不改变已有 spec 的行为要求，仅修复实现层面的 bug 和增加渲染能力_

## Impact

| 层级 | 涉及文件 | 改动性质 |
|------|----------|----------|
| 后端 engine | `src/maa/agent/engine.py` | 修复 tool_end 数据序列化 |
| 后端 prompt | `src/maa/agent/prompt.py` | 添加 `[file:路径]` 输出约定 |
| 后端 tools | `src/maa/tools/search.py` | 搜索结果增加 absolute_path |
| 后端 tools | `src/maa/tools/base.py` | ToolResult 增加 to_json() 方法 |
| 前端 | `desktop/src/App.tsx` | 识别 [file:] 语法，修复 fileResults 解析 |
