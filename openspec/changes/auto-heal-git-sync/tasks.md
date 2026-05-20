## 1. 基础设施层：RepoManager 增强

- [x] 1.1 修改 `RepoManager.__init__`，增加可选参数 `remote_url: str | None` 和 `branch: str | None`，并保存为实例属性
- [x] 1.2 在 `RepoManager` 中新增 `ensure_remote()` 方法：检查 `.git/config` 是否有 remote origin，无则 `git remote add`，尝试 `git fetch origin`（失败不抛异常）
- [x] 1.3 修改 `RepoManager.ensure_initialized()` 结尾调用 `ensure_remote()`（当 `remote_url` 已配置时）

## 2. 工具层：GitSyncTool 自愈能力

- [x] 2.1 新增 `_smart_pull()` 方法：检查 remote → 检查分支 → 检查 tracking → 执行 pull，任一环节自动修复
- [x] 2.2 修改 `GitSyncTool.execute(action="pull")` 分支，改为调用 `_smart_pull(repo, config)`
- [x] 2.3 修改 `GitSyncTool.execute` 中各 action 的 `RepoManager` 实例化，传入 `config.git_repo_url` 和 `config.git_branch`
- [x] 2.4 增强 `_smart_push()`：当本地分支不存在时，先尝试 fetch + checkout，再 push

## 3. 验证

- [x] 3.1 手动在 `E:/MAAStore` 测试：清理现有 git 状态后重新初始化，验证 `ensure_initialized()` 自动关联远程
- [x] 3.2 测试 `git_sync pull` 在无 tracking 信息时能自动建立追踪并成功拉取
- [x] 3.3 测试离线场景：fetch 失败不阻塞本地写入流程
