from typing import Dict, Any
import os
from util import YamlLoader, get_project_root
from common import *


class ConfigManager:
    """
    单例配置管理器，用于加载、获取和管理全局配置。

    特性：
    - 单例模式，确保全局只有一个实例
    - 支持 YAML 配置文件加载
    - 支持嵌套 key 路径访问，例如 'database.host'
    - 支持 ${ENV_VAR} 形式的环境变量替换
    """

    _instance = None
    _config = None  # 存储加载后的全局配置字典

    def __new__(cls):
        """单例模式实现，确保全局仅有一个 ConfigManager 实例"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def load_config(self, file_path="application.yml", default=None, required_keys=None):
        """
        加载 YAML 配置文件，并存储到全局变量 `_config`。

        如果 `_config` 已经加载过，则直接返回已加载内容。

        Args:
            file_path (str): 配置文件路径，相对于项目根目录
            default (dict, optional): 默认值
            required_keys (list, optional): 必须存在的 key 列表，缺失会抛出异常

        Returns:
            dict: 加载后的配置字典
        """
        if self._config is None:
            self._config = YamlLoader.load(
                file_path=get_project_root() / file_path,
                default=default,
                required_keys=required_keys
            )
        return self._config

    def get_config(self) -> Dict[str, Any]:
        """
        获取全局配置字典。

        Raises:
            RuntimeError: 如果配置尚未加载
        """
        if self._config is None:
            raise RuntimeError("配置尚未加载，请先调用 load_config 方法")
        return self._config

    def get(self, key_path: str, default=None):
        """
        根据点分路径获取配置值，例如 'database.host'。

        支持环境变量替换：
        如果值为 "${ENV_VAR}" 形式，则返回系统环境变量的值，如果未设置，则使用 default。

        Args:
            key_path (str): 配置 key 路径，支持嵌套
            default: 如果找不到 key，返回默认值

        Returns:
            Any: 配置值或默认值
        """
        if self._config is None:
            raise RuntimeError("配置尚未加载，请先调用 load_config 方法")

        keys = key_path.split('.')
        current = self._config

        try:
            # 遍历嵌套字典获取值
            for key in keys:
                current = current[key]

            # 支持 ${ENV_VAR} 替换
            if isinstance(current, str) and current.startswith("${") and current.endswith("}"):
                current = os.getenv(current[2:-1], default)

            return current
        except (KeyError, TypeError):
            return default


# ---------------- 全局配置管理器实例 ----------------
config_manager = ConfigManager()
config_manager.load_config()

if __name__ == "__main__":
    print(config_manager.get(SERVER_PORT)) # 输出：18089
    print(config_manager.get(SERVER_HOST)) # 输出：0.0.0.0
    print(config_manager.get(JWT_EXPIRE_HOURS))
