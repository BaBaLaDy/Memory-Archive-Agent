## 1. 数据模型增强

- [x] 1.1 `IndexEntry` 增加 `file_type: str = "md"` 字段，`to_dict` / `from_dict` 同步支持（models.py）

## 2. Summary 自动生成

- [x] 2.1 `index.py` 新增 `generate_summary(file_path: Path) -> str`：读前 200 字符，去 frontmatter，去空白，返回摘要（index.py）
- [x] 2.2 `SyncIndexTool.execute` 创建 `IndexEntry` 时调用 `generate_summary` 填入 summary（archive.py，依赖 2.1）
- [x] 2.3 `UpdateIndexTool.execute` 创建 `IndexEntry` 时同样调用 `generate_summary`（archive.py，依赖 2.1）

## 3. 搜索范围扩展

- [x] 3.1 `search_global_index` 的 `searchable` 拼接中加入 `entry.get("path", "")` 和文件名部分（index.py）

## 4. 非 .md 文件索引

- [x] 4.1 `sync_index` 扫描时增加对 `.pdf`、`.png`、`.jpg`、`.docx` 的 `rglob`，为非 .md 文件创建索引条目（archive.py）

## 5. list_tree 显示直接文件

- [x] 5.1 `list_tree` 遍历分类目录时，如果该目录下没有子目录但有 .md 文件，也收集展示（tree.py）

## 6. 验证

- [x] 6.1 运行 `sync_index` 验证 existing 条目被补充 summary，新文件（含 PDF）被索引
- [x] 6.2 搜索 "简历"/"实习" 验证能匹配到 personal/ 下的条目
- [x] 6.3 `list_tree` 验证能显示 personal/ 下的直接文件
