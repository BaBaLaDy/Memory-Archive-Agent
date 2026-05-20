## ADDED Requirements

### Requirement: sync_index 能扫描非 Markdown 文件
`sync_index` 扫描文件系统时，系统 MUST 同时扫描常见非 .md 文件格式（.pdf、.png、.jpg、.docx），并为它们创建索引条目。

#### Scenario: sync_index 发现 PDF 文件
- **WHEN** `sync_index` 扫描到一个 .pdf 文件且不在索引中
- **THEN** 创建索引条目，记录 path、title（从文件名提取）、file_type="pdf"、size（字节）、summary（元数据标注）

#### Scenario: 非 .md 文件在 search_index 中可被搜索
- **WHEN** 用户通过文件名关键词搜索
- **THEN** PDF 等非 .md 文件的索引条目能被匹配返回

### Requirement: 非 .md 文件的摘要使用元数据标注
对于无法直接读取文本内容的文件（PDF、图片等），系统 MUST 使用元数据格式作为 summary，而非空字符串。

#### Scenario: PDF 文件的摘要
- **WHEN** 为 PDF 文件创建索引条目
- **THEN** `summary` 设为 `"[PDF] {文件名}，大小 {size}KB"` 格式的元数据描述
