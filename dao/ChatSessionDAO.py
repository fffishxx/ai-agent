import random
import uuid
from collections import defaultdict
from datetime import datetime, date

from certifi import where
from sqlalchemy import select,delete,update
from sqlalchemy.orm import scoped_session
from vo import SessionVO, Example

from config import config_manager, get_id, logger
from dao.BaseDAO import BaseDAO
from dao.pojo import ChatSession

class ChatSessionVO:
    """会话展示用的 Value Object"""

    def __init__(self, session_id: str, title: str, update_time: datetime):
        self.session_id = session_id
        self.title = title
        self.update_time = update_time


# 时间分组常量
TODAY = "当天"
LAST_30_DAYS = "最近30天"
LAST_YEAR = "最近1年"
MORE_THAN_YEAR = "1年以上"


# 标准返回消息
SUCCESS_MESSAGE = {"status": "ok"}
NO_CHANGE_MESSAGE = {"status": "ok", "message": "No change"}

class ChatSessionDAO(BaseDAO):
    """
    ChatSession 数据访问对象（DAO）。

    提供功能：
    1. 创建聊天会话
    2. 查询历史会话并按时间分组
    3. 更新会话标题
    4. 删除历史会话
    """

    def create_session(self, num: int, agent_id: int, user_id: int) -> SessionVO:
        """
        创建新的聊天会话，并随机选取示例。

        Args:
            num (int): 随机选取的示例数量
            agent_id (int): 智能体 ID
            user_id (int): 用户 ID

        Returns:
            SessionVO: 会话数据对象，包括示例列表
        """

        logger.debug("开始创建新的 ChatSession（示例数量: %d）", num)

        def _create(session: scoped_session):
            # 创建并保存新的聊天会话
            chat_session = ChatSession(
                id=get_id(),  # 全局唯一ID
                session_id=uuid.uuid4().hex,  # 会话UUID
                user_id=user_id,
                agent_id=agent_id
            )
            session.add(chat_session)  # 添加到数据库 session
            logger.debug("ChatSession 已创建：id=%s, session_id=%s", chat_session.id, chat_session.session_id)
            # 构建 SessionVO 返回对象
            session_vo = SessionVO(
                sessionId=chat_session.session_id,
                title=config_manager.get(f"ai.{agent_id}.session.title"),
                describe=config_manager.get(f"ai.{agent_id}.session.describe"),
                examples=self.hot_question(num,agent_id)
            )

            logger.debug("ChatSession 创建成功，session_id=%s", chat_session.session_id)
            return session_vo

        return self._execute(_create)

    def hot_question(self, num, agent_id):
        question_list = config_manager.get(f"ai.{agent_id}.session.examples",[])
        res_index = random.sample(range(0, len(question_list)), num)
        res = []
        for i in res_index:
            res.append(question_list[i])

        return res

    def update_title(self, session_id: str, agent_id: int, title: str):
        """
        更新会话的标题，并返回命中的会话记录。

        Args:
            session_id (str): 会话 ID
            agent_id (int): 智能体 ID
            title (str): 新标题

        Returns:
            ChatSession 或 None: 命中的会话记录（调用方可读取 user_id 等字段，用于 Langfuse 追踪）；会话不存在时返回 None
        """

        def _update(session: scoped_session):
            stmt = (select(ChatSession)
                    .where(ChatSession.session_id == session_id)  # type: ignore
                    .where(ChatSession.agent_id == agent_id))
            chat_session: ChatSession = session.execute(stmt).scalars().first()
            if not chat_session:
                return None

            if not chat_session.title and title:
                chat_session.title = title[:100]  # 限制长度

            chat_session.update_time = datetime.now()
            return chat_session

        return self._execute(_update)

    def query_history_session(self, agent_id: int, user_id: int):

        """
        查询历史会话，并按时间分组（当天、30天、1年、超过1年）。

        Args:
            agent_id (int): 智能体 ID
            user_id (int): 用户 ID

        Returns:
            dict: 按时间分组的 ChatSessionVO 列表
        """

        def _query_history(session: scoped_session):

            stmt = (select(ChatSession).where(ChatSession.agent_id == agent_id)
                                        .where(ChatSession.user_id == user_id)
                                        .where(ChatSession.title.isnot(None))
                                        .order_by(ChatSession.update_time.desc()))
            result = session.execute(stmt).scalars()

            if not result:
                return None

            chat_session_list =  [
                ChatSessionVO(
                    session_id=res.session_id,
                    title=res.title,
                    update_time=res.update_time
                )
            for res in result]
            logger.info(f"查询到数据共有{len(chat_session_list)}")

            # 按时间分组
            now = date.today()
            groups = defaultdict(list)
            for vo in chat_session_list:
                days = abs((now - vo.update_time.date()).days)
                if days == 0:
                    key = TODAY
                elif days <= 30:
                    key = LAST_30_DAYS
                elif days <= 365:
                    key = LAST_YEAR
                else:
                    key = MORE_THAN_YEAR
                groups[key].append(vo)

            # 按顺序返回
            order = [MORE_THAN_YEAR, LAST_YEAR, LAST_30_DAYS, TODAY]
            return {key: groups[key] for key in order if key in groups}

        return self._execute(_query_history)

    def delete_history_session(self, agent_id: int, user_id: int , session_id: str):
        """
        删除历史会话。

        Args:
            agent_id (int): 智能体 ID
            user_id (int): 用户 ID
            session_id (str): 会话 ID

        Returns:
            dict: SUCCESS_MESSAGE 或 NO_CHANGE_MESSAGE
        """
        def _delete_history(session: scoped_session):

            stmt = (delete(ChatSession).where(ChatSession.session_id == session_id)
                                        .where(ChatSession.user_id == user_id)
                                        .where(ChatSession.agent_id == agent_id))
            res = session.execute(stmt)

            return SUCCESS_MESSAGE if res.rowcount > 0 else NO_CHANGE_MESSAGE

        return self._execute(_delete_history)

    def update_history_session(self, agent_id: int, user_id: int , session_id: str,title: str):
        """
        更新历史会话标题。

        Args:
            agent_id (int): 智能体 ID
            user_id (int): 用户 ID
            session_id (str): 会话 ID
            title (str): 新标题

        Returns:
            dict: SUCCESS_MESSAGE 或 NO_CHANGE_MESSAGE
        """
        def _update_history(session: scoped_session):
            stmt = (update(ChatSession).where(ChatSession.session_id == session_id)
                                        .where(ChatSession.agent_id == agent_id)
                                        .where(ChatSession.user_id == user_id)
                                        .values(title=title[:100]))
            res = session.execute(stmt)
            return SUCCESS_MESSAGE if res.rowcount > 0 else NO_CHANGE_MESSAGE

        return self._execute(_update_history)
# 全局 ChatSessionDAO 实例
chat_session_dao = ChatSessionDAO()

if __name__ == '__main__':
    # for e in chat_session_dao.hot_question(3, "1001"):
    #     print(e)

    dirt = chat_session_dao.query_history_session(1001,3)

    print(dirt)
