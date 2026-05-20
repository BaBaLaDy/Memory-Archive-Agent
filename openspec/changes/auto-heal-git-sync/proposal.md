## Why

Agent 的 git 同步功能在首次使用或远程仓库未关联时会失败。虽然 `config.json` 已配置 `git.repo_url`，但 `E:/MAAStore/.git/` 实际状态是一个通过 `git init` 创建的空仓库——没有 remote origin，没有本地分支，也没有 tracking 信息。当前 `_smart_push` 只在 push 时自动添加 remote，但 pull 操作没有任何前置检查和自愈逻辑。Agent 被 prompt 限制"最多重试 1 次"，遇到错误就放弃，无法自主修复基础设施问题。

这导致用户每次使用 git 同步都需要手动干预，违背了 Agent "自主归档"的设计目标。

## What Changes

- **`RepoManager.ensure_initialized()`**: 增加远程仓库自动关联逻辑。当检测到 `config.json` 有 `repo_url` 但 `.git/config` 没有 remote 时，自动执行 `git remote add + git fetch + git checkout/branch --set-upstream`
- **`GitSyncTool.execute(action="pull")`**: 替换直接 `git pull` 为 `_smart_pull()`，在 pull 前检查并修复 remote/tracking 缺失问题
- **`GitSyncTool._smart_push()`**: 现有逻辑保留，补充对本地分支不存在时的自动创建

## Capabilities

### New Capabilities
- `git-self-heal`: Git 同步操作的自动修复能力，包括远程关联、分支追踪建立、空仓库初始化推送

### Modified Capabilities
- (无现有 spec 需要修改)

## Impact

**涉及文件**:
- `src/maa/storage/repo.py` — RepoManager 初始化逻辑
- `src/maa/tools/sync.py` — GitSyncTool 的 pull/push 逻辑
- `src/maa/config.py` — 可能需要将 git 配置传递给 RepoManager

**不影响**: Agent 核心引擎、分类工具、存储模型、CLI 通道
