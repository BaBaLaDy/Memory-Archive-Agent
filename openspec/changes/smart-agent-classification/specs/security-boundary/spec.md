## ADDED Requirements

### Requirement: 禁止删除操作

所有工具 SHALL 被设计为不可执行文件删除操作。以下行为在任何情况下均被禁止：
- 调用系统命令删除文件（rm、del、rmdir、format）
- Git 破坏性操作（git reset --hard、git clean -f、git rm）
- 强制推送（git push --force / -f）
- 清空目录或文件内容后写入空内容

#### Scenario: code_run 收到删除命令

- **WHEN** LLM 生成包含 `rm` 或 `del` 的命令传给 `code_run`
- **THEN** 工具拒绝执行，返回错误信息"安全拒绝：包含禁止的删除操作"

#### Scenario: git_sync 收到 force push

- **WHEN** LLM 调用 `git_sync(action="push", message="--force")`
- **THEN** 工具拒绝执行，返回错误信息"安全拒绝：禁止强制推送"

#### Scenario: git_sync 收到 reset --hard

- **WHEN** LLM 调用 `git_sync(action="reset")` 或包含 `reset` 参数
- **THEN** 工具拒绝执行，返回错误信息"安全拒绝：reset 操作被禁止"

### Requirement: 路径安全校验

`archive_file` 工具 SHALL 在执行写入前校验目标路径：
- 路径必须在存储根目录（`~/MemoryArchive/`）范围内
- 禁止直接写入 `.maa/` 系统目录
- 允许覆盖已有 `.md` 文件（内容更新），但须通过安全校验

#### Scenario: 越权路径写入

- **WHEN** LLM 传入 `target_path` 指向存储根目录之外的路径（如 `/etc/passwd` 或 `~/.bashrc`）
- **THEN** 工具拒绝写入，返回错误信息"安全拒绝：目标路径在存储根目录之外"

#### Scenario: 写入系统目录

- **WHEN** LLM 传入 `target_path` 为 `.maa/config.json` 或 `.maa/index.json`
- **THEN** 工具拒绝写入，返回错误信息"安全拒绝：禁止直接写入 .ama 系统目录"

#### Scenario: 正常归档路径

- **WHEN** LLM 传入 `target_path` 为 `projects/my-project/notes.md`
- **THEN** 工具正常执行写入，创建必要父目录

### Requirement: code_run 安全约束

`code_run` 工具 SHALL 实施以下安全措施：
1. 禁用 `shell=True`，使用列表参数执行命令
2. 执行前检查命令是否包含禁止模式（rm、del、format、dd、chmod 777、sudo、git reset --hard、git clean、git push --force、pip install、npm install）
3. 命令仅限在存储根目录或子目录下执行

#### Scenario: 命令黑名单拦截

- **WHEN** LLM 生成的命令匹配 `FORBIDDEN_PATTERNS` 中任一正则模式
- **THEN** 工具拒绝执行，返回被拦截的具体模式和安全提示

#### Scenario: 安全命令通过

- **WHEN** LLM 生成 `git status` 或 `git remote -v` 等只读命令
- **THEN** 工具正常执行并返回结果

#### Scenario: 命令超时

- **WHEN** 命令执行超过 30 秒
- **THEN** 工具终止进程并返回超时错误

### Requirement: Prompt 层安全声明

系统 Prompt SHALL 包含"安全红线"章节，声明：
- 绝对禁止删除任何文件
- 绝对禁止强制推送
- 绝对禁止操作存储根目录之外的路径（读除外）
- 绝对禁止修改系统配置文件
- 绝对禁止安装软件包或运行不明确的脚本

#### Scenario: LLM 遵守安全红线

- **WHEN** Agent 遇到工具错误且无法自行修复
- **THEN** LLM 应向用户说明尝试了什么、为什么失败、建议什么，而非尝试危险操作
