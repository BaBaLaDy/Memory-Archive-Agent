## ADDED Requirements

### Requirement: 索引写入时自动生成文件摘要
当条目被添加到全局索引时（通过 `update_index` 或 `sync_index`），系统 MUST 从文件内容的前 200 个字符中提取摘要，去除 frontmatter 和空白后存入 `summary` 字段。

#### Scenario: 新文件归档生成摘要
- **WHEN** `update_index` 将文件添加到全局索引
- **THEN** 读取文件前 200 字符，去除 YAML frontmatter，去除首尾空白，存入 `summary`

#### Scenario: sync_index 修复遗漏条目时生成摘要
- **WHEN** `sync_index` 发现文件在磁盘但不在索引中并自动添加
- **THEN** 同样提取前 200 字符作为 `summary`

#### Scenario: 文件过短或无法读取时使用默认摘要
- **WHEN** 文件内容不足 200 字符或读取失败
- **THEN** `summary` 使用 `"文件名: {title}"` 作为降级值

### Requirement: 索引条目支持 file_type 字段
全局索引条目 MUST 记录文件类型（md、pdf、png 等），以便搜索和展示时区分。

#### Scenario: sync_index 扫描 .md 文件
- **WHEN** 扫描到 .md 文件
- **THEN** `file_type` 设为 "md"

#### Scenario: sync_index 扫描 .pdf 文件
- **WHEN** 扫描到 .pdf 文件
- **THEN** `file_type` 设为 "pdf"
