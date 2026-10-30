from typing import Any, Dict, List

from langchain_core.runnables import RunnableConfig

from agent.tripAgent import prompts
from agent.tripAgent.AmapClient import amap_client
from agent.tripAgent.constants import DEFAULT_BUDGET_LEVEL, DEFAULT_CROWD, DEFAULT_DAYS
from agent.tripAgent.node.BaseTripNode import BaseTripNode
from agent.tripAgent.schemas import CROWD_TYPES
from agent.tripAgent.TripState import TripState
from config import logger


class ParamFillNode(BaseTripNode):
    """
    参数补全：
    - destination 缺失 -> 追问（唯一硬性阻断）
    - 天数默认 3 天、人群默认 general、预算默认 economy，并写入 assumptions
    - 调用高德地理编码把目的地转为 adcode，供天气查询使用
    """

    async def execute(self, state: TripState, config: RunnableConfig) -> Dict[str, Any]:
        destination = (state.get("destination") or "").strip()
        if not destination:
            return {
                "need_clarification": True,
                "clarification_question": prompts.CLARIFY_DESTINATION,
            }

        days = state.get("days") or DEFAULT_DAYS
        crowd = state.get("crowd")
        if crowd not in CROWD_TYPES:
            crowd = DEFAULT_CROWD

        notes: List[str] = []
        if not state.get("days"):
            notes.append(f"未指定天数，默认 {DEFAULT_DAYS} 天")
        if not state.get("crowd"):
            notes.append("未指定同行人群，默认普通人群")
        notes.append("未指定预算，默认按经济型规划")

        assumptions = {
            "days": int(days),
            "crowd": crowd,
            "budget_level": DEFAULT_BUDGET_LEVEL,
            "notes": notes,
        }

        # 目的地每次都可能变化，这里重新地理编码
        adcode = None
        try:
            geo = await amap_client.geocode(destination)
            adcode = geo.get("adcode") or None
        except Exception as e:
            logger.warning("目的地 %s 地理编码失败：%s", destination, e)

        return {
            "destination": destination,
            "days": int(days),
            "crowd": crowd,
            "budget_level": DEFAULT_BUDGET_LEVEL,
            "city_adcode": adcode,
            "assumptions": assumptions,
            "need_clarification": False,
        }

    def route(self, state: TripState) -> str:
        """参数补全条件边：缺目的地 -> 追问，否则 -> 规划"""
        return "clarify" if state.get("need_clarification") else "planner"
