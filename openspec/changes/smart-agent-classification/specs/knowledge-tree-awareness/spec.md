## ADDED Requirements

### Requirement: list_tree 工具

系统 SHALL 提供 `list_tree` 工具，扫描知识库目录树并返回完整结构快照。

返回结果 SHALL 包含：
- 完整目录树（文件夹层级结构）
- 每个文件夹的 `.index.md` 内容（frontmatter + 文件列表）
- 可选按分类过滤（projects/research/personal）

该工具为只读操作，不修改任何文件。

#### Scenario: 扫描完整知识库

- **WHEN** Agent 调用 `list_tree()` 不带参数
- **THEN** 返回所有分类（projects/research/personal/inbox）的完整目录树和各文件夹 `.index.md` 内容

#### Scenario: 按分类过滤扫描

- **WHEN** Agent 调用 `list_tree(category_filter="projects")`
- **THEN** 仅返回 projects 分类下的目录树和 `.index.md` 内容

#### Scenario: 空知识库

- **WHEN** 知识库中仅有分类目录但无任何子文件夹
- **THEN** 返回目录树框架，各分类下显示空列表

### Requirement: 归档前先了解知识库结构

Agent SHALL 在执行任何归档操作前，先使用 `list_tree` 获取当前知识库结构。系统 Prompt SHALL 将此定义为强制步骤。

#### Scenario: 归档流程的第一步

- **WHEN** 用户请求归档文件
- **THEN** Agent 的第一个工具调用 MUST 是 `list_tree`（或用户明确指定了目标路径时除外）

#### Scenario: 用户明确指定路径时跳过

- **WHEN** 用户说"把这个归档到 projects/avatar/ 下"
- **THEN** Agent 可以跳过 `list_tree`，直接执行归档

### Requirement: 目录树上下文注入分类

`classify_content` 工具 SHALL 接收 `list_tree` 的输出作为 `tree_context` 参数，分类决策 MUST 基于此上下文进行。

#### Scenario: 正常的分类上下文流

- **WHEN** Agent 先调 `list_tree` 获得树结构，再将结果传给 `classify_content(tree_context=...)`
- **THEN** 分类结果基于真实知识库结构，而非 LLM 猜测

#### Scenario: 缺少目录树上下文

- **WHEN** `classify_content` 被调用但 `tree_context` 为空或未提供
- **THEN** 工具返回错误提示"请先使用 list_tree 获取知识库结构"

### Requirement: 查询场景下的目录树感知

`list_tree` 工具 SHALL 在查询场景下也可用。当用户询问"知识库里有什么"、"帮我看看有哪些项目"时，Agent 可以使用此工具获取概览。

#### Scenario: 用户询问知识库概况

- **WHEN** 用户输入"帮我看看知识库里都有什么内容"
- **THEN** Agent 使用 `list_tree` 获取结构后以自然语言回复用户
