## 1. Electron preload 增强

- [x] 1.1 在 preload.cjs 中引入 `webUtils` 和 `shell`，通过 `contextBridge` 暴露 `getFilePath`、`openPath`、`showItemInFolder` 三个函数到渲染进程
- [x] 1.2 在 `desktop/src/` 中新增 TypeScript 类型声明文件，为 `window.electronAPI` 提供类型定义

## 2. 后端小改

- [x] 2.1 修改 `ReadFileTool` 的返回数据，在 `/files/{path}` 响应中增加 `absolute_path` 字段（调用 `repo.resolve_path()` 获取）

## 3. 新组件实现

- [x] 3.1 新建 `InputBar.tsx`：多行 textarea + 文件 chip + 拖拽处理（拖入 → `getFilePath` → 显示 chip；Enter 发送 / Shift+Enter 换行；发送时禁用输入）
- [x] 3.2 新建 `AnswerPanel.tsx`：实时接收 token 累积文本，以 markdown 渲染 Agent 回答
- [x] 3.3 新建 `ResultPanel.tsx`：解析 search_index 的 tool_end 数据，渲染文件卡片列表（含标题、路径、标签）
- [x] 3.4 为文件卡片实现「预览」（调用 `/files/{path}` 内联展开）、「打开」（`openPath`）、「定位」（`showItemInFolder`）三个按钮

## 4. 主视图整合

- [x] 4.1 新建 `MainView.tsx`：编排三区域布局（上方 AnswerPanel、中间 InputBar、下方 ResultPanel），管理 SSE 事件分流逻辑（token → 上方，search_index tool_end → 下方）
- [x] 4.2 修改 `App.tsx`：移除三标签页和旧组件引用，直接渲染 MainView
- [x] 4.3 新增 markdown 渲染依赖（若现有项目中无可用库），在 AnswerPanel 中实现基本的 markdown → JSX 转换（标题、代码块、列表、链接）

## 5. 清理与验证

- [x] 5.1 删除废弃文件：`CaptureView.tsx`、`SearchView.tsx`、`ChatView.tsx`
- [x] 5.2 端到端验证：启动 dev 环境，测试拖入文件归档、文本搜索、Agent 问答三条主路径
