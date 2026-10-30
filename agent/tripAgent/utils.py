"""tripAgent 节点共用的消息、JSON 工具函数。"""

from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage

from agent.tripAgent.TripState import TripState
from util import JsonUtil


def current_turn_messages(state: TripState) -> List[Any]:
    """截取本轮消息（最后一条 HumanMessage 及之后的内容）"""
    messages = state.get("messages") or []
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            return list(messages[index:])
    return list(messages)


def intent_history(state: TripState) -> List[Any]:
    """意图识别只保留有文本内容的用户/助手消息，避免工具调用污染上下文"""
    history = []
    for message in state.get("messages") or []:
        if isinstance(message, HumanMessage):
            history.append(message)
        elif isinstance(message, AIMessage) and message.content and not getattr(message, "tool_calls", None):
            if not (message.response_metadata or {}).get("internal"):
                history.append(message)
    return history[-8:]


def previous_plan(state: TripState, destination: str) -> Optional[Dict[str, Any]]:
    """只有目的地相同时，才把上一版行程作为修改参考"""
    plan = state.get("plan")
    if plan and plan.get("destination") == destination:
        return plan
    return None


def content_to_text(content: Any) -> str:
    """把模型返回的 content 统一转成字符串"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """从模型输出中截取第一个 JSON 对象"""
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return JsonUtil.to_obj(text[start:end + 1])
    except Exception:
        return None
