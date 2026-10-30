"""打车相关的用户输入与车型匹配工具。"""

import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage

from agent.tripAgent.TripState import TripState
from agent.tripAgent.utils import content_to_text

_CN_NUMBERS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8}


def last_user_text(state: TripState) -> str:
    """获取本轮最后一条用户消息文本"""
    for message in reversed(state.get("messages") or []):
        if isinstance(message, HumanMessage):
            return content_to_text(message.content)
    return ""


def find_vehicle(text: str, vehicles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    从用户回复中匹配车型。

    支持：车型名称（特惠快车/快车/专车/豪华车）、品类代码（201/1/8/17）、
    序号（1/第一个）以及“特惠”“豪华”等简称。
    """
    text = (text or "").strip()
    if not text or not vehicles:
        return None

    lower = text.lower()
    for vehicle in vehicles:
        name = str(vehicle.get("name") or "").strip()
        if name and name.lower() in lower:
            return vehicle

    for vehicle in vehicles:
        category = str(vehicle.get("category") or "").strip()
        if category and category == text:
            return vehicle

    if text.isdigit() and 1 <= int(text) <= len(vehicles):
        return vehicles[int(text) - 1]

    match = re.search(r"第\s*([一二三四五六七八1-8])\s*(?:个|种)?", text)
    if match:
        raw = match.group(1)
        index = int(raw) if raw.isdigit() else _CN_NUMBERS.get(raw)
        if index and 1 <= index <= len(vehicles):
            return vehicles[index - 1]

    for alias, keyword in (("特惠", "特惠"), ("豪华", "豪华"), ("专车", "专车"), ("快车", "快车")):
        if alias in lower:
            for vehicle in vehicles:
                if keyword in str(vehicle.get("name") or ""):
                    return vehicle

    return None
