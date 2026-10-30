from typing import Any, Dict, List, Optional

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from agent.prompts import system_prompt_config
from agent.tripAgent.constants import DEFAULT_BUDGET_LEVEL, INTENT_TO_NODE
from agent.tripAgent.node.BaseTripNode import BaseTripNode
from agent.tripAgent.schemas import CROWD_TYPES, IntentResult
from agent.tripAgent.taxi_utils import find_vehicle, last_user_text
from agent.tripAgent.TripState import TripState
from agent.tripAgent.utils import content_to_text, extract_json, intent_history
from config import logger


class IntentNode(BaseTripNode):
    """意图识别 + 出行参数抽取"""

    def __init__(self, provider: str = "openai"):
        super().__init__(provider)
        self.intent_llm = self.create_structured_llm(IntentResult, 0.1, "TripIntent")

    async def execute(self, state: TripState, config: RunnableConfig) -> Dict[str, Any]:
        messages = [SystemMessage(content=system_prompt_config.intent_prompt)] + intent_history(state)

        result: Optional[IntentResult] = None
        try:
            result = await self.intent_llm.ainvoke(messages, config)
            logger.info(f"Intent: {result}")
        except Exception as e:
            # 结构化输出失败时，用普通 JSON 提示词兜底
            logger.warning("意图识别结构化输出失败，尝试 JSON 兜底：%s", e)
            try:
                result = await self._fallback_intent(messages, config)
            except Exception:
                logger.exception("出行意图识别失败，降级为 OTHER")

        previous_destination = state.get("destination")
        intent = "OTHER"
        destination = previous_destination
        origin = state.get("origin")
        city = state.get("city")
        transport = state.get("transport")
        vehicle_type = state.get("vehicle_type")
        days = state.get("days")
        crowd = state.get("crowd")

        if result is not None:
            if result.intent in INTENT_TO_NODE:
                intent = result.intent

            extracted_destination = (result.destination or "").strip()
            # 从“无目的地”补全为具体城市时，仍然属于同一段行程；只有明确换了城市才重置天数/人群
            destination_changed = (
                    bool(previous_destination)
                    and bool(extracted_destination)
                    and extracted_destination != previous_destination
            )
            if extracted_destination:
                destination = extracted_destination

            if result.days is not None and result.days > 0:
                days = result.days
            elif destination_changed:
                # 换了目的地视为新行程，不沿用上一段行程的天数
                days = None

            if result.crowd in CROWD_TYPES:
                crowd = result.crowd
            elif destination_changed:
                crowd = None

            if intent in ("ROUTE", "TAXI"):
                extracted_origin = (result.origin or "").strip()
                if extracted_origin:
                    origin = extracted_origin
                extracted_city = (result.city or "").strip()
                if extracted_city:
                    city = extracted_city
                if intent == "ROUTE" and result.transport in ("walking", "driving", "transit"):
                    transport = result.transport
                if intent == "TAXI":
                    extracted_vehicle = (result.vehicle_type or "").strip()
                    if extracted_vehicle:
                        vehicle_type = extracted_vehicle
                    elif destination_changed:
                        # 换了目的地视为新打车请求，不沿用上一次选择的车型
                        vehicle_type = None

        # 上一轮在等待选择打车车型时，用户只回复车型名/序号也视为 TAXI
        pending_estimate = state.get("taxi_estimate")
        if pending_estimate and intent != "TAXI":
            matched_vehicle = find_vehicle(
                last_user_text(state),
                pending_estimate.get("vehicles") or [],
            )
            if matched_vehicle:
                intent = "TAXI"
                vehicle_type = matched_vehicle.get("name")

        if intent not in ("ROUTE", "TAXI"):
            # 非路线/打车意图清理起终点字段，避免影响后续轮次
            origin = None
            city = None
        if intent != "ROUTE":
            transport = None
        if intent != "TAXI":
            vehicle_type = None

        # 本轮字段复位；plan 保留，供后续“修改行程”类请求参考
        return {
            "intent": intent,
            "destination": destination,
            "origin": origin,
            "city": city,
            "transport": transport,
            "vehicle_type": vehicle_type,
            "taxi_estimate": state.get("taxi_estimate") if intent == "TAXI" else None,
            "days": days,
            "crowd": crowd,
            "budget_level": DEFAULT_BUDGET_LEVEL,
            "need_clarification": False,
            "clarification_question": None,
            "tool_rounds": 0,
            "warnings": [],
            "validation_status": "pending",
        }

    async def _fallback_intent(self, messages: List[Any], config: RunnableConfig) -> IntentResult:
        """意图识别 JSON 兜底"""
        fallback_messages = [
            SystemMessage(
                content=(
                    f"{system_prompt_config.intent_prompt}\n\n"
                    f"{system_prompt_config.intent_json_instruction}"
                )
            )
        ] + messages[1:]

        response = await self.chat_llm().ainvoke(fallback_messages, config)
        data = extract_json(content_to_text(response.content))
        if data is None:
            raise ValueError("意图识别未返回有效 JSON")
        return IntentResult.model_validate(data)

    def route(self, state: TripState) -> str:
        """根图条件边：意图 -> 节点"""
        intent = state.get("intent", "OTHER")
        return intent if intent in INTENT_TO_NODE else "OTHER"
