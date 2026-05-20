## 背景

当前项目 Phase 1 核心引擎已跑通：ReAct Agent + 9 个工具（parse、extract、archive、update_index、search、read、list、git_sync、code_run）+ CLI 通道。但架构文档中设计的 `classify_content` 工具未实现，分类逻辑被嵌入 prompt 中的硬编码规则替代。Agent 在做归档决策时看不到知识库的目录树结构，无法实现语义级分类和跨文件夹项目关联。同时 `code_run` 使用 `shell=True` 无安全边界。

## 目标 / 非目标

**目标：**
- Agent 能读取知识库目录树 + 各文件夹语义描述，自主判断内容归属
- 支持跨文件夹的项目关联（不同路径的文档属于同一主题时能识别并记录）
- 建立多层安全边界，确保工具层强制执行"不可删除、不可越权"的约束
- Prompt 从操作手册升级为原则声明，让 LLM 自主决策而非无脑执行固定步骤

**非目标：**
- 不引入向量数据库或语义搜索（Phase 1 范围外）
- 不修改存储层核心逻辑（目录结构、Git 管理不变）
- 不增加新的外部依赖
- 不实现自动跨文件夹移动已有文件（只发现关联、记录关系，不自动重组已有结构）

## 决策

### 决策 1：分类逻辑从 Prompt 移至专用工具

**选择**：实现独立的 `classify_content` 工具，内部调用 LLM 做语义匹配。

**原因**：
- 工具调用时传入完整目录树上下文，能提供远超 prompt 可容纳的信息量
- 工具返回结构化 JSON，后续工具可直接消费，减少 Agent 循环次数
- 分类 prompt 可以独立调优，不影响主 Agent 的行为边界

**替代方案**：直接在系统 prompt 中注入目录树信息，让 LLM 在对话中直接输出分类决策。未采用原因：系统 prompt 过长会压缩可用上下文；分类逻辑和对话逻辑混在一起难以调试；无法利用 function calling 的结构化输出优势。

### 决策 2：list_tree 和 classify_content 分两步

**选择**：`list_tree` 扫描目录树 → `classify_content` 做语义分类，两步独立。

**原因**：
- `list_tree` 是通用能力，查询场景也需要（"帮我看看知识库里有什么"）
- 两个工具各自返回的结果可被 LLM 观察和验证，增强决策可解释性
- 减少单次 LLM 调用的上下文量，降低延迟和 token 消耗

**替代方案**：合并为一个工具。未采用原因：合并后工具职责不单一，且丢失中间可观测性。

### 决策 3：code_run 安全策略 —— 黑名单 + 移除 shell=True

**选择**：`code_run` 增加命令黑名单（含 rm/del/format/git reset --hard/git push --force 等破坏性词汇），移除 `shell=True` 改为列表参数 + 白名单前缀检查。同时新增专用诊断工具替代常见场景。

**原因**：
- `shell=True` 是命令注入的根源，移除后攻击面大幅缩小
- 黑名单阻止最危险的破坏性操作
- 专用工具（git_status、git_remote_info）覆盖 80% 的诊断场景，减少对 code_run 的依赖

**替代方案**：完全移除 code_run。未采用原因：保留受限版本作为"最后手段"有价值，完全移除会削弱 Agent 的自主排查能力。

### 决策 4：安全架构 —— 工具层强制执行，Prompt 层声明

**选择**：建立双层安全架构：
1. 工具层（强制）—— `archive_file` 拒绝写入 `.maa/` 和根目录外路径；`git_sync` 拒绝 force push / reset / clean；`code_run` 拒绝含破坏性关键词的命令
2. Prompt 层（声明）—— 在系统 prompt 中以"安全红线"章节声明禁止行为

**原因**：
- 工具层强制执行是最可靠的安全保障——即使 LLM 产生幻觉，工具也会拒绝危险操作
- Prompt 层声明让 LLM 理解边界，减少无效尝试，提高效率
- 双层设计符合纵深防御原则

**替代方案**：仅在 prompt 中声明安全规则。未采用原因：prompt 无法阻止 LLM 幻觉或被 jailbreak 的攻击。

### 决策 5：project_map.json 数据模型

**选择**：新增 `.maa/project_map.json`，以项目名称为 key，存储该项目的描述、标签、关联文件列表（可跨文件夹）。

**原因**：
- 解决"不同文件夹文档属于同一项目"的核心需求
- JSON 格式可被机器快速查询，也可被 LLM 理解
- 不影响现有索引结构，是增量补充
- `classify_content` 工具可检查此映射表发现已有项目的跨文件夹关联

**数据结构**：
```json
{
  "version": 1,
  "projects": {
    "project-name": {
      "name": "中文项目名",
      "description": "项目描述",
      "tags": ["tag1", "tag2"],
      "files": ["path/to/file1.md", "path/to/file2.md"],
      "created_at": "2026-05-17",
      "updated_at": "2026-05-17"
    }
  }
}
```

## 风险 / 权衡

| 风险 | 缓解措施 |
|---|---|
| `classify_content` 内部 LLM 调用增加延迟和成本 | 传入摘要而非全文（限制 2000 字）；结果缓存同类文件 |
| 黑名单可能被绕过（编码、变体） | 白名单前缀检查作为第二道防线；code_run 不是主要工具 |
| 新工具增加 Agent 工具选择复杂度 | 工具描述清晰标注使用场景；prompt 中提供工具选择指南 |
| project_map 与文件夹索引可能不同步 | `update_index` 工具同时更新两层索引；定期一致性检查 |
| LLM 分类结果不稳定 | classify_content 内部 prompt 要求 JSON 严格输出；tool 层做格式校验 |

## 迁移计划

1. **无破坏性变更**：所有改动是新增工具 + 现有工具内部增加安全校验，不改变现有接口签名
2. **回滚策略**：如有问题，恢复旧版 prompt.py 和 code_run.py 即可；新工具不调用则不影响运行
3. **渐进部署**：安全加固（Phase 1）→ 新工具 + Prompt 重构（Phase 2-3）→ code_run 替代（Phase 4）
