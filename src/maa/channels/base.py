from dataclasses import dataclass


@dataclass
class AgentInput:
    """通道转换后的标准输入"""
    text: str
    file_paths: list[str] | None = None
    user_id: str = "default"


class ChannelAdapter:
    """所有通道的统一接口"""

    def receive(self, raw_input) -> AgentInput:
        """将通道原始输入转为 Agent 标准格式"""
        raise NotImplementedError

    def send(self, agent_output: str) -> None:
        """将 Agent 回复发送到通道"""
        raise NotImplementedError

    def send_file(self, file_path: str) -> None:
        """发送文件到通道"""
        raise NotImplementedError
