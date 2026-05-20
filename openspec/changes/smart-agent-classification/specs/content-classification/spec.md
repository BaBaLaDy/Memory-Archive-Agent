## ADDED Requirements

### Requirement: classify_content 工具

系统 SHALL 提供 `classify_content` 工具，接收待归档内容的摘要和当前知识库目录树上下文，调用 LLM 进行语义匹配后返回结构化分类结果。

分类结果 SHALL 包含：
- `target_path`: 建议的目标路径（相对于存储根目录）
- `is_new_folder`: 是否需要创建新文件夹
- `title`: 文件标题
- `tags`: 标签列表
- `category`: 分类（projects/research/personal/inbox）
- `project`: 所属项目名称
- `summary`: 1-2 句内容摘要
- `related_existing`: 知识库中与待归档内容语义相关的已有文件路径列表

#### Scenario: 内容与已有项目语义匹配

- **WHEN** 待归档内容主题与 `projects/immersive-avatar/` 的 `.index.md` 描述语义相似
- **THEN** 工具返回 `is_new_folder: false`，`target_path` 指向 `projects/immersive-avatar/` 下，`related_existing` 列出项目中已有相关文件

#### Scenario: 内容属于全新领域

- **WHEN** 待归档内容与知识库中所有已有文件夹的 `.index.md` 描述均无语义匹配
- **THEN** 工具返回 `is_new_folder: true`，`target_path` 建议新建文件夹路径，`tags` 包含内容关键词

#### Scenario: 内容跨多个已有领域

- **WHEN** 待归档内容同时与 `projects/immersive-avatar/` 和 `research/imu/` 语义相关
- **THEN** 工具将内容归入最相关的文件夹，同时在 `related_existing` 中列出另一个文件夹中的关联文件

#### Scenario: 无法判断分类

- **WHEN** 待归档内容无法与任何已有知识结构建立语义关联
- **THEN** 工具返回 `category: "inbox"`，`is_new_folder: false`，`target_path` 指向 inbox 目录

### Requirement: classify_content 输入约束

分类内容输入 SHALL 限制为前 2000 字符摘要（非全文），以减少 LLM 调用成本和延迟。目录树上下文 SHALL 包含所有文件夹路径和各文件夹 `.index.md` 的 frontmatter 内容和文件列表。

工具执行失败时 SHALL 返回分类错误信息，而非阻塞整个归档流程（降级到 inbox）。

#### Scenario: 输入内容截断

- **WHEN** 待归档的原始内容超过 5000 字符
- **THEN** 工具仅取前 2000 字符传给 LLM 做分类判断，不影响后续完整归档

#### Scenario: 分类失败降级

- **WHEN** LLM 调用返回非 JSON 格式或超时
- **THEN** 工具返回 `category: "inbox"` 作为安全降级，不抛出异常

### Requirement: project_map.json 项目映射

系统 SHALL 维护 `.maa/project_map.json` 文件，以项目名称为 key 记录跨文件夹的项目文件关联。

`classify_content` 返回分类结果后，Agent SHALL 在归档完成时更新 `project_map.json`，将新归档文件路径加入对应项目的 `files` 列表。

#### Scenario: 新文件加入已有项目

- **WHEN** 文件归档到 `projects/immersive-avatar/new-note.md`，且该文件被分类为属于 `immersive-avatar` 项目
- **THEN** `project_map.json` 中 `immersive-avatar.files` 数组追加 `projects/immersive-avatar/new-note.md`

#### Scenario: 新建项目映射

- **WHEN** `classify_content` 返回 `is_new_folder: true` 和新的 `project` 名
- **THEN** 系统在 `project_map.json` 中创建新的项目条目，包含描述、标签和初始文件列表

#### Scenario: 跨文件夹项目关联

- **WHEN** 文件归档到 `projects/immersive-avatar/` 但 `classify_content` 返回 `related_existing` 包含 `research/imu/xxx.md`
- **THEN** `project_map.json` 中该项目条目同时包含两个路径的文件，但物理文件不移动
