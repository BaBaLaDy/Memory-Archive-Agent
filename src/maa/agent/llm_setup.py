"""LLM 创建与工具绑定"""

from langchain_openai import ChatOpenAI


def create_llm(
    model: str,
    api_key: str | None,
    api_base: str | None,
    extra_body: dict | None,
) -> ChatOpenAI:
    """从配置参数创建 ChatOpenAI 实例"""
    kwargs: dict = {
        "model": model,
        "api_key": api_key or "",
        "temperature": 0.1,  # 降低随机性，减少工具调用幻觉
    }
    if api_base:
        kwargs["base_url"] = api_base
    if extra_body:
        kwargs["extra_body"] = extra_body
    return ChatOpenAI(**kwargs)
