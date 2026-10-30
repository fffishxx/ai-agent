from typing import Any, Dict, List, Optional

from langgraph.graph import MessagesState


class TripState(MessagesState):
    """
    出行智能体状态。

    messages 用于多轮对话与 Checkpointer 记忆，其余字段承载本轮意图识别、
    参数补全、规划子图以及异步校验的结果。
    """

    intent: str  # 意图：TRAVEL_PLAN/ROUTE/TAXI/KNOWLEDGE/OTHER
    destination: Optional[str]  # 目的地：出行规划为城市，路线推荐为终点地点
    origin: Optional[str]  # 路线推荐起点地点
    city: Optional[str]  # 路线推荐所在城市，用于 POI 检索
    transport: Optional[str]  # 路线交通方式：walking/driving/transit
    vehicle_type: Optional[str]  # 打车车型（用户选择）
    taxi_estimate: Optional[Dict[str, Any]]  # 待选车型的打车预估结果
    days: Optional[int]  # 出行天数
    crowd: Optional[str]  # 同行人群
    budget_level: Optional[str]  # 预算档位（默认 economy）
    city_adcode: Optional[str]  # 目的地 adcode，用于天气查询
    assumptions: Dict[str, Any]  # 参数补全时写入的默认假设
    plan: Optional[Dict[str, Any]]  # 结构化行程
    plan_request_id: Optional[str]  # 本轮生成行程对应的请求 ID，避免重复推送旧行程
    taxi_order: Optional[Dict[str, Any]]  # 一键打车订单
    taxi_request_id: Optional[str]  # 本轮打车订单对应的请求 ID，避免重复推送旧订单
    need_clarification: bool  # 是否需要追问目的地
    clarification_question: Optional[str]  # 追问话术
    tool_rounds: int  # 规划子图已执行的工具轮次
    validation_status: str  # pending/done
    warnings: List[Dict[str, Any]]  # 异步校验告警
