"""SSE 流式输出工具，将 StreamEvent 转为 Server-Sent Events 文本"""

from maa.agent.engine import StreamEvent, StreamEventType


def stream_event_to_sse(event: StreamEvent) -> str:
    """将单个 StreamEvent 转为 SSE 文本行"""
    event_type = event.type.value
    data = event.data

    if data is None:
        payload = ""
    elif isinstance(data, str):
        payload = data.replace("\n", "\\n")
    else:
        import json
        payload = json.dumps(data, ensure_ascii=False)

    return f"event: {event_type}\ndata: {payload}\n\n"
