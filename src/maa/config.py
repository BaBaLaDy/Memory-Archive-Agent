import json
import os
from pathlib import Path

# 敏感字段的环境变量名映射
# key: 环境变量名, value: (config 路径元组, 默认值)
# 环境变量优先级高于 config.json，用于注入密钥等敏感信息
_SENSITIVE_ENV_MAP = {
    "DASHSCOPE_API_KEY":      (("llm", "api_key"), ""),
    "MAA_TELEGRAM_BOT_TOKEN": (("channels", "telegram", "bot_token"), ""),
    "MAA_FEISHU_APP_ID":      (("channels", "feishu", "app_id"), ""),
    "MAA_FEISHU_APP_SECRET":  (("channels", "feishu", "app_secret"), ""),
    "MAA_FIRECRAWL_API_KEY":  (("tools", "firecrawl_api_key"), ""),
    # 向后兼容旧变量名
    "FIRECRAWL_API_KEY":      (("tools", "firecrawl_api_key"), ""),
}

# 保存 config.json 时需要剥离的敏感字段路径（这些字段只存在于 .env，不写回 json）
_STRIP_ON_SAVE = [
    ("llm", "api_key"),
    ("channels", "telegram", "bot_token"),
    ("channels", "feishu", "app_id"),
    ("channels", "feishu", "app_secret"),
    ("tools", "firecrawl_api_key"),
]


def _load_dotenv():
    """加载项目根目录的 .env 文件（若存在）"""
    project_root = Path(__file__).resolve().parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            pass  # python-dotenv 未安装时降级


def _deep_set(data: dict, keys: tuple, value):
    """在嵌套 dict 中按路径设置值，中间不存在的 dict 自动创建"""
    for key in keys[:-1]:
        data = data.setdefault(key, {})
    data[keys[-1]] = value


def _deep_del(data: dict, keys: tuple):
    """在嵌套 dict 中按路径删除叶子键，空父节点一并清理"""
    if not keys:
        return
    *parents, leaf = keys
    for key in parents:
        if key not in data or not isinstance(data[key], dict):
            return
        data = data[key]
    data.pop(leaf, None)


def _inject_env_overrides(data: dict):
    """将环境变量中的敏感值注入到配置 dict 中，优先于文件中的值"""
    for env_var, (keys, default) in _SENSITIVE_ENV_MAP.items():
        val = os.environ.get(env_var, "")
        if val:
            _deep_set(data, keys, val)


DEFAULT_CONFIG = {
    "llm": {
        "provider": "dashscope",
        "model": "qwen3.6-plus",
        "extra_body": {"enable_thinking": False},
    },
    "git": {
        "repo_url": "",
        "branch": "main",
    },
    "storage": {
        "root": "~/MemoryArchive",
    },
    "categories": ["projects", "research", "personal", "inbox"],
    "channels": {
        "cli": {"enabled": True},
        "mcp": {"enabled": False, "port": 3000},
        "telegram": {"enabled": False},
        "feishu": {"enabled": False},
    },
}


class Config:
    def __init__(self, data: dict):
        self._raw = data
        llm = data.get("llm", {})
        git = data.get("git", {})
        storage = data.get("storage", {})
        tools = data.get("tools", {})

        self.llm_provider = llm.get("provider", "dashscope")
        self.llm_model = llm.get("model", "qwen3.6-plus")
        self.api_key = llm.get("api_key", "")
        self.api_base = llm.get("api_base", "")
        self.extra_body = llm.get("extra_body", {})
        self.git_repo_url = git.get("repo_url", "")
        self.git_branch = git.get("branch", "main")
        self.storage_root = storage.get("root", "~/MemoryArchive")
        self.categories = data.get("categories", DEFAULT_CONFIG["categories"])
        self.channels = data.get("channels", DEFAULT_CONFIG["channels"])
        self.firecrawl_api_key = tools.get("firecrawl_api_key", "")

    @property
    def config_path(self) -> Path | None:
        return self._raw.get("_config_path")


def load_config(config_path: str | None = None) -> Config:
    """加载配置文件，不存在时返回默认配置"""
    _load_dotenv()  # 优先加载 .env，允许后续 os.environ.get 生效

    if config_path:
        path = Path(config_path).expanduser().resolve()
    else:
        # 优先当前工作目录，再找项目根，最后 ~/.maa/
        candidates = [
            Path.cwd() / "config.json",
            Path(__file__).resolve().parent.parent.parent / "config.json",
            Path.home() / ".ama" / "config.json",
        ]
        path = None
        for p in candidates:
            if p.exists():
                path = p
                break
        if path is None:
            path = candidates[-1]

    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data["_config_path"] = str(path)
    else:
        data = dict(DEFAULT_CONFIG)

    # 环境变量优先于配置文件（敏感字段从 .env 注入）
    _inject_env_overrides(data)

    return Config(data)


def validate_config(config: Config) -> list[str]:
    """验证配置，返回错误列表"""
    errors = []
    if not config.api_key:
        errors.append("未配置 LLM API Key，请设置环境变量 DASHSCOPE_API_KEY 或在 config.json 中设置 llm.api_key")
    storage = Path(config.storage_root).expanduser()
    if storage.exists() and not storage.is_dir():
        errors.append(f"存储路径不是目录: {storage}")
    return errors


def save_config(config: Config, path: str | None = None) -> None:
    """保存配置到文件"""
    if path:
        save_path = Path(path).expanduser().resolve()
    elif config.config_path:
        save_path = Path(config.config_path)
    else:
        save_path = Path.home() / ".ama" / "config.json"

    save_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "llm": {
            "provider": config.llm_provider,
            "model": config.llm_model.split("/", 1)[1] if "/" in config.llm_model else config.llm_model,
            "api_base": config.api_base,
            "extra_body": config.extra_body,
        },
        "git": {
            "repo_url": config.git_repo_url,
            "branch": config.git_branch,
        },
        "storage": {"root": config.storage_root},
        "categories": config.categories,
        "channels": config.channels,
    }
    # 剥离敏感字段——这些值来自 .env，不写入 config.json
    for keys in _STRIP_ON_SAVE:
        _deep_del(data, keys)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
