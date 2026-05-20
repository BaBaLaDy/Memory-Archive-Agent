"""MAA HTTP API Server 入口

用法:
    python server.py              # 默认监听 127.0.0.1:8899
    python server.py --port 8900  # 指定端口
"""

import sys
import os
from pathlib import Path

# 修复 Windows GBK 编码问题：强制 stdout/stderr 使用 UTF-8
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# 确保项目根在 sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from maa.server.routes import router

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title="Memory Archive Agent API",
        description="个人长期数字记忆基础设施 HTTP API",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MAA HTTP API Server")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    parser.add_argument("--port", type=int, default=8899, help="监听端口（默认 8899）")
    args = parser.parse_args()

    print(f"MAA Server starting on http://{args.host}:{args.port}")
    print("API docs: http://127.0.0.1:8899/docs")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
