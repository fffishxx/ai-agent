"""滴滴 MCP 基础版客户端（Streamable HTTP + JSON-RPC 2.0）。

基础版提供两个能力：
- wyc_estimate：查询可用车型与预估价格
- wyc_new_order：生成跳转滴滴 App/微信小程序的链接（实际下单在滴滴侧完成）

注意：MCP Key 通过环境变量 DIDI_MCP_KEY 注入，禁止写入仓库。
"""

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import httpx

from common import (
    DIDI_MCP_BASE_URL,
    DIDI_MCP_KEY,
    DIDI_MCP_SANDBOX,
    DIDI_MCP_SANDBOX_URL,
    DIDI_MCP_TIMEOUT,
)
from config import config_manager, logger


class DidiMCPError(RuntimeError):
    """滴滴 MCP 调用异常"""


class DidiMCPClient:
    """滴滴 MCP 基础版客户端"""

    def __init__(self):
        self.key = (os.getenv("DIDI_MCP_KEY") or config_manager.get(DIDI_MCP_KEY, "") or "").strip()
        self.sandbox = bool(config_manager.get(DIDI_MCP_SANDBOX, False))
        url_key = DIDI_MCP_SANDBOX_URL if self.sandbox else DIDI_MCP_BASE_URL
        self.base_url = (config_manager.get(url_key, "") or "").rstrip("/")
        self.timeout = float(config_manager.get(DIDI_MCP_TIMEOUT, 15))

        self._client: Optional[httpx.AsyncClient] = None
        self._request_id = 0
        self._tools: Dict[str, str] = {}
        self._tools_expire_at = 0.0

        if self.key:
            logger.info("滴滴 MCP 已配置：%s", "沙箱环境" if self.sandbox else "正式环境")

    def is_configured(self) -> bool:
        """是否已配置 MCP Key"""
        return bool(self.key and self.base_url)

    # ------------------ 生命周期 ------------------

    async def start(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)

    async def close(self):
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    # ------------------ JSON-RPC ------------------

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_configured():
            raise DidiMCPError("未配置 DIDI_MCP_KEY，无法调用滴滴打车")
        if self._client is None or self._client.is_closed:
            await self.start()

        request_id = payload.get("id")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        try:
            async with self._client.stream(
                    "POST",
                    self.base_url,
                    params={"key": self.key},
                    json=payload,
                    headers=headers,
            ) as response:
                if response.status_code >= 400:
                    raise DidiMCPError(f"滴滴 MCP 返回 HTTP {response.status_code}")

                content_type = response.headers.get("content-type", "")
                if "text/event-stream" in content_type:
                    data = await self._read_sse(response, request_id)
                else:
                    body = await response.aread()
                    try:
                        data = json.loads(body.decode("utf-8"))
                    except Exception as e:
                        raise DidiMCPError("滴滴 MCP 返回格式异常") from e
        except DidiMCPError:
            raise
        except Exception as e:
            # 异常信息可能带 key 的 URL，这里只保留异常类型
            raise DidiMCPError(f"滴滴 MCP 请求失败：{type(e).__name__}") from e

        if not isinstance(data, dict):
            raise DidiMCPError("滴滴 MCP 返回格式异常")

        error = data.get("error")
        if error:
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise DidiMCPError(f"滴滴 MCP 返回错误：{message}")

        return data.get("result") or {}

    @staticmethod
    async def _read_sse(response, request_id) -> Dict[str, Any]:
        """从 Streamable HTTP 的 SSE 响应中读取匹配的 JSON-RPC 结果"""
        async for line in response.aiter_lines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw or raw == "[DONE]":
                continue
            try:
                obj = json.loads(raw)
            except Exception:
                continue
            if isinstance(obj, dict) and (
                    obj.get("id") == request_id or "result" in obj or "error" in obj
            ):
                return obj
        raise DidiMCPError("滴滴 MCP 未返回有效响应")

    async def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }
        return await self._post(payload)

    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        result = await self._rpc("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            text = self._content_text(result) or "工具调用失败"
            raise DidiMCPError(f"滴滴 MCP 工具 {name} 调用失败：{text[:200]}")
        return result

    # ------------------ 工具发现 ------------------

    async def _load_tools(self):
        if self._tools and time.time() < self._tools_expire_at:
            return

        try:
            result = await self._rpc("tools/list", {})
        except DidiMCPError as e:
            logger.warning("滴滴 MCP tools/list 失败，使用默认工具名：%s", e)
            self._tools = {}
            self._tools_expire_at = time.time() + 60
            return

        mapping = {}
        for tool in result.get("tools") or []:
            name = tool.get("name") or ""
            low = name.lower()
            if "estimate" in low and "estimate" not in mapping:
                mapping["estimate"] = name
            if ("generate_ride_app_link" in low or "new_order" in low) and "link" not in mapping:
                mapping["link"] = name
            if "create_order" in low and "create_order" not in mapping:
                mapping["create_order"] = name
            if "query_order" in low and "query_order" not in mapping:
                mapping["query_order"] = name
            if "cancel_order" in low and "cancel_order" not in mapping:
                mapping["cancel_order"] = name

        self._tools = mapping
        self._tools_expire_at = time.time() + 300
        logger.info("滴滴 MCP 可用工具：%s", mapping or "未发现可用工具")

    async def _tool_name(self, kind: str, fallback: str) -> str:
        await self._load_tools()
        return self._tools.get(kind) or fallback

    # ------------------ 对外能力 ------------------

    async def estimate(self, pickup: Dict[str, Any], destination: Dict[str, Any]) -> Dict[str, Any]:
        """
        车型与预估价查询。

        :return: {"data": 原始数据, "text": 原始文本, "vehicles": [标准化车型]}
        """
        tool = await self._tool_name("estimate", "wyc_estimate")
        arguments = {
            "from_lng": self._coord(pickup["coords"][0]),
            "from_lat": self._coord(pickup["coords"][1]),
            "from_name": pickup.get("name") or "",
            "to_lng": self._coord(destination["coords"][0]),
            "to_lat": self._coord(destination["coords"][1]),
            "to_name": destination.get("name") or "",
        }
        result = await self._call_tool(tool, arguments)
        payload = self._extract_payload(result)
        payload["vehicles"] = self.extract_vehicles(payload)
        payload["trace_id"] = self._extract_trace_id(payload)
        return payload

    async def generate_link(
            self,
            pickup: Dict[str, Any],
            destination: Dict[str, Any],
            category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成跳转滴滴 App/小程序的链接（基础版，不直接创建订单）。

        :param category: 用户选择的车型品类；用户未明确选择时不传
        :return: {"url": 跳转链接, "payload": 原始响应}
        """
        tool = await self._tool_name("link", "taxi_generate_ride_app_link")
        arguments = {
            "from_lng": self._coord(pickup["coords"][0]),
            "from_lat": self._coord(pickup["coords"][1]),
            "to_lng": self._coord(destination["coords"][0]),
            "to_lat": self._coord(destination["coords"][1]),
        }
        if category:
            arguments["product_category"] = str(category)

        result = await self._call_tool(tool, arguments)
        payload = self._extract_payload(result)
        links = self._extract_links(payload)
        url = (
                links.get("app")
                or links.get("browser")
                or links.get("miniprogram")
                or links.get("url")
                or links.get("deep")
        )
        return {"url": url, "links": links, "payload": payload}

    # ------------------ 响应解析 ------------------

    @staticmethod
    def _coord(value: Any) -> str:
        try:
            return f"{float(value):.6f}"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _content_text(result: Dict[str, Any]) -> str:
        texts = []
        for block in result.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text") or "")
        return "\n".join(texts).strip()

    @classmethod
    def _extract_payload(cls, result: Dict[str, Any]) -> Dict[str, Any]:
        text = cls._content_text(result)
        data = cls._maybe_json(text) if text else None
        if data is None:
            structured = result.get("structuredContent")
            if isinstance(structured, (dict, list)):
                data = structured
        return {"data": data, "text": text, "result": result}

    @staticmethod
    def _maybe_json(text: str) -> Optional[Any]:
        text = (text or "").strip()
        if not text:
            return None

        candidates = [text]
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
        if fenced:
            candidates.insert(0, fenced.group(1).strip())

        for candidate in candidates:
            try:
                return json.loads(candidate)
            except Exception:
                pass

        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                pass

        start, end = text.find("["), text.rfind("]")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                pass

        return None

    @classmethod
    def extract_vehicles(cls, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从 estimate 响应中提取车型、价格和品类标识（兼容结构化与文本返回）"""
        data = payload.get("data")
        raw_items: List[Dict[str, Any]] = []

        def collect(obj: Any):
            if isinstance(obj, list):
                raw_items.extend([item for item in obj if isinstance(item, dict)])
            elif isinstance(obj, dict):
                for key in ("items", "vehicles", "products", "estimates",
                            "estimate_list", "car_list", "models", "list"):
                    if isinstance(obj.get(key), list):
                        raw_items.extend([item for item in obj[key] if isinstance(item, dict)])
                        return
                for key in ("data", "result", "estimate"):
                    if isinstance(obj.get(key), (dict, list)):
                        collect(obj[key])
                        return
                # 兼容 {"特惠快车": 18, "快车": 22} 这种映射
                scalar_values = [v for v in obj.values() if isinstance(v, (int, float, str))]
                if scalar_values and len(scalar_values) == len(obj):
                    for key, value in obj.items():
                        raw_items.append({"name": key, "price": value, "category": key})

        collect(data)
        if not raw_items:
            raw_items = cls._vehicles_from_text(payload.get("text") or "")

        vehicles: List[Dict[str, Any]] = []
        seen = set()
        for item in raw_items:
            name = cls._first(item, ("name", "productName", "product_name",
                                     "car_type", "vehicle_type", "title", "type"))
            price = cls._first(item, ("priceText", "price", "estimate_price", "total_price",
                                      "amount", "cost", "lowest_price", "pre_price"))
            coupon = cls._first(item, ("priceDiscounted", "coupon_price",
                                       "discounted_price", "couponPrice"))
            category = cls._first(item, ("productCategory", "product_category", "category",
                                         "product_id", "productId", "car_type", "vehicle_type", "type"))
            price_value = cls._price_value(price)
            coupon_value = cls._price_value(coupon)

            if not name and price_value is None:
                continue

            key = (str(name), price_value, str(category))
            if key in seen:
                continue
            seen.add(key)

            vehicles.append({
                "name": str(name) if name is not None else "",
                "price": price_value if price_value is not None else price,
                "price_value": price_value,
                "coupon_price": coupon_value,
                "category": str(category) if category is not None else None,
                "raw": item,
            })

        return vehicles

    @staticmethod
    def _vehicles_from_text(text: str) -> List[Dict[str, Any]]:
        """解析 estimate 的纯文本返回（【用户显示内容】格式）"""
        if not text:
            return []

        items: List[Dict[str, Any]] = []
        pattern = re.compile(
            r"^\s*\d+[.、]\s*(?P<name>[^:：\n]+?)\s*[:：]\s*约\s*(?P<price>[\d.]+)\s*元"
            r"(?:[，,]\s*券后约\s*(?P<coupon>[\d.]+)\s*元)?"
            r"\s*[（(]品类代码[:：]\s*(?P<category>\d+)[）)]",
            re.M,
        )
        for match in pattern.finditer(text):
            items.append({
                "productName": match.group("name").strip(),
                "priceText": match.group("price"),
                "priceDiscounted": match.group("coupon"),
                "productCategory": match.group("category"),
            })
        if items:
            return items

        pattern = re.compile(
            r"^\s*\d+[.、]\s*(?P<name>[^（(\n]+?)\s*[（(]product_category[:：]\s*(?P<category>\d+)[）)]",
            re.M,
        )
        for match in pattern.finditer(text):
            items.append({
                "productName": match.group("name").strip(),
                "productCategory": match.group("category"),
            })
        return items

    @classmethod
    def _extract_trace_id(cls, payload: Dict[str, Any]) -> Optional[str]:
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("traceId", "trace_id", "estimate_trace_id", "estimateTraceId"):
                value = data.get(key)
                if value not in (None, "", []):
                    return str(value)

        text = payload.get("text") or ""
        match = re.search(r"预估流程ID[:：]\s*([0-9A-Za-z_-]+)", text)
        return match.group(1) if match else None

    @classmethod
    def _extract_links(cls, payload: Dict[str, Any]) -> Dict[str, str]:
        """提取 app / 小程序 / 浏览器 / deep link 等跳转地址"""
        links: Dict[str, str] = {}

        def walk(obj: Any):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and value.strip():
                        low = key.lower()
                        if "miniprogram" in low:
                            links.setdefault("miniprogram", value.strip())
                        elif low in ("applink", "app_link", "appurl"):
                            links.setdefault("app", value.strip())
                        elif low in ("browserlink", "browser_link", "browserurl"):
                            links.setdefault("browser", value.strip())
                        elif low in ("deeplink", "deep_link"):
                            links.setdefault("deep", value.strip())
                        elif low in ("jump_url", "jumpurl", "url", "link"):
                            links.setdefault("url", value.strip())
                    else:
                        walk(value)
            elif isinstance(obj, list):
                for value in obj:
                    walk(value)
            elif isinstance(obj, str):
                for url in re.findall(r"(https?://[^\s\"'<>]+|diditaxi://[^\s\"'<>]+)", obj):
                    links.setdefault("url", url)

        walk(payload.get("data"))
        if not links:
            walk(payload.get("text"))
        return links

    @classmethod
    def _extract_url(cls, payload: Dict[str, Any]) -> Optional[str]:
        links = cls._extract_links(payload)
        return (
                links.get("app")
                or links.get("browser")
                or links.get("miniprogram")
                or links.get("url")
                or links.get("deep")
        )

    @staticmethod
    def _first(item: Dict[str, Any], keys: tuple) -> Any:
        for key in keys:
            value = item.get(key)
            if value not in (None, "", []):
                return value
        return None

    @staticmethod
    def _price_value(value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"\d+(?:\.\d+)?", value)
            if match:
                return float(match.group())
        if isinstance(value, dict):
            for key in ("value", "amount", "price", "min", "lowest_price"):
                if key in value:
                    return DidiMCPClient._price_value(value[key])
        return None


# 全局滴滴 MCP 客户端
didi_mcp = DidiMCPClient()
