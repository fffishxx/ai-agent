from sqlalchemy import Column, BigInteger, String, DateTime, func, Index
from config import Base

class AppInfo(Base):
    """
    应用信息表 ORM 映射类。

    用于存储应用的 key、secret、名称，以及创建和更新时间。
    """

    # 表名
    __tablename__ = "app_info"

    # ---------------- 字段定义 ----------------
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=False,  # 由外部系统或业务生成，不自动增长
        comment="数据id"
    )
    app_key = Column(
        String(64),
        nullable=False,       # 不允许为空
        comment="应用key"
    )
    app_secret = Column(
        String(64),
        nullable=False,       # 不允许为空
        comment="应用秘钥"
    )
    name = Column(
        String(32),
        nullable=True,        # 应用名称可为空
        comment="应用名称"
    )
    create_time = Column(
        DateTime,
        server_default=func.now(),  # 默认值为当前时间
        nullable=False,
        comment="创建时间"
    )
    update_time = Column(
        DateTime,
        server_default=func.now(),  # 默认值为当前时间
        onupdate=func.now(),         # 更新时自动更新为当前时间
        nullable=False,
        comment="更新时间"
    )

    # ---------------- 索引定义 ----------------
    __table_args__ = (
        Index('app_key', 'app_key'),  # 为 app_key 字段创建索引，加快查询速度
    )

    # ---------------- 字符串表示 ----------------
    def __repr__(self):
        """
        对象的可读字符串表示，方便调试和日志记录。
        """
        return f"<AppInfo(id={self.id}, app_key='{self.app_key}', name='{self.name}')>"