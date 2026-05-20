## ADDED Requirements

### Requirement: 搜索覆盖文件名和路径
`search_global_index` 搜索时，系统 MUST 在 searchable 文本中包含文件的 path（完整路径）和 filename（仅文件名部分）。

#### Scenario: 通过文件名关键词搜索到条目
- **WHEN** 用户搜索 "intern" 且索引中存在 `personal/intern-log.md`
- **THEN** 该条目被匹配返回，因为文件名包含 "intern"

#### Scenario: 通过路径中的分类名搜索到条目
- **WHEN** 用户搜索 "personal" 且索引中存在 `personal/` 下的条目
- **THEN** 该条目被匹配返回，因为路径包含 "personal"

#### Scenario: 通过内容摘要关键词搜索到条目
- **WHEN** 用户搜索 "简历" 且某条目的 `summary` 包含 "简历"
- **THEN** 该条目被匹配返回
