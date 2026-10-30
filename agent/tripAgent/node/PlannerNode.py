from datetime import date
from typing import Any, Dict

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from agent.prompts import system_prompt_config
from agent.tripAgent.constants import DEFAULT_CROWD, DEFAULT_DAYS, MAX_TOOL_ROUNDS
from agent.tripAgent.node.BaseTripNode import BaseTripNode
from agent.tripAgent.tools import AMAP_TOOLS
from agent.tripAgent.TripState import TripState
from agent.tripAgent.utils import current_turn_messages, previous_plan
from util import JsonUtil


class PlannerNode(BaseTripNode):
    """规划 LLM：绑定工具，循环收集天气 / POI / 美食信息"""

    def __init__(self, provider: str = "openai"):
        super().__init__(provider)
        self.planner_llm = self.create_llm(0.5, "TripPlanner").bind_tools(AMAP_TOOLS)

    async def execute(self, state: TripState, config: RunnableConfig) -> Dict[str, Any]:
        rounds = int(state.get("tool_rounds") or 0)
        if rounds >= MAX_TOOL_ROUNDS:
            # 工具轮次耗尽，交给结构化输出
            return {}

        system_prompt = system_prompt_config.planner_prompt.format(**self._planner_prompt_params(state))
        messages = [SystemMessage(content=system_prompt)] + current_turn_messages(state)

        response = await self.planner_llm.ainvoke(messages, config)
        # 标记为内部消息，避免会话历史把规划过程中的思考文本展示给用户
        metadata = dict(response.response_metadata or {})
        metadata["internal"] = True
        response = response.model_copy(update={"response_metadata": metadata})

        return {"messages": [response], "tool_rounds": rounds + 1}

    def route(self, state: TripState) -> str:
        """规划循环条件边：有工具调用且未超轮次 -> tools，否则 -> 结构化输出"""
        messages = state.get("messages") or []
        if messages:
            last_message = messages[-1]
            tool_calls = getattr(last_message, "tool_calls", None)
            rounds = int(state.get("tool_rounds") or 0)
            if tool_calls and rounds <= MAX_TOOL_ROUNDS:
                return "tools"
        return "format_plan"

    def _planner_prompt_params(self, state: TripState) -> Dict[str, Any]:
        assumptions = state.get("assumptions") or {}
        destination = state.get("destination") or ""
        last_plan = previous_plan(state, destination)

        return {
            "destination": destination,
            "city_adcode": state.get("city_adcode") or "未知",
            "weather_city": state.get("city_adcode") or destination,
            "days": state.get("days") or DEFAULT_DAYS,
            "crowd": state.get("crowd") or DEFAULT_CROWD,
            "today": date.today().isoformat(),
            "assumption_notes": "；".join(assumptions.get("notes") or []) or "无",
            "previous_plan": JsonUtil.to_str(last_plan) if last_plan else "无",
        }
