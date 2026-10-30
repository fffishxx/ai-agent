import math
from typing import Any, Dict, List, Optional

import httpx

from common import AMAP_KEY, AMAP_TIMEOUT
from config import config_manager, logger


class AmapError(RuntimeError):
    """高德 Web 服务调用异常"""


def _as_text(value: Any) -> str:
    """高德部分字段在为空时会返回 []，这里统一转成字符串"""
    return value if isinstance(value, str) else ""


class AmapClient:
    """
    高德地图 Web 服务客户端（异步）。

    封装出行规划所需的四类接口：
    - 地理编码：城市名 -> adcode
    - 天气查询：未来 3 天预报
    - POI 搜索：景点、美食等地点
    - 步行路径规划：供异步行程校验使用

    注意：这里使用的是「Web服务」类型的 Key，与 JS API Key 不通用。
    """

    BASE_URL = "https://restapi.amap.com"

    def __init__(self):
        self.key = config_manager.get(AMAP_KEY)
        self.timeout = float(config_manager.get(AMAP_TIMEOUT, 10))
        self._client: Optional[httpx.AsyncClient] = None

        if not self.key:
            logger.warning("未配置 AMAP_KEY（高德 Web 服务 Key），出行规划的地图工具将不可用")

    # ------------------ 生命周期 ------------------

    async def start(self):
        """创建共享的 HTTP 客户端，在 Agent 初始化时调用"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)

    async def close(self):
        """关闭共享的 HTTP 客户端，在 Agent 销毁时调用"""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    # ------------------ 基础请求 ------------------

    async def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发起 GET 请求并校验高德返回状态。

        :raises AmapError: Key 缺失、网络异常或业务状态非 1 时抛出
        """
        if not self.key:
            raise AmapError("未配置 AMAP_KEY，请先配置高德 Web 服务 Key")

        if self._client is None or self._client.is_closed:
            await self.start()

        try:
            response = await self._client.get(
                f"{self.BASE_URL}{path}",
                params={"key": self.key, **params},
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise AmapError(f"高德接口请求失败：{e}") from e

        if not isinstance(data, dict):
            raise AmapError("高德接口返回格式异常")

        if str(data.get("status")) != "1":
            info = data.get("info") or "未知错误"
            infocode = data.get("infocode") or ""
            raise AmapError(f"高德接口返回失败：{info}({infocode})")

        return data

    # ------------------ 地理编码 ------------------

    async def geocode(self, address: str) -> Dict[str, Any]:
        """
        地理编码：城市/地址 -> adcode、城市名、坐标。

        Returns:
            {"adcode": "330100", "city": "杭州市", "province": "浙江省", "location": [lng, lat]}
        """
        address = (address or "").strip()
        if not address:
            raise AmapError("地理编码地址不能为空")

        data = await self._get("/v3/geocode/geo", {"address": address})
        geocodes = data.get("geocodes") or []
        if not geocodes:
            raise AmapError(f"未找到目的地：{address}")

        first = geocodes[0]
        city = _as_text(first.get("city")) or _as_text(first.get("province")) or address
        return {
            "adcode": _as_text(first.get("adcode")),
            "city": city,
            "province": _as_text(first.get("province")),
            "location": self.parse_location(first.get("location")),
        }

    # ------------------ 天气查询 ------------------

    async def weather(self, city: str) -> List[Dict[str, Any]]:
        """
        查询未来 3 天天气预报。

        :param city: 城市 adcode（如 330100）或城市名称（如 杭州）
        """
        city = (city or "").strip()
        adcode = city if self._is_adcode(city) else (await self.geocode(city)).get("adcode")
        if not adcode:
            raise AmapError(f"无法解析城市 adcode：{city}")

        data = await self._get(
            "/v3/weather/weatherInfo",
            {"city": adcode, "extensions": "all"},
        )
        forecasts = data.get("forecasts") or []
        if not forecasts:
            raise AmapError(f"未查询到天气数据：{city}")

        casts = forecasts[0].get("casts") or []
        return [
            {
                "date": cast.get("date"),
                "week": cast.get("week"),
                "day_weather": cast.get("dayweather"),
                "night_weather": cast.get("nightweather"),
                "day_temp": cast.get("daytemp"),
                "night_temp": cast.get("nighttemp"),
                "day_wind": cast.get("daywind"),
                "day_power": cast.get("daypower"),
            }
            for cast in casts
        ]

    # ------------------ POI 搜索 ------------------

    async def search_poi(
            self,
            keywords: str,
            city: str,
            types: str = "",
            limit: int = 8,
    ) -> List[Dict[str, Any]]:
        """
        POI 关键字搜索（高德 v5）。

        :param keywords: 具体关键词，如「西湖 景点」
        :param city: 城市名称或 adcode
        :param types: 可选类型码，如餐饮 050000
        :param limit: 返回数量上限
        """
        keywords = (keywords or "").strip()
        city = (city or "").strip()
        types = (types or "").strip()
        if not keywords or not city:
            raise AmapError("POI 搜索的关键词和城市不能为空")

        params: Dict[str, Any] = {
            "keywords": keywords,
            "region": city,
            "city_limit": "true",
            "page_size": max(1, min(limit, 25)),
            "page_num": 1,
        }
        if types:
            params["types"] = types

        data = await self._get("/v5/place/text", params)
        pois = data.get("pois") or []

        result = []
        for poi in pois:
            location = poi.get("location")
            coords = self.parse_location(location)
            if not coords:
                continue
            result.append({
                "name": _as_text(poi.get("name")),
                "coords": coords,
                "location": location,
                "address": _as_text(poi.get("address")),
                "type": _as_text(poi.get("type")),
                "typecode": _as_text(poi.get("typecode")),
                "city": _as_text(poi.get("cityname")),
            })
        return result

    # ------------------ 步行路径规划 ------------------

    async def walking_route(
            self,
            origin: List[float],
            destination: List[float],
    ) -> Optional[Dict[str, Any]]:
        """
        步行路径规划，优先 v5，失败时回退 v3。

        :return: {"distance_m": 1200, "duration_min": 18}，无法获取时返回 None
        """
        origin_str = self._format_coords(origin)
        destination_str = self._format_coords(destination)

        try:
            data = await self._get(
                "/v5/direction/walking",
                {
                    "origin": origin_str,
                    "destination": destination_str,
                    "show_fields": "cost",
                },
            )
            route = self._parse_v5_route(data)
            if route:
                return route
        except Exception as e:
            logger.debug("高德 v5 步行路径规划失败，尝试 v3：%s", e)

        try:
            data = await self._get(
                "/v3/direction/walking",
                {"origin": origin_str, "destination": destination_str},
            )
            return self._parse_v3_route(data)
        except Exception as e:
            logger.debug("高德 v3 步行路径规划失败：%s", e)
            return None

    async def driving_route(
            self,
            origin: List[float],
            destination: List[float],
    ) -> Optional[Dict[str, Any]]:
        """
        驾车路径规划（v5）。

        :return: {"distance_m": 1200, "duration_min": 18}，无法获取时返回 None
        """
        try:
            data = await self._get(
                "/v5/direction/driving",
                {
                    "origin": self._format_coords(origin),
                    "destination": self._format_coords(destination),
                    "show_fields": "cost",
                },
            )
            return self._parse_v5_route(data)
        except Exception as e:
            logger.debug("高德 v5 驾车路径规划失败：%s", e)
            return None

    async def transit_route(
            self,
            origin: List[float],
            destination: List[float],
            city1: str,
            city2: str,
    ) -> Optional[Dict[str, Any]]:
        """
        公交/地铁路径规划（v5）。

        :param city1: 起点城市 adcode
        :param city2: 终点城市 adcode
        :return: {"distance_m": 1200, "duration_min": 18, "transit_fee": "2.0"}，无法获取时返回 None
        """
        if not city1 or not city2:
            return None

        try:
            data = await self._get(
                "/v5/direction/transit/integrated",
                {
                    "origin": self._format_coords(origin),
                    "destination": self._format_coords(destination),
                    "city1": city1,
                    "city2": city2,
                    "show_fields": "cost",
                },
            )
            return self._parse_v5_transit(data)
        except Exception as e:
            logger.debug("高德 v5 公交路径规划失败：%s", e)
            return None

    # ------------------ 工具方法 ------------------

    @staticmethod
    def _is_adcode(value: str) -> bool:
        return bool(value) and value.isdigit() and len(value) == 6

    @staticmethod
    def _format_coords(coords: List[float]) -> str:
        """高德坐标格式：「经度,纬度」"""
        return f"{coords[0]:.6f},{coords[1]:.6f}"

    @staticmethod
    def parse_location(location: Any) -> Optional[List[float]]:
        """解析高德坐标字符串「经度,纬度」"""
        if not isinstance(location, str):
            return None
        parts = location.split(",")
        if len(parts) != 2:
            return None
        try:
            lng, lat = float(parts[0]), float(parts[1])
        except ValueError:
            return None
        if not (-180 <= lng <= 180 and -90 <= lat <= 90):
            return None
        return [round(lng, 6), round(lat, 6)]

    @staticmethod
    def _parse_v5_route(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        route_data = data.get("route") or {}
        paths = route_data.get("paths") or []
        if not paths:
            return None

        path = paths[0]
        cost = path.get("cost") or {}
        duration = cost.get("duration") or path.get("duration") or 0
        distance = path.get("distance") or 0
        route = AmapClient._build_route(distance, duration)

        # 驾车路线会返回打车费用预估（元），供一键打车使用
        taxi_cost = route_data.get("taxi_cost")
        if route is not None and taxi_cost not in (None, "", []):
            try:
                route["taxi_cost"] = float(taxi_cost)
            except (TypeError, ValueError):
                pass

        return route

    @staticmethod
    def _parse_v3_route(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        paths = (data.get("route") or {}).get("paths") or []
        if not paths:
            return None

        path = paths[0]
        return AmapClient._build_route(path.get("distance"), path.get("duration"))

    @staticmethod
    def _parse_v5_transit(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        transits = (data.get("route") or {}).get("transits") or []
        if not transits:
            return None

        transit = transits[0]
        cost = transit.get("cost") or {}
        route = AmapClient._build_route(
            transit.get("distance"),
            cost.get("duration") or transit.get("duration"),
        )
        if route is not None and cost.get("transit_fee") is not None:
            route["transit_fee"] = cost.get("transit_fee")
        return route

    @staticmethod
    def _build_route(distance: Any, duration: Any) -> Optional[Dict[str, Any]]:
        try:
            distance_m = int(float(distance))
            duration_s = int(float(duration))
        except (TypeError, ValueError):
            return None
        if duration_s <= 0:
            return None
        return {
            "distance_m": distance_m,
            "duration_min": math.ceil(duration_s / 60),
        }


# 全局高德客户端实例
amap_client = AmapClient()
