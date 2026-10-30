import redis
from config import config_manager


class RedisConfig:
    """
    Redis 配置管理器。

    功能：
    1. 根据配置文件初始化 Redis 客户端
    2. 提供全局可访问的 Redis 实例
    """

    def __init__(self):
        # ---------------- Redis 连接配置 ----------------
        self._host = config_manager.get("redis.host", "127.0.0.1")  # Redis 主机地址
        self._port = int(config_manager.get("redis.port", 6379))  # Redis 端口
        self._password = config_manager.get("redis.password", 6379)  # Redis 密码

        # ---------------- 创建 Redis 客户端 ----------------
        # decode_responses=True 会自动将返回的 bytes 转为 str
        self._redis = redis.Redis(
            host=self._host,
            port=self._port,
            password=self._password,
            decode_responses=True
        )

    # ---------------- 获取 Redis 实例 ----------------
    def get_instance(self):
        """
        获取 Redis 客户端实例。

        Returns:
            redis.Redis: Redis 客户端
        """
        return self._redis


# ---------------- 全局 Redis 配置实例 ----------------
redis_config = RedisConfig()