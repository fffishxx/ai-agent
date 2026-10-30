from typing import AsyncIterable

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.BaseAgent import make_sse_event  # SSE 事件格式化工具
from config import logger
from agent import AGENTS  # 全局智能体实例字典

# ========================= 创建路由对象 =========================
chat_router = APIRouter()

# ========================= 请求体模型 =========================
class ChatRequest(BaseModel):
    """
    用户发送给智能体的请求体
    """
    question: str      # 用户提出的问题
    sessionId: str     # 会话ID，用于关联上下文
    userToken: str     # 用户身份token，用于调用业务系统接口
    agentId: int = 1001  # 智能体ID，默认1001

# ========================= SSE 错误流 =========================
async def error_stream(message: str) -> AsyncIterable[str]:
    """
    异步生成错误消息的 SSE 流
    """
    yield make_sse_event(404, message)  # 将错误信息包装成 SSE 格式

# ========================= SSE 响应封装 =========================
def stream(data: AsyncIterable[str]) -> StreamingResponse:
    """
    将异步迭代对象封装为 StreamingResponse，返回 SSE 流
    """
    return StreamingResponse(
        data,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}  # 禁止缓存
    )

# ========================= 流式对话接口 =========================
@chat_router.post("")
async def chat(req: ChatRequest):
    """
    用户发起流式对话：
    - 从请求中获取 question, sessionId, agentId, userToken
    - 获取对应 agent 对象
    - 返回 agent 执行结果的 SSE 流
    """
    logger.info(f"【ChatRouter】收到请求：question = {req.question}, sessionId = {req.sessionId}, agentId = {req.agentId}")

    # 根据 agentId 获取智能体实例
    agent = AGENTS.get(req.agentId, None)
    if agent is None:
        error_msg = f"Agent not found (agentId={req.agentId})"
        return stream(error_stream(error_msg))  # 返回错误 SSE 流

    # 返回智能体生成的流式 SSE
    return stream(agent.execute(req.question, req.sessionId, req.userToken))