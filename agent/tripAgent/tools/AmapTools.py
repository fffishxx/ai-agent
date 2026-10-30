from typing import Optional

from langchain_core.tools import tool

from agent.tripAgent.AmapClient import AmapError, amap_client
from util import JsonUtil


def _error(message: str) -> str:
    """工具统一错误返回：序列化为 JSON 交给大模型继续处理"""
    return JsonUtil.to_str({"error": message})


@tool
async def weather_query(city_adcode: str) -> str:
    """
    查询指定城市未来 3 天的天气预报，用于决定户外/室内景点安排。

    Args:
        city_adcode: 城市 adcode（例如杭州为 330100），也可以直接传城市名称。
    """
    try:
        forecasts = await amap_client.weather(city_adcode)
        return JsonUtil.to_str({"city": city_adcode, "forecasts": forecasts})
    except AmapError as e:
        return _error(f"天气查询失败：{e}")
    except Exception as e:
        return _error(f"天气查询异常：{e}")


@tool
async def poi_search(keywords: str, city: str, types: Optional[str] = None) -> str:
    """
    在高德地图按关键词搜索景点、博物馆、街区等 POI，返回名称、坐标、地址和类型。

    Args:
        keywords: 具体搜索关键词，例如“西湖 景点”“杭州 博物馆”，不要只传“景点”。
        city: 城市名称或 adcode，例如“杭州”或“330100”。
        types: 可选的高德 POI 类型码，例如景点 110000、餐饮 050000；一般留空即可。
    """
    try:
        pois = await amap_client.search_poi(keywords=keywords, city=city, types=types or "", limit=8)
        return JsonUtil.to_str({
            "city": city,
            "keywords": keywords,
            "pois": pois,
        })
    except AmapError as e:
        return _error(f"POI 搜索失败：{e}")
    except Exception as e:
        return _error(f"POI 搜索异常：{e}")


@tool
async def food_search(keywords: str, city: str) -> str:
    """
    搜索目的地餐厅或美食聚集区域，返回餐厅名称、坐标和地址。

    Args:
        keywords: 美食关键词，例如“杭帮菜”“河坊街 美食”。
        city: 城市名称或 adcode，例如“杭州”。
    """
    try:
        # 高德餐饮类型码 050000
        pois = await amap_client.search_poi(
            keywords=keywords,
            city=city,
            types="050000",
            limit=8,
        )
        return JsonUtil.to_str({
            "city": city,
            "keywords": keywords,
            "pois": pois,
        })
    except AmapError as e:
        return _error(f"美食搜索失败：{e}")
    except Exception as e:
        return _error(f"美食搜索异常：{e}")
