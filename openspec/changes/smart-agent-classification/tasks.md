## 1. 安全加固（无依赖，可并行）

- [x] 1.1 archive_file 增加路径安全校验：在 `ArchiveFileTool.execute()` 中增加目标路径验证，拒绝写入存储根目录外路径和 `.maa/` 系统目录。修改 `src/maa/tools/archive.py`。
- [x] 1.2 git_sync 增加危险操作拦截：在 `GitSyncTool.execute()` 中拒绝 `push --force`、`reset --hard`、`clean -f` 等破坏性操作。修改 `src/maa/tools/sync.py`。
- [x] 1.3 code_run 增加安全约束：增加命令黑名单（`FORBIDDEN_PATTERNS`），检查禁止模式后拒绝执行；移除 `shell=True` 改为列表参数执行。修改 `src/maa/tools/code_run.py`。

## 2. 知识库感知（无依赖，可并行）

- [x] 2.1 实现 list_tree 工具：新建 `src/maa/tools/tree.py`，扫描 `~/MemoryArchive/` 下所有分类目录，读取各子文件夹的 `.index.md` 内容，返回目录树 JSON。继承 `BaseTool`，纯只读操作。
- [x] 2.2 新增 ProjectMap 数据模型和读写函数：在 `src/maa/storage/models.py` 中新增 `ProjectMap` 数据类，在 `src/maa/storage/index.py` 中新增 `load_project_map()` / `save_project_map()` / `add_to_project_map()` 函数。

## 3. 分类智能化（依赖：2.1, 2.2）

- [x] 3.1 实现 classify_content 工具：新建 `src/maa/tools/classify.py`，接收 `content_summary` + `tree_context` + `original_filename`，内部调用 LLM 做语义分类，返回结构化 JSON（target_path, is_new_folder, title, tags, category, project, summary, related_existing）。
- [x] 3.2 实现 classify_content 内部分类子 prompt：在 `src/maa/agent/prompt.py` 中新增 `build_classify_prompt()` 函数，生成用于内容分类的结构化 prompt，要求严格返回 JSON。
- [x] 3.3 update_index 增加 project_map 同步：在 `UpdateIndexTool.execute()` 中增加 `project_map` 更新逻辑，归档完成后将文件路径同步到对应项目映射。修改 `src/maa/tools/archive.py`。

## 4. Prompt 重构（依赖：1.x, 2.x, 3.x 完成后进行）

- [x] 4.1 重写系统 Agent Prompt：重写 `src/maa/agent/prompt.py` 中的 `build_system_prompt()` 函数。从操作手册式改为原则声明式，包含：核心职责、分类决策原则、安全红线、工具使用指南、错误处理降级策略。
- [x] 4.2 新增 prompt 中的安全红线章节：在系统 prompt 中以显眼方式声明禁止删除、越权写入、强制推送等安全约束，让 LLM 明确行为边界。

## 5. 诊断工具替代 code_run（无依赖，可并行）

- [x] 5.1 实现 git_status / git_remote_info 工具：在 `src/maa/tools/sync.py` 中新增 `GitStatusTool` 和 `GitRemoteInfoTool` 两个只读工具，分别封装 `git status`、`git branch`、`git remote` 等诊断命令。
- [x] 5.2 在 CLI 中注册所有新工具：修改 `src/maa/channels/cli.py` 的 `create_engine()` 函数，注册新增工具（list_tree, classify_content, git_status, git_remote_info），替换原有 code_run 的推荐使用场景。
