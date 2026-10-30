"""地点解析工具：路线推荐与一键打车共用。"""

from typing import Any, Dict, Optional

from agent.tripAgent.AmapClient import amap_client
from agent.tripAgent.validation import parse_coords
from config import logger


async def resolve_place(name: str, city: str) -> Optional[Dict[str, Any]]:
    """
    把地点名解析为坐标。

    优先在指定城市内做 POI 检索（避免“灵隐寺”被地理编码到同名异地），
    没有城市或检索失败时回退地理编码。

    :return: {"name", "coords", "city", "adcode"}，无法解析时返回 None
    """
    name = (name or "").strip()
    city = (city or "").strip()
    if not name:
        return None

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


async def resolve_city_adcode(city: str) -> Optional[str]:
    """城市名 -> adcode（公交路径规划需要）"""
    city = (city or "").strip()
    if not city:
        return None
    if city.isdigit() and len(city) == 6:
        return city

    try:
        geo = await amap_client.geocode(city)
    except Exception as e:
        logger.debug("城市 %s 解析 adcode 失败：%s", city, e)
        return None
    return geo.get("adcode") or None
