from contextlib import contextmanager
from typing import Callable, Generator, TypeVar

from sqlalchemy.orm import scoped_session

from config import SessionLocal, logger

T = TypeVar('T')  # 泛型类型，用于 _execute 方法的返回值类型提示

class BaseDAO:
    """
    所有 DAO 的基础类。

    功能：
    1. 提供数据库会话的上下文管理
    2. 统一执行数据库操作并捕获异常
    3. 提供事务自动提交/回滚机制
    """

    @contextmanager
    def _session_scope(self) -> Generator[scoped_session, None, None]:
        """
        数据库会话上下文管理器。

        功能：
        - 自动创建数据库 session
        - 事务操作完成后自动提交
        - 如果发生异常则回滚事务
        - 最终关闭 session，避免连接泄漏

        Yields:
            session (scoped_session): SQLAlchemy 会话对象
        """
        session = SessionLocal()  # 从全局 Session 工厂获取 session
        try:
            yield session  # 暴露给 with 语句使用
            session.commit()  # 会话正常执行完毕后提交事务
        except Exception as e:
            session.rollback()  # 遇到异常回滚事务
            logger.exception("数据库事务执行失败，已回滚。错误详情：%s", e)
            raise  # 继续抛出异常，供外层处理
        finally:
            session.close()  # 关闭会话，释放连接资源

    def _execute(self, func: Callable[[scoped_session], T]) -> T:
        """
        统一执行数据库操作并捕获异常。

        功能：
        1. 自动创建 session（通过 _session_scope）
        2. 调用传入的 func 函数执行数据库逻辑
        3. 捕获并记录异常，保证日志完整

        Args:
            func (Callable[[scoped_session], T]): 接受 session 的函数，用于执行数据库操作

        Returns:
            T: func 执行的返回值
        """
        try:
            # 使用上下文管理器自动管理事务和 session
            with self._session_scope() as session:
                return func(session)
        except Exception as e:
            # 捕获异常并记录日志
            logger.exception("数据库操作失败：%s", e)
            raise  # 异常继续抛出，调用方可处理
