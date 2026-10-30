from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field


# 意图类型
IntentType = Literal["TRAVEL_PLAN", "ROUTE", "TAXI", "KNOWLEDGE", "OTHER"]

# 路线交通方式
TransportType = Literal["walking", "driving", "transit"]

# 同行人群
CROWD_TYPES = {"general", "family", "couple", "elderly", "solo", "student"}


class IntentResult(BaseModel):
    """意图识别结果"""

    intent: IntentType = Field(description="用户意图")
    destination: Optional[str] = Field(
        default=None,
        description="目的地：TRAVEL_PLAN 为城市名（如“杭州”），ROUTE 为终点地点名（如“灵隐寺”）；未提及且历史中也没有时为 null",
    )
    origin: Optional[str] = Field(
        default=None,
        description="仅 ROUTE 意图使用的起点地点名（如“西湖”）；其他意图为 null",
    )
    city: Optional[str] = Field(
        default=None,
        description="仅 ROUTE 意图使用的起点/终点所在城市（如“杭州”），用于地点检索；无法判断时为 null",
    )
    transport: Optional[TransportType] = Field(
        default=None,
        description="仅 ROUTE 意图使用的交通方式：walking/driving/transit；用户未提及时为 null",
    )
    vehicle_type: Optional[str] = Field(
        default=None,
        description="仅 TAXI 意图使用的车型，例如“特惠快车”“快车”“专车”“豪华车”；用户未明确指定时为 null",
    )
    days: Optional[int] = Field(
        default=None,
        description="出行天数（整数）；用户未提及时为 null",
    )
    crowd: Optional[str] = Field(
        default=None,
        description="同行人群，取值 general/family/couple/elderly/solo/student；未提及时为 null",
    )


class PlanItem(BaseModel):
    """行程中的单个安排"""

    poi: str = Field(description="景点/地点名称，必须来自工具搜索结果")
    coords: Optional[Union[List[float], str]] = Field(
        default=None,
        description="[经度, 纬度]，必须原样使用工具返回的 coords",
    )
    time_slot: str = Field(description="时间段：上午/中午/下午/晚上")
    reason: str = Field(description="安排理由，结合天气、人群和地理位置说明")
    duration_min: int = Field(default=60, description="预计游玩时长（分钟）")


class PlanDay(BaseModel):
    """一天的行程"""

    day_index: int = Field(description="第几天，从 1 开始")
    theme: str = Field(description="当天主题，例如“西湖核心区”")
    items: List[PlanItem] = Field(default_factory=list, description="当天按顺序游览的地点")


class LodgingArea(BaseModel):
    """住宿区域建议"""

    name: str = Field(description="建议住宿的区域名称")
    reason: str = Field(description="推荐理由，例如靠近景点群、交通便利")


class DiningSuggestion(BaseModel):
    """餐饮建议"""

    area: str = Field(description="餐饮区域")
    cuisine: str = Field(description="菜系")
    note: str = Field(description="推荐说明，例如适合晚餐")


class BudgetEstimate(BaseModel):
    """预算粗估"""

    total: str = Field(description="人均总预算区间，例如“约 1500-2000 元/人”")
    breakdown: str = Field(description="预算构成，例如交通/餐饮/门票/住宿的粗估")


class TravelPlan(BaseModel):
    """最终行程（首屏结构化输出）"""

    days: List[PlanDay] = Field(description="逐日行程")
    lodging_area: LodgingArea = Field(description="住宿区域建议")
    dining_suggestions: List[DiningSuggestion] = Field(
        default_factory=list,
        description="餐饮建议",
    )
    budget_estimate: BudgetEstimate = Field(description="预算粗估")
