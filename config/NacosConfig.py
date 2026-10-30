from nacos import NacosClient
from config import config_manager
from common import *

class NacosConfig:
    """
    Nacos 配置管理器。

    功能：
    1. 连接 Nacos 配置中心，获取配置信息
    2. 连接 Nacos 注册中心，实现服务发现
    3. 提供全局可访问的客户端实例
    """

    def __init__(self):
        # ---------------- Nacos 配置 ----------------
        self.__server_addr = config_manager.get(NACOS_SERVER_ADDR)           # Nacos 服务地址
        self.__username = config_manager.get(NACOS_USERNAME, "nacos")       # Nacos 用户名
        self.__password = config_manager.get(NACOS_PASSWORD, "nacos")       # Nacos 密码
        self.__config_namespace = config_manager.get(NACOS_CONFIG_NAMESPACE, "public")  # 配置命名空间
        self.__config_group = config_manager.get(NACOS_CONFIG_GROUP, "DEFAULT_GROUP")   # 配置分组
        self.__discovery_namespace = config_manager.get(NACOS_DISCOVERY_NAMESPACE, "public")  # 注册命名空间
        self.__discovery_group = config_manager.get("nacos.discovery.group", "DEFAULT_GROUP")     # 注册分组
        self.__discovery_ip = config_manager.get(NACOS_DISCOVERY_IP, "127.0.0.1")             # 本机 IP
        self.__discovery_name = config_manager.get(NACOS_DISCOVERY_NAME, "default_server_name") # 服务名称

        # ---------------- 创建 Nacos 配置中心客户端 ----------------
        self.__config_client = NacosClient(
            server_addresses="http://" + self.__server_addr,  # Nacos 服务器地址
            namespace=self.__config_namespace,               # 命名空间 ID
            username=self.__username,                        # 用户名
            password=self.__password,                         # 密码
            logDir="logs/"
        )

        # ---------------- 创建 Nacos 注册中心客户端 ----------------
        self.__discovery_client = NacosClient(
            server_addresses="http://" + self.__server_addr,  # Nacos 服务器地址
            namespace=self.__discovery_namespace,            # 注册命名空间
            username=self.__username,                        # 用户名
            password=self.__password,                         # 密码
            logDir="logs/",
        )

        # 关闭客户端缓存，保证每次获取最新数据
        self.__config_client.no_snapshot = True
        self.__discovery_client.no_snapshot = True

    # ---------------- 配置操作方法 ----------------
    def load_config(self, data_id: str):
        """
        加载 Nacos 中的指定配置。

        Args:
            data_id (str): 配置标识

        Returns:
            str: 配置内容
        """
        return self.__config_client.get_config(
            data_id=data_id,
            group=self.__config_group,
            timeout=10  # 请求超时时间（秒）
        )

    # ---------------- 客户端获取方法 ----------------
    def get_config_client(self):
        """获取 Nacos 配置中心客户端实例"""
        return self.__config_client

    def get_discovery_client(self):
        """获取 Nacos 注册中心客户端实例"""
        return self.__discovery_client

    # ---------------- 服务注册信息 ----------------
    def get_discovery_ip(self):
        """获取本机服务 IP"""
        return self.__discovery_ip

    def get_discovery_name(self):
        """获取本机服务名称"""
        return self.__discovery_name

    def get_discovery_group(self):
        """获取注册服务分组"""
        return self.__discovery_group


# ---------------- 全局 Nacos 配置实例 ----------------
nacos_config = NacosConfig()