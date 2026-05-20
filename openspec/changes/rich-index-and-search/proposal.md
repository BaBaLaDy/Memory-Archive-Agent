## Why

当前索引系统存在多个根因问题，导致知识库中已有文件无法被 agent 检索到：

1. **Summary 永远为空**：`update_index` 和 `sync_index` 在创建 `IndexEntry` 时 `summary=""`，没有生成任何摘要，导致搜索字段极度贫乏
2. **搜索不覆盖文件名**：`search_global_index` 只搜索 title + tags + summary，不包含 path/filename
3. **list_tree 不显示直接文件**：只遍历子目录，跳过直接放在 `personal/` 等分类下的文件
4. **非 MD 文件不被索引**：PDF、图片等非 Markdown 文件完全跳过，无法被检索
5. **文件不在索引时很难找到**：默认 `deep=False` 只查索引，遗漏文件需要用户主动触发 deep 模式

## What Changes

- `IndexEntry` 写入时自动生成 summary（从文件前几行提取关键信息）
- `search_global_index` 搜索范围扩展：加入 path、filename、category 字段
- `list_tree` 增加对直接文件的显示（不仅限于子目录）
- `sync_index` 支持索引非 .md 文件（PDF、图片等），提取元数据
- `search_index` deep 模式的提示更友好，自动触发修复

## Capabilities

### New Capabilities
- `auto-summary`: 索引写入时自动生成文件摘要，让搜索字段有意义
- `extended-search`: 搜索范围覆盖文件名、路径、分类字段
- `non-md-indexing`: PDF、图片等非 Markdown 文件的元数据索引

### Modified Capabilities
- `knowledge-tree-awareness`: list_tree 需要增加对直接文件的展示能力（不改变"先看再动"的原则，只扩展覆盖范围）

## Impact

**涉及文件**:
- `src/maa/storage/index.py` — `search_global_index` 扩展搜索字段 + 新增 summary 生成函数
- `src/maa/storage/models.py` — `IndexEntry` 增加 `file_type` 字段（区分 md/pdf/image）
- `src/maa/tools/archive.py` — `UpdateIndexTool` 和 `SyncIndexTool` 写入时生成 summary
- `src/maa/tools/search.py` — `search_index` deep 模式优化
- `src/maa/tools/tree.py` — `list_tree` 显示直接文件
