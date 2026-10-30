from fastapi import APIRouter
from web.routers.ChatRouter import AGENTS, chat_router  # 全局智能体实例字典
from config import logger
from dao import chat_session_dao  # ChatSession 数据访问对象

# ========================= 创建路由对象 =========================
session_router = APIRouter()


# ========================= 创建新会话 =========================
@session_router.post("")
async def create_session(n: int, agent_id: int, user_id: int):
    """
    创建新的聊天会话，并返回会话VO
    - n: 随机选取的示例数量
    - agent_id: 智能体ID
    - user_id: 用户ID
    """
    return chat_session_dao.create_session(n, agent_id, user_id)

# ========================= 获取热门问题 =========================
@session_router.get("/hot")
async def get_hots(n: int, agent_id: int):
    return chat_session_dao.hot_question(n, agent_id)


# ========================= 查询会话细节 =========================
@session_router.get("/{agent_id}/{user_id}/{session_id}")
async def session_detail(agent_id: int, user_id: int, session_id: str):
    """
    查询某个具体会话的详情
    - agent_id: 智能体ID
    - user_id: 用户ID
    - session_id: 会话ID
    """
    agent = AGENTS.get(agent_id, None)
    if agent is None:
        return f"Agent not found (agentId={agent_id})"

    # 调用智能体的 session_detail 方法，获取会话详情
    return await agent.session_detail(user_id, session_id)

# ========================= 停止会话接口 =========================
@session_router.post("/stop")
def stop(session_id: str, agent_id: int):
    """
    停止指定 session 的对话：
    - 根据 agent_id 获取智能体
    - 调用 agent.stop(session_id) 停止该会话
    """
    logger.debug(f"【ChatRouter】收到停止请求：sessionId = {session_id}")

    # 获取智能体
    agent = AGENTS.get(agent_id, None)
    if agent is None:
        error_msg = f"Agent not found (agentId={agent_id})"
        return {"status": "ok", "message": error_msg}

    # 停止会话
    agent.stop(session_id)
    return {"status": "ok"}  # 返回成功状态

# ========================= 查询历史会话 =========================
@session_router.get("/history")
def get_history(agent_id: int , user_id:int):
    return chat_session_dao.query_history_session(agent_id = agent_id, user_id=user_id )
# ========================= 删除历史会话 =========================
@session_router.delete("/history")
def delete_history(agent_id: int , user_id:int, session_id: str):
    return chat_session_dao.delete_history_session(agent_id = agent_id, user_id=user_id ,session_id = session_id)
# ========================= 更新历史会话标题 =========================
@session_router.put("/history")
def update_history(agent_id: int , user_id:int, session_id: str,title:str):
    return chat_session_dao.update_history_session(agent_id = agent_id, user_id=user_id ,
                                                   session_id = session_id,title = title)

