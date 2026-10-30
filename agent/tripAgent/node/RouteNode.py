from datetime import date
from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from agent.prompts import system_prompt_config
from agent.tripAgent import prompts
from agent.tripAgent.AmapClient import amap_client
from agent.tripAgent.location import resolve_city_adcode, resolve_place
from agent.tripAgent.node.BaseTripNode import BaseTripNode
from agent.tripAgent.TripState import TripState
from agent.tripAgent.validation import haversine_km, parse_coords
from config import logger

# 交通方式 -> 中文名
TRANSPORT_LABELS = {
    "walking": "步行",
    "driving": "驾车",
    "transit": "公交/地铁",
}

# 自动选择交通方式时，直线距离不超过该值（公里）按步行规划
WALKING_MAX_KM = 3.0
# 自动步行方案超过该时长（分钟）时，改用驾车
MAX_AUTO_WALK_MIN = 45


class RouteNode(BaseTripNode):
    """
    路线推荐：
    1. 解析起点/终点为高德坐标（优先 POI 检索，回退地理编码）
    2. 按用户指定或距离自动选择步行/驾车/公交，调用高德路径规划
    3. 由 LLM 根据路径结果组织回答，经 SSE 流式输出
    """

    async def execute(self, state: TripState, config: RunnableConfig) -> Dict[str, Any]:
        origin_name = (state.get("origin") or "").strip()
        destination_name = (state.get("destination") or "").strip()
        city_name = (state.get("city") or "").strip()

        if not origin_name or not destination_name:
            return {"messages": [AIMessage(content=prompts.ROUTE_CLARIFY)]}

        origin = await resolve_place(origin_name, city_name)
        destination = await resolve_place(destination_name, city_name)
        if not origin or not destination:
            return {"messages": [AIMessage(content=prompts.ROUTE_FAILED.format(
                origin=origin_name,
                destination=destination_name,
            ))]}

        if origin["coords"] == destination["coords"]:
            return {"messages": [AIMessage(content="起点和终点是同一个地点，请确认后重新告诉我。")]}

        straight_km = haversine_km(origin["coords"], destination["coords"])
        requested_transport = state.get("transport")
        auto_transport = requested_transport not in TRANSPORT_LABELS
        transport = requested_transport if not auto_transport else (
            "walking" if straight_km <= WALKING_MAX_KM else "driving"
        )

        route = await self._plan_route(transport, origin, destination, city_name)

        # 自动模式下，步行耗时过长（如遇水域/山路绕行）时改用驾车
        if auto_transport and transport == "walking" and (
                route is None or route["duration_min"] > MAX_AUTO_WALK_MIN
        ):
            driving = await self._plan_route("driving", origin, destination, city_name)
            if driving:
                transport = "driving"
                route = driving

        if route is None and transport == "transit":
            # 公交失败时回退驾车，避免直接返回错误
            transport = "driving"
            route = await self._plan_route(transport, origin, destination, city_name)

        if route is None:
            return {"messages": [AIMessage(content=prompts.ROUTE_FAILED.format(
                origin=origin_name,
                destination=destination_name,
            ))]}

        params = {
            "origin": origin_name,
            "destination": destination_name,
            "city": city_name or origin.get("city") or destination.get("city") or "未知",
            "transport_label": TRANSPORT_LABELS[transport],
            "distance_km": round(route["distance_m"] / 1000, 1),
            "duration_min": route["duration_min"],
            "today": date.today().isoformat(),
        }
        response = await self.chat_llm().ainvoke(
            [
                SystemMessage(content=system_prompt_config.route_prompt.format(**params)),
                HumanMessage(content=f"请给出从{origin_name}到{destination_name}的路线建议。"),
            ],
            config,
        )
        return {"messages": [response]}

    # ------------------ 地点解析 ------------------

    async def _resolve_place(self, name: str, city: str) -> Optional[Dict[str, Any]]:
        """
        把地点名解析为坐标。

        优先在指定城市内做 POI 检索（避免“灵隐寺”被地理编码到同名异地），
        没有城市或检索失败时回退地理编码。
        """
        coords = parse_coords(name)
        if coords:
            return {"name": name, "coords": coords, "city": city, "adcode": None}

        if city:
            try:
                pois = await amap_client.search_poi(name, city, limit=1)
                if pois:
                    return {
                        "name": pois[0].get("name") or name,
                        "coords": pois[0]["coords"],
                        "city": city,
                        "adcode": None,
                    }
            except Exception as e:
                logger.debug("POI 解析 %s 失败，回退地理编码：%s", name, e)

        try:
            geo = await amap_client.geocode(name)
        except Exception as e:
            logger.warning("地理编码 %s 失败：%s", name, e)
            return None

        if not geo.get("location"):
            return None

        return {
            "name": name,
            "coords": geo["location"],
            "city": geo.get("city") or city,
            "adcode": geo.get("adcode"),
        }

    # ------------------ 路径规划 ------------------

    async def _plan_route(
            self,
            transport: str,
            origin: Dict[str, Any],
            destination: Dict[str, Any],
            city_name: str,
    ) -> Optional[Dict[str, Any]]:
        if transport == "walking":
            return await amap_client.walking_route(origin["coords"], destination["coords"])

        if transport == "driving":
            return await amap_client.driving_route(origin["coords"], destination["coords"])

        if transport == "transit":
            city1_name = origin.get("city") or city_name
            city2_name = destination.get("city") or city_name
            city1 = await resolve_city_adcode(city1_name)
            city2 = city1 if city2_name == city1_name else await resolve_city_adcode(city2_name)
            return await amap_client.transit_route(
                origin["coords"],
                destination["coords"],
                city1,
                city2,
            )

        return None
