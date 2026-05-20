## ADDED Requirements

### Requirement: 仓库初始化时自动关联远程
当 `config.json` 配置了 `git.repo_url` 且本地仓库尚未配置 remote 时，`RepoManager.ensure_initialized()` 必须自动执行 `git remote add origin <url>`，并尝试 `git fetch origin` 以建立远程追踪分支。如果 fetch 失败（网络不可达），不得抛出异常，仅记录日志后继续。

#### Scenario: 有远程配置且无 remote 时自动关联
- **WHEN** `ensure_initialized()` 被调用，`config.json` 中有 `git.repo_url`，且 `.git/config` 中不存在 `[remote "origin"]`
- **THEN** 执行 `git remote add origin <url>`，并尝试 `git fetch origin`

#### Scenario: fetch 失败时不中断初始化
- **WHEN** `git fetch origin` 因网络问题返回非零退出码
- **THEN** `ensure_initialized()` 不抛异常，本地目录结构仍然创建成功

#### Scenario: 已有 remote 时不重复添加
- **WHEN** `.git/config` 中已存在 `[remote "origin"]`
- **THEN** 跳过 `git remote add`，不执行任何修改

### Requirement: pull 操作前自动修复 git 状态
`GitSyncTool` 执行 `action="pull"` 时，必须在 pull 前检查并修复以下问题：remote 缺失、本地分支不存在、tracking 信息缺失。

#### Scenario: remote 缺失时先添加再 pull
- **WHEN** 执行 `git_sync pull`，且 `git remote -v` 输出为空
- **THEN** 先执行 `git remote add origin <url>`，再执行 `git pull`

#### Scenario: 无 tracking 信息时建立追踪再 pull
- **WHEN** 执行 `git_sync pull`，当前分支无 tracking 信息
- **THEN** 执行 `git branch --set-upstream-to=origin/<branch> <branch>` 后再 pull

#### Scenario: 本地分支不存在时从远程创建
- **WHEN** 执行 `git_sync pull`，本地无对应分支但远程存在
- **THEN** 先 fetch，再 checkout 对应远程分支，然后 pull

### Requirement: push 时自动建立分支追踪
`_smart_push` 在推送时必须确保当前分支有正确的 upstream 追踪。

#### Scenario: 首次推送建立追踪
- **WHEN** 执行 `git_sync push`，当前分支无 upstream
- **THEN** 使用 `git push -u origin <branch>` 建立追踪并推送
