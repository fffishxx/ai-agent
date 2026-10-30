from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from config import config_manager
from common import *

# ---------------- 数据库配置 ----------------
# 从全局配置管理器读取数据库连接 URL
database_url = config_manager.get(DB_URL)

# ---------------- 创建 SQLAlchemy Engine ----------------
# Engine 是 SQLAlchemy 的核心接口，管理数据库连接和连接池
engine = create_engine(
    url=database_url,
    pool_size=config_manager.get(DB_POOL_SIZE),       # 连接池大小（同时保持的最小连接数）
    max_overflow=config_manager.get(DB_MAX_OVERFLOW), # 超出池大小时允许的最大临时连接数
    pool_timeout=config_manager.get(DB_POOL_TIMEOUT), # 池中无可用连接时的最大等待时间（秒）
    pool_recycle=config_manager.get(DB_POOL_RECYCLE), # 连接回收时间（秒），避免连接过期
    echo=bool(config_manager.get(DB_ECHO))            # 是否在控制台输出 SQL 日志
)

# ---------------- ORM 基类 ----------------
# 所有 ORM 映射类都应继承 Base
Base = declarative_base()

# ---------------- 创建线程安全的 Session 工厂 ----------------
# 使用 scoped_session 保证多线程环境下每个线程拥有独立 Session
# sessionmaker(bind=engine) 创建 Session 工厂
# expire_on_commit=False：commit 后不失效 ORM 对象的已加载属性，
# 避免 session 关闭后访问属性（如 chat_session.user_id）触发 DetachedInstanceError
SessionLocal = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))
