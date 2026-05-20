import os
import subprocess
from pathlib import Path


CATEGORIES = ["projects", "research", "personal", "inbox"]


class RepoManager:
    """管理 MemoryArchive 仓库的初始化和路径解析"""

    def __init__(
        self,
        root: str,
        remote_url: str | None = None,
        branch: str | None = None,
    ):
        self.root = Path(root).expanduser().resolve()
        self._remote_url = remote_url
        self._branch = branch or "main"

    def ensure_initialized(self) -> None:
        """创建目录结构和 Git 仓库（若已存在则跳过），并自动关联远程仓库"""
        self.root.mkdir(parents=True, exist_ok=True)

        meta = self.root / ".ama"
        meta.mkdir(exist_ok=True)

        for cat in CATEGORIES:
            (self.root / cat).mkdir(exist_ok=True)

        git_dir = self.root / ".git"
        if not git_dir.exists():
            self._run_git("init", cwd=str(self.root))

        # 自动关联远程仓库（当配置了 repo_url 且尚未关联时）
        self.ensure_remote()

    def ensure_remote(self) -> None:
        """检查并自动关联远程仓库，失败时不抛异常"""
        if not self._remote_url:
            return

        # 检查是否已存在 remote origin
        stdout, stderr, code = self.run_git("remote", "-v")
        if code == 0 and stdout:
            return  # remote 已存在，跳过

        # 添加 remote
        _, add_stderr, add_code = self.run_git("remote", "add", "origin", self._remote_url)
        if add_code != 0:
            return  # 不抛异常，允许继续本地操作

        # 尝试 fetch 远程以建立追踪信息（失败不阻塞）
        self.run_git("fetch", "origin")

        # 如果本地没有分支，尝试从远程创建
        branches, _, _ = self.run_git("branch")
        if not branches.strip():
            # 远程有分支则 checkout，否则创建空分支
            remote_branches, _, _ = self.run_git("ls-remote", "--heads", "origin")
            if remote_branches:
                # 查找配置的分支
                target = f"refs/heads/{self._branch}"
                if target in remote_branches:
                    self.run_git("checkout", "-b", self._branch)
                    self.run_git(
                        "branch", "--set-upstream-to",
                        f"origin/{self._branch}", self._branch,
                    )
                else:
                    # 用远程第一个分支
                    first = remote_branches.split("\n")[0]
                    branch_name = first.split("/")[-1]
                    self.run_git("checkout", "-b", branch_name)
                    self.run_git(
                        "branch", "--set-upstream-to",
                        f"origin/{branch_name}", branch_name,
                    )
            else:
                # 远程也没有分支，创建本地初始分支
                self.run_git("checkout", "-b", self._branch)

    def resolve_path(self, relative_path: str) -> Path:
        """将相对路径解析为存储根目录下的绝对路径"""
        return (self.root / relative_path).resolve()

    def run_git(self, *args: str) -> tuple[str, str, int]:
        """执行 Git 命令，返回 (stdout, stderr, returncode)"""
        return self._run_git(*args, cwd=str(self.root))

    @staticmethod
    def _run_git(*args: str, cwd: str) -> tuple[str, str, int]:
        try:
            result = subprocess.run(
                ["git", *args],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=30,
            )
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            return stdout, stderr, result.returncode
        except FileNotFoundError:
            return "", "git 命令未找到，请确认已安装 Git 并加入 PATH", 127
        except subprocess.TimeoutExpired:
            return "", "Git 命令超时（30 秒）", 124
        except Exception as e:
            return "", f"Git 命令执行异常: {e}", 1
