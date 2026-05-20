## 为什么

当前 Agent 存在三个根因问题：(1) Prompt 是硬编码的操作手册而非原则声明，LLM 按固定步骤无脑执行；(2) 架构文档中定义的 `classify_content` 工具未实现，分类逻辑嵌入 prompt，LLM 看不到知识库目录树，只能盲猜分类；(3) `code_run` 使用 `shell=True` 无安全边界，且当前模型写出正确诊断命令的能力弱。这导致 Agent 分类不准、无法跨文件夹关联项目、安全性差、智能度低。现在 Phase 1 核心引擎刚跑通，正是修正架构方向的最佳时机。

## 改变什么

- **新增 `classify_content` 工具**：输入内容摘要 + 目录树上下文，LLM 语义匹配后返回结构化分类结果（目标路径、是否新建、标签、摘要、跨文件夹关联）
- **新增 `list_tree` 工具**：扫描知识库完整目录树 + 各文件夹 `.index.md` 摘要，为分类决策提供上下文
- **新增 `git_status` / `git_remote_info` 工具**：替代 `code_run` 做 Git 诊断，只读操作，零风险
- **改造 `code_run`**：移除 `shell=True` 改为安全模式，增加命令黑名单/白名单
- **改造 `archive_file`**：增加路径安全校验，禁止写入 `.maa/` 和存储根目录外的路径
- **改造 `git_sync`**：禁止 `push --force`、`reset --hard`、`clean -f` 等破坏性操作
- **重构系统 Prompt**：从操作手册式转为原则声明式，定义安全红线、分类决策原则、工具使用指南
- **新增 `project_map.json` 数据模型**：支持跨文件夹的项目视图索引，解决不同文件夹文档属于同一类的问题

## 能力

### 新增能力

- `content-classification`: Agent 能读取知识库完整目录树和各文件夹的语义描述（.index.md），根据待归档内容的语义自主判断归属，发现跨文件夹的项目关联。输出结构化分类结果，支持新建项目建议和关联已有文件。
- `security-boundary`: 建立多层安全边界——工具层强制执行（拒绝删除/越权写入）、Prompt 层声明红线、命令执行白名单模式。所有工具不得执行任何删除操作（rm、git reset --hard、git clean、force push）。
- `knowledge-tree-awareness`: Agent 在做任何分类决策前，能先获取知识库的完整结构视图（目录树 + 各文件夹语义描述），实现"先看再动"的智能决策模式。

### 修改的能力

（无——当前没有已存在的 spec，这是首次建立能力规范）

## 影响

涉及文件：
- `src/maa/agent/prompt.py` — 重写系统 prompt（核心改动）
- `src/maa/tools/classify.py` — 新增 classify_content 工具（核心新增）
- `src/maa/tools/tree.py` — 新增 list_tree 工具
- `src/maa/tools/code_run.py` — 安全收紧
- `src/maa/tools/archive.py` — 路径安全校验 + project_map 更新
- `src/maa/tools/sync.py` — 禁止危险 git 操作 + 新增 git_status / git_remote_info
- `src/maa/storage/models.py` — 新增 ProjectMap 数据模型
- `src/maa/channels/cli.py` — 注册新工具

不引入新依赖，不改变现有工具的外部接口（只增加安全约束），不修改存储层核心逻辑。
