import asyncio
import sys
import os

# 修复 Windows GBK 编码问题
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

import click

from maa.channels.cli import run_repl


@click.command()
@click.option("--config", "config_path", default=None, help="配置文件路径")
def main(config_path: str | None = None):
    """Memory Archive Agent (MAA) - 个人记忆归档 CLI"""
    asyncio.run(run_repl(config_path))


if __name__ == "__main__":
    main()
