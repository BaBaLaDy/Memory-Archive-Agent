## Context

当前索引系统在 `update_index`、`sync_index`、`search_global_index`、`list_tree` 四个关键路径上都有缺失：
- 写入索引时不生成 summary，搜索字段只有 title + 空 tags + 空 summary
- 搜索时不覆盖文件名和路径
- list_tree 只显示子目录，不显示直接文件
- PDF 等非 Markdown 文件被完全跳过

这导致知识库中的文件即使存在，agent 也可能查不到。

## Goals / Non-Goals

**Goals:**
- 每个索引条目都有有意义的 summary
- 搜索覆盖 title + tags + summary + filename + path + category
- list_tree 能显示直接放在分类目录下的文件
- sync_index 能索引非 .md 文件（至少记录文件名、类型、大小）

**Non-Goals:**
- 不做 PDF 全文文本提取（需要 PyPDF2 集成到 sync_index，改动大且不是核心瓶颈）
- 不重写索引存储结构（保持 index.json 格式，只增加字段）
- 不引入新的外部依赖

## Decisions

### 决策 1：Summary 从文件前 200 字符提取，不引入 LLM

**选择**: 用纯文本截断法：取前 200 字符，去掉前导空白和 frontmatter，作为 summary。

**理由**: Summary 的目的是给搜索提供足够的关键词。文件开头通常包含核心信息（标题、第一段），截断后足以覆盖大部分搜索场景。用 LLM 生成 summary 会增加成本和延迟，且当前索引写入是同步操作。

**备选**: LLM 生成摘要 → 成本高、延迟大、索引写入会变慢。

### 决策 2：搜索扩展为在 `search_global_index` 中追加 path 和 filename 匹配

**选择**: 在现有 `searchable` 字符串中追加 `entry.get("path", "")` 和 `path.split("/")[-1]`（文件名部分）。

**理由**: 改动最小，不改变函数签名或返回结构，直接扩大搜索范围。

### 决策 3：`list_tree` 增加 `show_files` 参数，默认 true

**选择**: 在遍历分类目录时，如果目录下没有子目录但有直接 .md 文件，也收集展示。

**理由**: 保持向后兼容，不改变已有子目录的展示逻辑，只是补充显示直接文件。

### 决策 4：`sync_index` 对非 .md 文件只记录元数据，不做全文索引

**选择**: 扫描时同时 `rglob("*.pdf")`、`rglob("*.png")` 等常见格式，记录 path、title、file_type、size，但 summary 标注为元数据而非内容摘要。

**理由**: 最小改动，让 PDF/图片文件至少"能被搜到文件名"，不需要引入 PDF 解析库到 sync_index。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| 截断法提取的 summary 可能包含代码/噪音 | 前 200 字符足够提供搜索关键词，精确度要求不高 |
| 非 .md 文件扫描增加 sync_index 耗时 | 仅扫描文件名和 stat，不读取内容，开销极小 |
| index.json 体积增长 | 增加的字段数据量很小（每个条目几十字节） |

## Migration Plan

1. 代码部署后，用户需要手动运行一次 `sync_index` 来为现有文件补充 summary
2. 也可以让 agent 在下次归档时自动触发 `sync_index`（prompt 已有指导）
3. 无需回滚机制——新字段是可选的，旧条目不会因缺少字段而出错
