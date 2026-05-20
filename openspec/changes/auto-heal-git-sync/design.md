## Context

当前 `E:/MAAStore/.git/` 是一个 `git init` 创建的空仓库：
- 没有 `[remote "origin"]` 配置段
- 没有本地分支（`refs/heads/` 为空）
- HEAD 指向 `refs/heads/master`（不存在的分支）
- 没有 tracking 信息

而 `config.json` 已配置了 `git.repo_url = "git@github.com:..."`。

问题根源：
1. `RepoManager.ensure_initialized()` 只做 `git init`，不关联远程
2. `GitSyncTool` 的 `pull` action 直接调用 `git pull`，没有任何前置检查
3. `_smart_push` 只在 push 时处理 remote 缺失，但 push 成功后 pull 仍然失败

## Goals / Non-Goals

**Goals:**
- 仓库初始化时自动关联远程仓库（如果 config 配置了 repo_url）
- pull/push 操作前自动检查并修复 git 状态，不需要 agent 介入
- 失败时优雅降级，不阻塞归档流程

**Non-Goals:**
- 不改变 prompt 中的 git 同步行为（依然可选、失败不重试）
- 不处理 SSH key / token 认证问题（那是网络/凭据层问题）
- 不修改 agent 核心引擎或分类逻辑

## Decisions

### 决策 1：在 RepoManager 层处理远程关联，而不是在 sync tool

**选择**: 在 `RepoManager` 新增 `ensure_remote()` 方法，在 `ensure_initialized()` 后被调用

**理由**: 这是基础设施层面的初始化逻辑，不应该依赖 LLM 的工具调用决策。`RepoManager` 已经负责仓库初始化，远程关联是自然的延伸。

**备选**: 在 `GitSyncTool._smart_push` 中处理 → 但这样 pull 操作依然无法自愈。

### 决策 2：修改 `RepoManager.__init__` 接受 config，使它能访问 git_repo_url

**选择**: 给 `RepoManager.__init__` 增加可选的 `remote_url` 和 `branch` 参数

**理由**: `RepoManager` 目前不依赖 Config 模块（避免循环引用）。通过参数传入 git 配置，保持低耦合。

**修改点**:
- `src/maa/storage/repo.py`: `__init__` 增加 `remote_url` 和 `branch` 参数；新增 `ensure_remote()` 方法
- 调用处（`sync.py` 中各工具的 `execute`）传入 config 的 git 参数

### 决策 3：pull 操作增加 `_smart_pull` 方法

**选择**: 类似 `_smart_push`，`_smart_pull` 在 pull 前检查：
1. remote 是否存在 → 不存在则 add
2. 本地分支是否存在 → 不存在则 fetch + checkout
3. tracking 是否存在 → 不存在则 `branch --set-upstream-to`

**修改点**:
- `src/maa/tools/sync.py`: `action == "pull"` 分支改为调用 `_smart_pull()`

### 决策 4：不改变 prompt 中的 git 失败处理策略

**理由**: prompt 已经正确定义了 "git 同步失败不阻塞归档"。底层基础设施的自愈是透明补充，不是行为变更。prompt 不需要改动。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| `git fetch` 在离线/网络差时超时 | `run_git` 已有 30s 超时，fetch 失败时 `ensure_remote()` 静默跳过，不影响本地写入 |
| 用户更换了 remote URL 但 config.json 未更新 | `ensure_remote()` 只在 remote 不存在时创建，不覆盖已有 remote |
| SSH key 未配置导致 fetch/push 失败 | 这属于认证层问题，`ensure_remote()` 只负责关联关系，不负责认证 |
