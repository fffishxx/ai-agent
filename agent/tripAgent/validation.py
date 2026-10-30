import math
from typing import Any, Dict, List, Optional

from agent.tripAgent.AmapClient import amap_client
from config import logger

# 直线距离小于该值（公里）时直接跳过路径规划
NEAR_DISTANCE_KM = 1.0
# 步行时间超过该值（分钟）时输出告警
MAX_WALK_MIN = 60


def parse_coords(value: Any) -> Optional[List[float]]:
    """
    将模型输出的坐标统一解析为 [经度, 纬度]。

    兼容：list/tuple、[lng, lat] 字符串、"lng,lat" 字符串、工具返回的 location。
    """
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            lng, lat = float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None
        if -180 <= lng <= 180 and -90 <= lat <= 90:
            return [lng, lat]
        return None

    if isinstance(value, str):
        parts = value.split(",")
        if len(parts) != 2:
            return None
        try:
            lng, lat = float(parts[0]), float(parts[1])
        except ValueError:
            return None
        if -180 <= lng <= 180 and -90 <= lat <= 90:
            return [lng, lat]

    return None


def haversine_km(a: List[float], b: List[float]) -> float:
    """计算两点间的大圆距离（公里）"""
    lng1, lat1 = math.radians(a[0]), math.radians(a[1])
    lng2, lat2 = math.radians(b[0]), math.radians(b[1])

    dlng = lng2 - lng1
    dlat = lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


async def run_validation(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    行程校验任务（代码主导，不调 LLM）。

    只校验同一天内相邻景点：直线距离超过 1km 时调用高德步行路径规划，
    步行时间超过 60 分钟则输出 warning。最小版只告警，不做 LLM 重排。

    :return: {"validation_status": "done", "warnings": [...]}
    """
    warnings: List[Dict[str, Any]] = []

    for day in plan.get("days") or []:
        day_index = day.get("day_index")

        # 过滤出带有效坐标的相邻点位
        items = []
        for item in day.get("items") or []:
            coords = parse_coords(item.get("coords"))
            if coords:
                items.append((item, coords))

        for (a, coords_a), (b, coords_b) in zip(items, items[1:]):
            distance_km = haversine_km(coords_a, coords_b)
            if distance_km < NEAR_DISTANCE_KM:
                continue

            try:
                route = await amap_client.walking_route(coords_a, coords_b)
            except Exception as e:
                logger.warning("行程校验路径规划失败：%s", e)
                continue

            if not route:
                continue

            walk_min = route["duration_min"]
            if walk_min > MAX_WALK_MIN:
                warnings.append({
                    "day_index": day_index,
                    "from": a.get("poi"),
                    "to": b.get("poi"),
                    "walk_min": walk_min,
                    "distance_km": round(distance_km, 2),
                    "message": f"第{day_index}天 {a.get('poi')} → {b.get('poi')} "
                               f"步行约 {walk_min} 分钟，建议调整",
                })

    return {"validation_status": "done", "warnings": warnings}
