import uuid
from datetime import datetime
from typing import Any, Dict, List

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from agent.tripAgent import prompts
from agent.tripAgent.AmapClient import amap_client
from agent.tripAgent.didi_mcp import DidiMCPError, didi_mcp
from agent.tripAgent.location import resolve_place
from agent.tripAgent.node.BaseTripNode import BaseTripNode
from agent.tripAgent.taxi_utils import find_vehicle, last_user_text
from agent.tripAgent.TripState import TripState
from config import logger


class TaxiNode(BaseTripNode):
    """
    一键打车（滴滴 MCP 基础版）：

    1. 解析上车点/目的地坐标
    2. taxi_estimate 获取车型与预估价
    3. 用户选择车型后，taxi_generate_ride_app_link 生成跳转链接
       （实际下单在滴滴 App/小程序完成，不在本系统创建订单）

    未配置 DIDI_MCP_KEY 时保留演示实现：高德驾车路径 + taxi_cost 预估。
    """

    async def execute(self, state: TripState, config: RunnableConfig) -> Dict[str, Any]:
        pickup_name = (state.get("origin") or "").strip()
        destination_name = (state.get("destination") or "").strip()
        city_name = (state.get("city") or "").strip()

        if not pickup_name or not destination_name:
            return self._error(prompts.TAXI_CLARIFY)

        pickup = await resolve_place(pickup_name, city_name)
        destination = await resolve_place(destination_name, city_name)
        if not pickup or not destination:
            return self._error(prompts.TAXI_FAILED.format(
                origin=pickup_name,
                destination=destination_name,
            ))

        if didi_mcp.is_configured():
            return await self._didi_order(
                state, pickup_name, destination_name, city_name, pickup, destination, config
            )
        return await self._demo_order(
            pickup_name, destination_name, city_name, pickup, destination, config
        )

    # ------------------ 滴滴 MCP 基础版 ------------------

    async def _didi_order(
            self,
            state: TripState,
            pickup_name: str,
            destination_name: str,
            city_name: str,
            pickup: Dict[str, Any],
            destination: Dict[str, Any],
            config: RunnableConfig,
    ) -> Dict[str, Any]:
        request_id = (config.get("configurable") or {}).get("request_id")
        pending = self._pending_estimate(state, pickup_name, destination_name)
        selected_text = (state.get("vehicle_type") or "").strip()

        if not selected_text and pending:
            matched = find_vehicle(last_user_text(state), pending.get("vehicles") or [])
            if matched:
                selected_text = matched.get("name") or ""

        if pending:
            vehicles = pending.get("vehicles") or []
            trace_id = pending.get("trace_id")
            pickup_coords = pending.get("pickup_coords") or pickup["coords"]
            destination_coords = pending.get("destination_coords") or destination["coords"]
            if not vehicles:
                pending = None

        if not pending:
            try:
                estimate = await didi_mcp.estimate(pickup, destination)
            except DidiMCPError as e:
                logger.warning("滴滴 MCP 估价失败：%s", e)
                return self._error(f"滴滴打车服务暂时不可用：{e}")

            vehicles = estimate.get("vehicles") or []
            trace_id = estimate.get("trace_id")
            pickup_coords = pickup["coords"]
            destination_coords = destination["coords"]

            if not vehicles:
                raw = (estimate.get("text") or "").strip()
                if raw:
                    logger.warning("滴滴 MCP 未解析出车型，原始返回：%s", raw[:500])
                return self._error("滴滴暂未返回可用车型，请稍后重试。")

        selected = find_vehicle(selected_text, vehicles) if selected_text else None
        if not selected:
            # 未指定车型或选择不匹配：展示车型选择卡，等待用户选择
            return self._selection_card(
                pickup_name, destination_name, city_name, pickup, destination,
                vehicles, trace_id, request_id,
            )

        try:
            link = await didi_mcp.generate_link(
                {"name": pickup_name, "coords": pickup_coords},
                {"name": destination_name, "coords": destination_coords},
                category=selected.get("category"),
            )
        except DidiMCPError as e:
            logger.warning("滴滴 MCP 生成打车链接失败：%s", e)
            return self._error(f"滴滴打车服务暂时不可用：{e}")

        jump_url = link.get("url")
        if not jump_url:
            return self._error("滴滴未返回打车跳转链接，请稍后重试。")

        options = self._vehicle_options(vehicles)
        order = {
            "order_id": self._order_id(),
            "provider": "didi_mcp",
            "provider_name": "滴滴出行",
            "status": "PENDING_JUMP",
            "status_text": "请在滴滴 App/小程序中完成叫车",
            "pickup": pickup_name,
            "destination": destination_name,
            "city": city_name or pickup.get("city") or destination.get("city") or "",
            "vehicle_type": selected.get("name"),
            "vehicle_options": options,
            "estimated_fare": self._vehicle_price(selected),
            "coupon_fare": selected.get("coupon_price"),
            "currency": "CNY",
            "jump_url": jump_url,
            "jump_links": link.get("links") or {},
            "estimate_trace_id": trace_id,
            "simulated": False,
            "note": "通过滴滴 MCP 生成跳转链接，实际下单在滴滴 App/小程序完成",
            "request_id": request_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        logger.info("生成滴滴打车链接：%s %s -> %s | %s", order["order_id"],
                    pickup_name, destination_name, selected.get("name"))

        vehicle_text = self._vehicle_text(selected)
        text = (
            f"已为你生成滴滴叫车链接：{pickup_name} → {destination_name}，"
            f"{vehicle_text}。\n"
            f"请点击订单卡片中的链接前往滴滴 App/小程序完成叫车。"
        )
        message = AIMessage(
            content=text,
            response_metadata={"taxi_order": order, "request_id": request_id},
        )

        return {
            "taxi_order": order,
            "taxi_request_id": request_id,
            "taxi_estimate": None,
            "vehicle_type": None,
            "messages": [message],
        }

    def _selection_card(
            self,
            pickup_name: str,
            destination_name: str,
            city_name: str,
            pickup: Dict[str, Any],
            destination: Dict[str, Any],
            vehicles: List[Dict[str, Any]],
            trace_id: Any,
            request_id: Any,
    ) -> Dict[str, Any]:
        """返回车型选择卡，等待用户回复车型名称"""
        options = self._vehicle_options(vehicles)
        order = {
            "order_id": self._order_id(),
            "provider": "didi_mcp",
            "provider_name": "滴滴出行",
            "status": "SELECT_VEHICLE",
            "status_text": "请选择车型",
            "pickup": pickup_name,
            "destination": destination_name,
            "city": city_name or pickup.get("city") or destination.get("city") or "",
            "vehicle_options": options,
            "estimate_trace_id": trace_id,
            "currency": "CNY",
            "simulated": False,
            "note": "请回复车型名称，随后生成滴滴叫车链接",
            "request_id": request_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        lines = [
            f"{index}. {self._vehicle_text(vehicle)}"
            for index, vehicle in enumerate(vehicles, 1)
        ]
        text = (
            f"滴滴打车预估（{pickup_name} → {destination_name}）：\n"
            + "\n".join(lines)
            + "\n请回复你想乘坐的车型名称（例如“特惠快车”），我再为你生成滴滴叫车链接。"
        )
        message = AIMessage(
            content=text,
            response_metadata={"taxi_order": order, "request_id": request_id},
        )

        pending_state = {
            "pickup": pickup_name,
            "destination": destination_name,
            "city": order["city"],
            "pickup_coords": pickup["coords"],
            "destination_coords": destination["coords"],
            "vehicles": options,
            "trace_id": trace_id,
        }
        return {
            "taxi_order": order,
            "taxi_request_id": request_id,
            "taxi_estimate": pending_state,
            "messages": [message],
        }

    @staticmethod
    def _pending_estimate(
            state: TripState,
            pickup_name: str,
            destination_name: str,
    ) -> Dict[str, Any] | None:
        """只有起终点一致时，才复用上一轮车型预估"""
        pending = state.get("taxi_estimate")
        if not pending:
            return None
        if (pending.get("pickup") or "").strip() != pickup_name:
            return None
        if (pending.get("destination") or "").strip() != destination_name:
            return None
        return pending

    @staticmethod
    def _vehicle_options(vehicles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "name": vehicle.get("name") or "",
                "price": vehicle.get("price_value") if vehicle.get("price_value") is not None
                else vehicle.get("price"),
                "coupon_price": vehicle.get("coupon_price"),
                "category": str(vehicle.get("category")) if vehicle.get("category") is not None else None,
            }
            for vehicle in vehicles
        ]

    @staticmethod
    def _vehicle_price(vehicle: Dict[str, Any]) -> Any:
        price = vehicle.get("price_value")
        return price if price is not None else vehicle.get("price")

    @classmethod
    def _vehicle_text(cls, vehicle: Dict[str, Any]) -> str:
        name = vehicle.get("name") or "车型"
        price = cls._vehicle_price(vehicle)
        coupon = vehicle.get("coupon_price")
        text = f"{name} 约 {price:.0f} 元" if isinstance(price, (int, float)) else name
        if coupon is not None:
            text += f"（券后约 {coupon:.0f} 元）"
        return text

    # ------------------ 未配置 MCP 时的演示实现 ------------------

    async def _demo_order(
            self,
            pickup_name: str,
            destination_name: str,
            city_name: str,
            pickup: Dict[str, Any],
            destination: Dict[str, Any],
            config: RunnableConfig,
    ) -> Dict[str, Any]:
        route = await amap_client.driving_route(pickup["coords"], destination["coords"])
        if route is None:
            return self._error(prompts.TAXI_FAILED.format(
                origin=pickup_name,
                destination=destination_name,
            ))

        request_id = (config.get("configurable") or {}).get("request_id")
        order = self._build_demo_order(
            pickup_name=pickup_name,
            destination_name=destination_name,
            city=city_name or pickup.get("city") or destination.get("city") or "",
            route=route,
            request_id=request_id,
        )
        logger.info("生成演示打车订单：%s %s -> %s", order["order_id"], pickup_name, destination_name)

        fare = order.get("estimated_fare")
        fare_text = f"预估车费 {fare:.0f} 元" if fare is not None else "车费以实际为准"
        text = (
            f"已为你呼叫车辆：{pickup_name} → {destination_name}，"
            f"全程约 {order['distance_km']} 公里，预计 {order['duration_min']} 分钟，{fare_text}。"
            f"订单号 {order['order_id']}，正在为你寻找附近司机。"
            f"（当前为演示打车，未接入真实打车平台）"
        )
        message = AIMessage(
            content=text,
            response_metadata={"taxi_order": order, "request_id": request_id},
        )

        return {
            "taxi_order": order,
            "taxi_request_id": request_id,
            "messages": [message],
        }

    @staticmethod
    def _build_demo_order(
            pickup_name: str,
            destination_name: str,
            city: str,
            route: Dict[str, Any],
            request_id: Any,
    ) -> Dict[str, Any]:
        """组装演示订单。接入真实平台时可替换为对应的 Provider"""
        taxi_cost = route.get("taxi_cost")
        try:
            taxi_cost = round(float(taxi_cost), 1) if taxi_cost is not None else None
        except (TypeError, ValueError):
            taxi_cost = None

        return {
            "order_id": TaxiNode._order_id(),
            "provider": "mock",
            "provider_name": "演示打车",
            "status": "WAITING_DRIVER",
            "status_text": "正在为你寻找附近司机",
            "pickup": pickup_name,
            "destination": destination_name,
            "city": city,
            "distance_km": round(route.get("distance_m", 0) / 1000, 1),
            "duration_min": route.get("duration_min"),
            "estimated_fare": taxi_cost,
            "currency": "CNY",
            "simulated": True,
            "note": "演示订单，未接入真实打车平台",
            "request_id": request_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    @staticmethod
    def _order_id() -> str:
        return "TX" + uuid.uuid4().hex[:12].upper()

    @staticmethod
    def _error(message: str) -> Dict[str, Any]:
        return {"messages": [AIMessage(content=message)]}
