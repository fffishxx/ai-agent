"""tripAgent 公共常量。"""

# ------------------ 规划参数 ------------------

MAX_TOOL_ROUNDS = 5  # 规划子图最大工具轮次
DEFAULT_DAYS = 3  # 用户未指定天数时的默认值
DEFAULT_CROWD = "general"  # 用户未指定人群时的默认值
DEFAULT_BUDGET_LEVEL = "economy"  # 用户未指定预算时的默认档位

# ------------------ SSE 事件类型 ------------------

TRIP_PLAN_EVENT = 1005  # 首屏行程 JSON
TRIP_VALIDATION_EVENT = 1006  # 异步路线校验结果
TAXI_ORDER_EVENT = 1007  # 一键打车订单

# ------------------ 图路由 ------------------

# 意图 -> 根图节点
INTENT_TO_NODE = {
    "TRAVEL_PLAN": "travel_plan",
    "ROUTE": "route_node",
    "TAXI": "taxi_node",
    "KNOWLEDGE": "knowledge_node",
    "OTHER": "other_node",
}

# 只有这些节点的模型输出需要按文本流式推送给前端
STREAM_NODES = {"knowledge_node", "other_node", "route_node"}
