from sqlalchemy import select
from sqlalchemy.orm import scoped_session
from dao.BaseDAO import BaseDAO
from dao.pojo import AppInfo
from util import JWTUtil
from config import config_manager
from common import *


class AppDAO(BaseDAO):
    """
    应用数据访问对象（DAO）。

    功能：
    1. 通过 app_key 和 app_secret 验证应用身份
    2. 生成访问接口的 JWT 凭证
    """

    def __init__(self):
        """
        初始化 DAO，读取 JWT 配置：
        - expire_hours: token 有效期（小时）
        - private_key: 用于签发 JWT 的私钥
        """
        print(config_manager.get(JWT_EXPIRE_HOURS))
        self._expire_hours = int(config_manager.get(JWT_EXPIRE_HOURS))
        self._private_key = config_manager.get(JWT_PRIVATE_KEY)

    def create_token(self, app_key: str, app_secret: str):
        """
        通过 app_key 和 app_secret 获取访问接口凭证（JWT）。

        Args:
            app_key (str): 应用的唯一 key
            app_secret (str): 应用的密钥

        Returns:
            dict: 包含 token、有效期和 app_id 信息
        """

        def _query_app_info(session: scoped_session):
            """
            内部查询方法，在数据库中验证 app_key 和 app_secret。
            """
            # 查询 app_info 表中匹配的记录
            stmt = select(AppInfo).where(AppInfo.app_key == app_key)  # type: ignore
            result = session.execute(stmt).scalars().first()

            # 检查是否存在该应用
            if result is None:
                raise Exception("生成凭证失败，app_key不存在")

            # 校验 app_secret 是否匹配
            if result.app_secret != app_secret:
                raise Exception("生成凭证失败，请检查 app_key 和 app_secret 是否正确")

            # 生成 JWT token，指定有效期
            new_token = JWTUtil.create_token(
                data={
                    "app_id": result.id,
                    "app_key": app_key,
                    "name": result.name
                },
                private_key_b64=self._private_key,
                expire_hours=self._expire_hours
            )

            return {
                "token": new_token,
                "expire_hours": self._expire_hours,
                "app_id": result.id
            }

        # 使用 BaseDAO 提供的执行方法执行数据库操作
        return self._execute(_query_app_info)


# ---------------- 全局 DAO 实例 ----------------
app_dao = AppDAO()


if __name__ == "__main__":
    """
    测试示例：
    通过指定 app_key 和 app_secret 生成 JWT token
    """
    res = app_dao.create_token(
        "ddd8c127b3c1baa5f2ca7280d287a102",
        "5ca5087fd74a5afd5cb1cad3016e4980"
    )
    print(res)