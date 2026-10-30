from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from agent.tripAgent.TripState import TripState
from agent.tripAgent.utils import current_turn_messages
from config import config_manager

# 问答与 JSON 兜底共用 LLM 实例（按 provider 缓存，避免重复创建）
_CHAT_LLM_CACHE: Dict[str, Any] = {}


class BaseTripNode(ABC):
    """
    tripAgent 节点抽象基类。

    统一约定：
    - 子类实现 execute(state, config)，返回 LangGraph 状态增量
    - 带分支的节点实现 route(state)，供条件边使用
    - 需要 LLM 的节点通过 create_llm() 创建，tag 用于 Langfuse 追踪
    """

    def __init__(self, provider: str = "openai"):
        self.provider = provider

    # ------------------ 子类实现 ------------------

    @abstractmethod
    async def execute(self, state: TripState, config: RunnableConfig) -> Dict[str, Any]:
        """执行节点逻辑，返回状态增量"""

    def route(self, state: TripState) -> str:
        """条件边路由方法，只有带分支的节点需要实现"""
        raise NotImplementedError(f"{self.__class__.__name__} 不支持条件路由")

    # ------------------ LLM 工厂 ------------------

    @property
    def default_temperature(self) -> float:
        """问答节点使用的默认温度"""
        return float(config_manager.get(f"ai.{self.provider}.temperature", 0.7))

    def create_llm(
            self,
            temperature: float,
            tag: str,
            timeout: Optional[int] = None,
            extra_body: Optional[Dict[str, Any]] = None,
    ):
        """按统一配置创建 LLM 实例"""
        prefix = f"ai.{self.provider}"
        kwargs = {"extra_body": extra_body} if extra_body else {}
        return init_chat_model(
            model=config_manager.get(f"{prefix}.model"),
            model_provider="openai",
            api_key=config_manager.get(f"{prefix}.api-key"),
            base_url=config_manager.get(f"{prefix}.base-url"),
            temperature=temperature,
            timeout=timeout or int(config_manager.get(f"{prefix}.timeout", 60)),
            tags=[tag],
            **kwargs,
        )

    def create_structured_llm(self, schema: Any, temperature: float, tag: str):
        """
        创建结构化输出 LLM。

        DeepSeek 推理模型（deepseek-v4-pro）不支持 json_schema 响应格式，
        思考模式下也不支持 with_structured_output 使用的强制 tool_choice，
        因此按配置关闭思考模式，并改用 function_calling 方式抽取。
        """
        prefix = f"ai.{self.provider}"
        extra_body = None
        if config_manager.get(f"{prefix}.structured-output.disable-thinking", False):
            extra_body = {"thinking": {"type": "disabled"}}

        structured_timeout = config_manager.get(f"{prefix}.structured-output.timeout")
        return self.create_llm(
            temperature,
            tag,
            timeout=int(structured_timeout) if structured_timeout else None,
            extra_body=extra_body,
        ).with_structured_output(schema, method="function_calling")

    def chat_llm(self):
        """问答节点与 JSON 兜底共用的 LLM"""
        if self.provider not in _CHAT_LLM_CACHE:
            _CHAT_LLM_CACHE[self.provider] = self.create_llm(
                self.default_temperature,
                "TripAnswer",
            )
        return _CHAT_LLM_CACHE[self.provider]

    # ------------------ 通用逻辑 ------------------

    @staticmethod
    def trip_context(state: TripState) -> str:
        """汇总当前行程上下文，供问答类节点注入提示词"""
        parts = []
        if state.get("destination"):
            parts.append(f"目的地：{state['destination']}")
        if state.get("days"):
            parts.append(f"天数：{state['days']}")
        if state.get("crowd"):
            parts.append(f"同行人群：{state['crowd']}")
        return "；".join(parts) or "无"

    async def answer(self, state: TripState, config: RunnableConfig, system_prompt: str):
        """通用流式问答：注入系统提示词，只保留本轮消息"""
        messages = [SystemMessage(content=system_prompt)] + current_turn_messages(state)
        response = await self.chat_llm().ainvoke(messages, config)
        return {"messages": [response]}
