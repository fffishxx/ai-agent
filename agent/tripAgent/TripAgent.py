import asyncio
import copy
import uuid
from typing import Any, AsyncIterable, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.constants import START, END
from langgraph.graph.state import CompiledStateGraph, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import StateSnapshot

from agent.BaseAgent import BaseAgent, STOP_EVENT, format_sse_data, make_sse_event
from agent.tripAgent import prompts
from agent.tripAgent.AmapClient import amap_client
from agent.tripAgent.didi_mcp import didi_mcp
from agent.tripAgent.constants import (
    INTENT_TO_NODE,
    STREAM_NODES,
    TAXI_ORDER_EVENT,
    TRIP_PLAN_EVENT,
    TRIP_VALIDATION_EVENT,
)
from agent.tripAgent.node import (
    ClarifyNode,
    FormatPlanNode,
    IntentNode,
    KnowledgeNode,
    OtherNode,
    ParamFillNode,
    PlannerNode,
    RouteNode,
    TaxiNode,
)
from agent.tripAgent.TripState import TripState
from agent.tripAgent.tools import AMAP_TOOLS
from agent.tripAgent.utils import content_to_text, current_turn_messages
from agent.tripAgent.validation import run_validation
from config import get_async_pg_pool, langfuse_config, logger
from dao import chat_session_dao


class TripAgent(BaseAgent):
    """
    出行智能体。

    根图：意图识别 -> 出行推荐 / 路线推荐 / 一键打车 / 旅游知识 / 其他

    出行推荐子图：
        START -> 参数补全 -> 规划 LLM（绑定工具） -> ToolNode -> should_continue
                 ├─ 有 tool_calls 且未超过 5 轮 -> 回到规划 LLM
                 └─ 无 tool_calls -> 结构化输出 -> END

    各节点实现在 agent/tripAgent/node/ 下，统一继承 BaseTripNode；
    本类只负责节点装配、图构建、SSE 输出与会话状态管理。

    行程生成后先通过 SSE 推送首屏 JSON（eventType=1005），再异步执行路线校验，
    校验完成后推送 warnings（eventType=1006），最后发送 STOP_EVENT。
    """

    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.checkpointer: Optional[AsyncPostgresSaver] = None
        self.travel_graph: Optional[CompiledStateGraph] = None
        self.graph: Optional[CompiledStateGraph] = None
        self.tools = AMAP_TOOLS

        # 根图节点
        self.intent_node = IntentNode(provider)
        self.route_node = RouteNode(provider)
        self.taxi_node = TaxiNode(provider)
        self.knowledge_node = KnowledgeNode(provider)
        self.other_node = OtherNode(provider)

        # 出行推荐子图节点
        self.param_fill = ParamFillNode(provider)
        self.clarify = ClarifyNode(provider)
        self.planner = PlannerNode(provider)
        self.format_plan = FormatPlanNode(provider)

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------

    async def init(self):
        """初始化 Checkpointer、子图与根图"""
        # 检查会话记忆所需要的表是否存在
        await self.check_table()

        # 获取异步数据库连接池，并创建 Checkpointer 用于多轮会话记忆
        async_pg_pool = await get_async_pg_pool()
        self.checkpointer = AsyncPostgresSaver(conn=async_pg_pool)

        self.init_travel_graph()
        self.init_graph()

        # 高德 HTTP 客户端（共享连接，供工具与校验任务复用）
        await amap_client.start()

        logger.info("TripAgent 初始化完成")

    async def destroy(self):
        """释放高德/滴滴 HTTP 客户端"""
        await amap_client.close()
        await didi_mcp.close()

    async def check_table(self):
        """检查 Checkpointer 相关的表是否存在，不存在则自动创建"""
        async_pg_pool = await get_async_pg_pool()
        conn = None
        try:
            conn = await async_pg_pool.getconn()
            await conn.set_autocommit(True)
            checkpointer = AsyncPostgresSaver(conn=conn)
            await checkpointer.setup()
        finally:
            if conn is not None:
                await async_pg_pool.putconn(conn)

    # ------------------------------------------------------------------
    # 图构建
    # ------------------------------------------------------------------

    def init_travel_graph(self):
        """构建出行推荐子图"""
        build = StateGraph(TripState)

        build.add_node("param_fill", self.param_fill.execute)
        build.add_node("clarify", self.clarify.execute)
        build.add_node("planner", self.planner.execute)
        build.add_node("tools", ToolNode(self.tools, handle_tool_errors=True))
        build.add_node("format_plan", self.format_plan.execute)

        build.add_edge(START, "param_fill")
        build.add_conditional_edges(
            "param_fill",
            self.param_fill.route,
            {"clarify": "clarify", "planner": "planner"},
        )
        build.add_conditional_edges(
            "planner",
            self.planner.route,
            {"tools": "tools", "format_plan": "format_plan"},
        )
        build.add_edge("tools", "planner")
        build.add_edge("clarify", END)
        build.add_edge("format_plan", END)

        self.travel_graph = build.compile()

    def init_graph(self):
        """构建根图，并将出行推荐子图作为节点挂载"""
        build = StateGraph(TripState)

        build.add_node("intent_node", self.intent_node.execute)
        build.add_node("travel_plan", self.travel_graph)
        build.add_node("route_node", self.route_node.execute)
        build.add_node("taxi_node", self.taxi_node.execute)
        build.add_node("knowledge_node", self.knowledge_node.execute)
        build.add_node("other_node", self.other_node.execute)

        build.add_edge(START, "intent_node")
        build.add_conditional_edges("intent_node", self.intent_node.route, INTENT_TO_NODE)

        for node in INTENT_TO_NODE.values():
            build.add_edge(node, END)

        self.graph = build.compile(checkpointer=self.checkpointer)
        logger.info("TripAgent 图初始化成功....")

    # ------------------------------------------------------------------
    # 对外执行入口（SSE）
    # ------------------------------------------------------------------

    async def execute(self, question: str, session_id: str, user_token: str) -> AsyncIterable[str]:
        """
        执行一次出行对话，返回 SSE 流。

        事件类型：
        - 1001：文本增量（旅游知识/其他意图、路线与打车文字说明）
        - 1005：首屏行程 JSON
        - 1006：异步路线校验结果
        - 1007：一键打车订单
        - 2001：错误
        - 1002：结束
        """
        request_id = uuid.uuid4().hex
        answer_parts: List[str] = []
        stopped = False

        self.reset_stop(session_id)

        try:
            # 更新会话标题，并取回会话记录（读取 user_id 用于 Langfuse 追踪）
            chat_session = chat_session_dao.update_title(session_id, self.id(), question)
            user_id = chat_session.user_id if chat_session else None

            # Langfuse 追踪：一次用户请求对应一条 trace
            with langfuse_config.trace_span(
                name="trip-agent-chat",
                session_id=session_id,
                user_id=user_id,
                tags=["agent-1004"],
                input={"question": question},
                metadata={"request_id": request_id},
            ) as trace_span:
                handler = langfuse_config.new_handler()
                config = RunnableConfig(
                    configurable={
                        "thread_id": session_id,
                        "user_token": user_token,
                        "request_id": request_id,
                    },
                    callbacks=[handler] if handler else None,
                )

                stream = self.graph.astream(
                    input={"messages": [HumanMessage(content=question)]},
                    config=config,
                    subgraphs=True,
                    stream_mode="messages",
                )

                try:
                    async for _, (message, metadata) in stream:
                        if self.is_stop(session_id):
                            await stream.aclose()
                            stopped = True
                            break

                        # 只推送问答节点的文本，规划/意图节点不直接暴露给用户
                        if metadata.get("langgraph_node") not in STREAM_NODES:
                            continue
                        if isinstance(message, ToolMessage):
                            continue

                        text = content_to_text(getattr(message, "content", None))
                        if not text:
                            continue

                        answer_parts.append(text)
                        yield make_sse_event(1001, text)
                except asyncio.CancelledError:
                    await stream.aclose()
                    raise

                plan = None
                plan_is_current = False
                taxi_order = None
                taxi_is_current = False
                if not stopped:
                    snapshot: StateSnapshot = await self.graph.aget_state(config)
                    values = snapshot.values or {}
                    plan = values.get("plan")
                    plan_is_current = bool(plan) and values.get("plan_request_id") == request_id
                    taxi_order = values.get("taxi_order")
                    taxi_is_current = bool(taxi_order) and values.get("taxi_request_id") == request_id

                    if values.get("need_clarification"):
                        # 目的地缺失：唯一硬性阻断，输出追问
                        text = values.get("clarification_question") or prompts.CLARIFY_DESTINATION
                        answer_parts.append(text)
                        yield make_sse_event(1001, text)

                    elif plan_is_current:
                        # 1. 先启动异步校验任务，与首屏推送并行
                        validation_task = asyncio.create_task(run_validation(plan))

                        # 2. 立即推送首屏行程（若客户端在此断开，生成器关闭时取消校验任务）
                        resumed = False
                        try:
                            yield make_sse_event(TRIP_PLAN_EVENT, plan)
                            resumed = True
                        finally:
                            if not resumed and not validation_task.done():
                                validation_task.cancel()

                        # 3. 等待校验完成，推送增量 patch
                        validation = await self._validate_plan(
                            config, plan, request_id, validation_task
                        )
                        if not self.is_stop(session_id):
                            yield make_sse_event(TRIP_VALIDATION_EVENT, validation)

                    elif taxi_is_current:
                        # 一键打车：先推送订单卡片，再补一条文字说明
                        yield make_sse_event(TAXI_ORDER_EVENT, taxi_order)
                        if not answer_parts:
                            text = self._last_ai_text(values)
                            if text:
                                answer_parts.append(text)
                                yield make_sse_event(1001, text)

                    elif not answer_parts:
                        # 路线等非流式节点：统一输出最后一条 AIMessage
                        text = self._last_ai_text(values)
                        if text:
                            answer_parts.append(text)
                            yield make_sse_event(1001, text)

                if trace_span is not None:
                    trace_span.update(output={
                        "answer": "".join(answer_parts),
                        "plan": plan if plan_is_current else None,
                        "taxi_order": taxi_order if taxi_is_current else None,
                    })

        except Exception as e:
            if not self.is_stop(session_id):
                logger.exception("TripAgent execute error")
                yield make_sse_event(2001, str(e))

        finally:
            self.reset_stop(session_id)

        yield format_sse_data(STOP_EVENT)

    async def _validate_plan(
            self,
            config: RunnableConfig,
            plan: Dict[str, Any],
            request_id: str,
            validation_task: Optional[asyncio.Task] = None,
    ) -> Dict[str, Any]:
        """等待行程校验任务完成，并把结果写回 Checkpointer"""
        try:
            result = await validation_task if validation_task is not None else await run_validation(plan)
        except Exception as e:
            logger.exception("行程校验任务失败")
            result = {"validation_status": "done", "warnings": [], "error": str(e)}

        # 将校验结果写回状态与会话历史中的行程消息
        updated_plan = copy.deepcopy(plan)
        updated_plan.update(result)

        try:
            snapshot: StateSnapshot = await self.graph.aget_state(config)
            messages = list((snapshot.values or {}).get("messages") or [])
            for index, message in enumerate(messages):
                if not isinstance(message, AIMessage):
                    continue
                metadata = message.response_metadata or {}
                if metadata.get("request_id") != request_id:
                    continue
                new_metadata = dict(metadata)
                new_metadata["trip_plan"] = updated_plan
                messages[index] = message.model_copy(update={"response_metadata": new_metadata})

            await self.graph.aupdate_state(config, {
                "messages": messages,
                "plan": updated_plan,
                "validation_status": result.get("validation_status", "done"),
                "warnings": result.get("warnings", []),
            })
        except Exception as e:
            logger.warning("行程校验结果写回状态失败：%s", e)

        return result

    # ------------------------------------------------------------------
    # 会话相关
    # ------------------------------------------------------------------

    async def session_detail(self, user_id: int, session_id: str) -> list:
        """从 Checkpointer 恢复历史消息；行程消息附带 tripPlan，打车消息附带 taxiOrder"""
        config = RunnableConfig(configurable={"thread_id": session_id})
        snapshot: StateSnapshot = await self.graph.aget_state(config)
        values = snapshot.values or {}
        messages = values.get("messages") or []

        result = []
        for message in messages:
            msg_type = ""
            content = content_to_text(getattr(message, "content", None))
            params: Dict[str, Any] = {}

            if isinstance(message, HumanMessage):
                msg_type = "USER"
            elif isinstance(message, AIMessage):
                metadata = message.response_metadata or {}
                if metadata.get("internal"):
                    continue

                msg_type = "ASSISTANT"
                plan = metadata.get("trip_plan")
                if plan:
                    plan = copy.deepcopy(plan)
                    if metadata.get("request_id") == values.get("plan_request_id"):
                        plan["validation_status"] = values.get(
                            "validation_status", plan.get("validation_status")
                        )
                        plan["warnings"] = values.get("warnings", plan.get("warnings", []))
                    params["tripPlan"] = plan

                taxi_order = metadata.get("taxi_order")
                if taxi_order:
                    params["taxiOrder"] = copy.deepcopy(taxi_order)

            if msg_type and content:
                result.append({"type": msg_type, "content": content, "params": params})

        return result

    async def delete_session(self, session_id: str):
        """删除该会话的 Checkpointer 状态"""
        if self.checkpointer is not None:
            await self.checkpointer.adelete_thread(session_id)

    def id(self) -> int:
        """出行 Agent 的固定 ID"""
        return 1004

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    def _last_ai_text(self, values: Dict[str, Any]) -> str:
        """获取本轮最后一条 AI 文本消息"""
        for message in reversed(current_turn_messages(values)):
            if isinstance(message, AIMessage) and not getattr(message, "tool_calls", None):
                if (message.response_metadata or {}).get("internal"):
                    continue
                text = content_to_text(message.content)
                if text:
                    return text
        return ""


# 全局 TripAgent 实例
trip_agent = TripAgent()
