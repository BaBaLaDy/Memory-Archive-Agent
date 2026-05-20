from .base import BaseTool, ToolResult


class GitSyncTool(BaseTool):
    """Git 同步操作"""

    name = "git_sync"
    description = "对存储库执行 Git 操作：pull、push、status、add、commit"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["pull", "push", "status", "add", "commit"],
                "description": "要执行的 Git 操作",
            },
            "message": {"type": "string", "description": "commit 时使用提交信息（仅 action=commit 时需要）"},
        },
        "required": ["action"],
    }

    def execute(self, action: str, message: str | None = None) -> ToolResult:
        from maa.storage.repo import RepoManager
        from maa.config import load_config

        # --- 危险操作拦截 ---
        if action in ("reset", "clean"):
            return ToolResult(
                success=False,
                error=f"安全拒绝：{action} 操作被禁止（不可撤销的数据破坏风险）",
            )
        if action == "push" and message and "--force" in message:
            return ToolResult(
                success=False,
                error="安全拒绝：禁止强制推送（push --force）",
            )

        config = load_config()
        repo = RepoManager(
            config.storage_root,
            remote_url=config.git_repo_url,
            branch=config.git_branch,
        )

        try:
            if action == "status":
                stdout, stderr, code = repo.run_git("status", "--short")
                if code != 0:
                    return ToolResult(success=False, error=stderr)
                return ToolResult(success=True, data=stdout or "工作树干净")

            if action == "add":
                stdout, stderr, code = repo.run_git("add", "-A")
                if code != 0:
                    return ToolResult(success=False, error=stderr)
                return ToolResult(success=True, data="已暂存所有变更")

            if action == "commit":
                if not message:
                    return ToolResult(success=False, error="commit 需要 message 参数")
                stdout, stderr, code = repo.run_git("commit", "-m", message)
                if code != 0:
                    if "nothing to commit" in stderr.lower():
                        return ToolResult(success=True, data="没有需要提交的变更")
                    return ToolResult(success=False, error=stderr)
                return ToolResult(success=True, data=stdout)

            if action == "push":
                return self._smart_push(repo, config)

            if action == "pull":
                return self._smart_pull(repo, config)

            return ToolResult(success=False, error=f"未知操作: {action}")
        except Exception as e:
            return ToolResult(success=False, error=f"Git 操作失败: {e}")

    def _smart_pull(self, repo, config) -> ToolResult:
        """拉取前自动修复 git 状态：remote → 分支 → tracking → pull"""
        # 1. 检查并修复 remote
        stdout, stderr, code = repo.run_git("remote", "-v")
        has_remote = bool(stdout.strip())
        if code != 0 or not has_remote:
            if not config.git_repo_url:
                return ToolResult(
                    success=False,
                    error="未配置远程仓库: 请在 config.json 中设置 git.repo_url",
                )
            _, add_stderr, add_code = repo.run_git("remote", "add", "origin", config.git_repo_url)
            if add_code != 0:
                return ToolResult(success=False, error=f"添加远程仓库失败: {add_stderr}")

        # 2. 检查本地分支是否存在
        branches, _, _ = repo.run_git("branch")
        has_local_branch = bool(branches.strip())

        if not has_local_branch:
            # 空仓库：直接用 pull origin <branch> 拉取首次内容
            stdout, stderr, code = repo.run_git("pull", "origin", config.git_branch)
            if code != 0:
                return ToolResult(success=False, error=stderr)
            return ToolResult(success=True, data=stdout or "首次拉取成功")

        # 3. 检查 tracking 信息
        tracking, _, _ = repo.run_git("status", "-b", "--porcelain")
        has_tracking = "..." in (tracking.split("\n")[0] if tracking else "")

        if not has_tracking:
            # 先 fetch 确保远程 ref 是最新的
            repo.run_git("fetch", "origin")
            # 获取当前分支名
            current_branch = None
            for line in branches.split("\n"):
                line = line.strip()
                if line.startswith("*"):
                    current_branch = line.lstrip("* ").strip()
                    break
            if current_branch:
                repo.run_git(
                    "branch", "--set-upstream-to",
                    f"origin/{current_branch}", current_branch,
                )

        # 4. 执行 pull
        stdout, stderr, code = repo.run_git("pull")
        if code != 0:
            # fallback: 用显式远程+分支拉取
            stdout2, stderr2, code2 = repo.run_git("pull", "origin", config.git_branch)
            if code2 != 0:
                return ToolResult(success=False, error=stderr2)
            return ToolResult(success=True, data=stdout2 or "拉取成功")
        return ToolResult(success=True, data=stdout or "已是最新")

    @staticmethod
    def _smart_push(repo, config) -> ToolResult:
        """推送前检查 remote 配置，缺失时自动添加；本地分支不存在时先创建"""
        stdout, stderr, code = repo.run_git("remote", "-v")
        if code != 0:
            return ToolResult(
                success=False,
                error=f"无法检查远程仓库配置: {stderr}\n请确认 Git 仓库已初始化且 Git 可用。",
            )

        if not stdout:
            remote_url = config.git_repo_url
            if not remote_url:
                return ToolResult(
                    success=False,
                    error="未配置远程仓库: 请在 config.json 中设置 git.repo_url，或跳过 push 步骤",
                )
            _, stderr, code = repo.run_git("remote", "add", "origin", remote_url)
            if code != 0:
                return ToolResult(
                    success=False,
                    error=f"添加远程仓库失败: {stderr}\n请检查 config.json 中 git.repo_url 是否正确",
                )

        # 检查本地分支是否存在
        branches, _, _ = repo.run_git("branch")
        current_branch = None
        for line in branches.split("\n"):
            line = line.strip()
            if line.startswith("*"):
                current_branch = line.lstrip("* ").strip()
                break

        if not current_branch:
            # 本地无分支，先 fetch 再从远程创建
            _, fetch_err, fetch_code = repo.run_git("fetch", "origin")
            if fetch_code == 0:
                target = f"refs/heads/{config.git_branch}"
                remote_branches, _, _ = repo.run_git("ls-remote", "--heads", "origin")
                if target in remote_branches or remote_branches:
                    # 用配置的分支名创建本地分支
                    repo.run_git("checkout", "-b", config.git_branch)
                else:
                    # 远程也没有分支，创建新分支
                    repo.run_git("checkout", "-b", config.git_branch)
            else:
                # fetch 失败（可能是空远程），直接用配置的分支名创建
                repo.run_git("checkout", "-b", config.git_branch)

        # 推送并建立追踪
        stdout, stderr, code = repo.run_git("push", "-u", "origin", config.git_branch)
        if code != 0:
            return ToolResult(
                success=False,
                error=(
                    f"推送失败: {stderr}\n"
                    "（网络问题或远程仓库不可达，文件已在本地安全保存。"
                    "请稍后手动 git push，或检查 SSH/HTTPS 配置。）"
                ),
            )
        return ToolResult(success=True, data=stdout or "推送成功")


class GitStatusTool(BaseTool):
    """只读 Git 状态查询"""

    name = "git_status"
    description = "查看存储库的 Git 状态（工作区和暂存区变更）"
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def execute(self) -> ToolResult:
        from maa.storage.repo import RepoManager
        from maa.config import load_config

        config = load_config()
        repo = RepoManager(config.storage_root)
        stdout, stderr, code = repo.run_git("status", "--short")
        if code != 0:
            return ToolResult(success=False, error=stderr)
        return ToolResult(success=True, data=stdout or "工作树干净")


class GitRemoteInfoTool(BaseTool):
    """只读远程仓库信息查询"""

    name = "git_remote_info"
    description = "查看远程仓库 URL 和分支信息"
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def execute(self) -> ToolResult:
        from maa.storage.repo import RepoManager
        from maa.config import load_config

        config = load_config()
        repo = RepoManager(config.storage_root)
        stdout, stderr, code = repo.run_git("remote", "-v")
        if code != 0:
            return ToolResult(success=False, error=stderr)
        return ToolResult(success=True, data=stdout or "未配置远程仓库")


class PullToLocalTool(BaseTool):
    """将知识库中的文件/文件夹复制到本地指定目录"""

    name = "pull_to_local"
    description = (
        "将知识库中的文件或文件夹复制到本地任意目录。"
        "source_path 为知识库内相对路径（文件或文件夹），dest_dir 为本地目标目录绝对路径。"
        "文件夹会递归复制其下所有 .md 文件（跳过 .index.md），单文件则直接复制。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "source_path": {
                "type": "string",
                "description": "知识库内的相对路径，如 personal/intern-log.md 或 projects/immersive-avatar",
            },
            "dest_dir": {
                "type": "string",
                "description": "本地目标目录绝对路径，如 D:/InternWork/",
            },
        },
        "required": ["source_path", "dest_dir"],
    }

    def execute(self, source_path: str, dest_dir: str) -> ToolResult:
        import shutil
        from pathlib import Path
        from maa.storage.repo import RepoManager
        from maa.config import load_config

        config = load_config()
        repo = RepoManager(config.storage_root)
        src = repo.resolve_path(source_path)

        if not src.exists():
            return ToolResult(success=False, error=f"知识库中不存在: {source_path}")

        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)

        copied: list[str] = []
        if src.is_dir():
            for md_file in src.glob("*.md"):
                if md_file.name == ".index.md":
                    continue
                target = dest / md_file.name
                shutil.copy2(md_file, target)
                copied.append(str(target))
            # 也递归复制子目录下的 .md 文件
            for md_file in src.rglob("*.md"):
                if md_file.name == ".index.md" or md_file.parent == src:
                    continue
                rel = md_file.relative_to(src)
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(md_file, target)
                copied.append(str(target))
        else:
            target = dest / src.name
            shutil.copy2(src, target)
            copied.append(str(target))

        if not copied:
            return ToolResult(success=False, error=f"{source_path} 下没有可复制的 .md 文件")
        return ToolResult(success=True, data={"copied": copied, "count": len(copied)})
