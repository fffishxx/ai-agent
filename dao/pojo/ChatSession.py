from sqlalchemy import Column, BigInteger, String, DateTime, func
from config import Base

class ChatSession(Base):
    """
    聊天会话表 ORM 映射类。

    用于存储用户与智能体的会话信息，包括会话ID、用户ID、智能体ID、会话标题及时间信息。
    """

    # 表名
    __tablename__ = "chat_session"

    # ---------------- 字段定义 ----------------
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=False,  # 数据ID由外部或业务系统生成，不自动增长
        comment="数据id"
    )
    session_id = Column(
        String(32),
        nullable=False,       # 会话ID不能为空
        comment="会话id"
    )
    user_id = Column(
        BigInteger,
        nullable=False,
        default=0,            # 默认用户ID为0（匿名或未指定用户）
        comment="用户id"
    )
    agent_id = Column(
        BigInteger,
        nullable=False,       # 对应智能体ID，不能为空
        comment="智能体id"
    )
    title = Column(
        String(100),
        nullable=True,        # 会话标题可为空
        comment="会话标题"
    )
    create_time = Column(
        DateTime,
        server_default=func.now(),  # 默认创建时间为当前时间
        nullable=False,
        comment="创建时间"
    )
    update_time = Column(
        DateTime,
        server_default=func.now(),  # 默认更新时间为当前时间
        onupdate=func.now(),         # 更新时自动修改为当前时间
        nullable=False,
        comment="更新时间"
    )

    # ---------------- 字符串表示 ----------------
    def __repr__(self):
        """
        对象的可读字符串表示，便于调试和日志查看。
        """
        return f"<ChatSession(id={self.id}, session_id='{self.session_id}', title='{self.title}')>"