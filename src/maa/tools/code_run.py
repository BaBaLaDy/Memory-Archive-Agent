import re
import shlex
import subprocess
import sys
import platform
from maa.tools.base import BaseTool, ToolResult

# 禁止模式列表（正则），匹配则拒绝执行（跨平台通用）
FORBIDDEN_PATTERNS = [
    r"\brm\b",           # 删除文件
    r"\bdel\b",          # Windows 删除
    r"\brmdir\b",        # 删除目录
    r"\bformat\b",       # 格式化磁盘
    r"\bdd\b",           # 磁盘写入
    r"chmod\s+777",      # 危险权限
    r"\bsudo\b",         # 提权
    r"git\s+reset\s+--hard",  # 硬重置
    r"git\s+clean",      # 清理未跟踪文件
    r"git\s+push\s+.*--force",  # 强制推送
    r"git\s+push\s+.*-f\b",     # 强制推送简写
    r"pip\s+install",    # 安装包
    r"npm\s+install",    # 安装包
    r">\s*/dev/",        # 写入设备文件
    r"\bmv\b.*/dev/",    # 移动文件到设备
]


def _detect_shell() -> str:
    """检测当前环境可用的 Shell（用于 Agent 自主选择命令）"""
    if sys.platform != "win32":
        return "bash/zsh"

    # Windows: 检查 PowerShell 是否可用
    try:
        result = subprocess.run(
            ["powershell", "-Command", "$PSVersionTable.PSVersion"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return "CMD 和 PowerShell 均可用"
    except Exception:
        pass
    return "CMD"


def _build_description() -> str:
    """动态生成工具描述，包含当前平台信息，让 LLM 自主选择命令"""
    os_name = platform.system()
    shell_info = _detect_shell()

    if sys.platform == "win32":
        return (
            f"执行只读诊断命令并返回 stdout、stderr 和返回码。"
            f"当前平台: **{os_name}**，可用 Shell: **{shell_info}**。"
            f"你可以使用 CMD 命令（dir、type、findstr、where）或 "
            f"PowerShell 命令（Get-ChildItem、Get-Content、Select-String、Get-Location）。"
            f"也可以直接执行 git、python 等跨平台命令。"
            f"仅限非破坏性诊断命令，超时 30 秒。"
        )
    else:
        return (
            f"执行只读诊断命令并返回 stdout、stderr 和返回码。"
            f"当前平台: **{os_name}**，Shell: **{shell_info}**。"
            f"可以执行常见的 Unix 诊断命令（ls、cat、grep、which 等）以及 git、python 命令。"
            f"仅限非破坏性诊断命令，超时 30 秒。"
        )


class CodeRunTool(BaseTool):
    """执行诊断命令（LLM 根据平台自主选择命令，不做硬编码翻译）"""

    name = "code_run"
    description = _build_description()
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的诊断命令（根据当前平台选择正确的命令）"},
            "cwd": {"type": "string", "description": "工作目录（默认：存储根目录）"},
        },
        "required": ["command"],
    }

    def execute(self, command: str, cwd: str | None = None) -> ToolResult:
        from maa.config import load_config

        # --- 安全检查：黑名单匹配（跨平台，不可绕过）---
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return ToolResult(
                    success=False,
                    error=f"安全拒绝：命令包含禁止模式 '{pattern}'，匹配: {re.search(pattern, command, re.IGNORECASE).group()}",
                )

        config = load_config()
        working_dir = cwd or config.storage_root

        if sys.platform == "win32":
            return self._run_with_shell(command, working_dir)
        else:
            return self._run_without_shell(command, working_dir)

    @staticmethod
    def _run_with_shell(command: str, cwd: str) -> ToolResult:
        """使用 shell=True 执行（Windows CMD/PowerShell 均适用）"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd,
            )
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            data = {"stdout": stdout, "stderr": stderr, "returncode": result.returncode}
            if result.returncode != 0:
                return ToolResult(
                    success=False,
                    data=data,
                    error=f"命令返回非零: {result.returncode}\n{stderr}",
                )
            return ToolResult(success=True, data=data)
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="命令超时（30 秒）")
        except Exception as e:
            return ToolResult(success=False, error=f"命令执行失败: {e}")

    @staticmethod
    def _run_without_shell(command: str, cwd: str) -> ToolResult:
        """Unix: shlex.split + shell=False（更安全）"""
        try:
            args = shlex.split(command)
            result = subprocess.run(
                args,
                shell=False,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=cwd,
            )
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            data = {"stdout": stdout, "stderr": stderr, "returncode": result.returncode}
            if result.returncode != 0:
                return ToolResult(
                    success=False,
                    data=data,
                    error=f"命令返回非零: {result.returncode}\n{stderr}",
                )
            return ToolResult(success=True, data=data)
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="命令超时（30 秒）")
        except FileNotFoundError as e:
            return ToolResult(success=False, error=f"命令未找到: {e}")
        except Exception as e:
            return ToolResult(success=False, error=f"命令执行失败: {e}")
