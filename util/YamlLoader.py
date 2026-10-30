import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class YamlLoader:
    """
    YAML 配置文件加载器

    功能：
    - 加载 YAML 文件为 Python 字典
    - 提供默认值 fallback
    - 可验证必须存在的配置键路径
    """

    @staticmethod
    def load(
            file_path: str | Path,
            default: Optional[Dict[str, Any]] = None,
            required_keys: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        加载并验证 YAML 文件

        Args:
            file_path: YAML 文件路径（字符串或 Path 对象）
            default: 当文件不存在时使用的默认配置字典
            required_keys: 必须存在的键路径列表，例如 ['database.host', 'api.keys']

        Returns:
            dict: 解析后的 YAML 数据（字典形式）
        """

        path = Path(file_path)  # 确保路径是 Path 对象
        data = default.copy() if default else {}  # 初始化数据，优先使用默认值

        # ================= 文件读取与解析 =================
        if path.exists():  # 文件存在则尝试读取
            try:
                with path.open('r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}  # 安全加载 YAML，避免返回 None
            except yaml.YAMLError as e:  # YAML 语法错误
                raise ValueError(f"YAML 语法错误 ({path}): {e}")
        elif default is None:
            # 文件不存在且没有默认值则报错
            raise FileNotFoundError(f"配置文件缺失: {path}")

        # ================= 必要键路径验证 =================
        if required_keys:
            missing = []  # 用于记录缺失的配置项
            for key_path in required_keys:
                keys = key_path.split('.')  # 支持嵌套路径
                current = data
                for key in keys:
                    # 检查当前层级是否包含目标键
                    if isinstance(current, dict) and key in current:
                        current = current[key]  # 继续深入
                    else:
                        missing.append(key_path)
                        break  # 找不到直接跳出
            if missing:
                raise KeyError(f"缺少必要配置项: {', '.join(missing)}")

        return data  # 返回最终配置字典


# ================= 使用示例 =================
# try:
#     config = YamlLoader.load(
#         "app_config.yml",
#         default={"debug": False, "log_level": "INFO"},
#         required_keys=["database.host", "api.keys"]
#     )
#     print("数据库主机:", config["database"]["host"])
# except Exception as e:
#     print(f"配置加载失败: {e}")
#     # 处理错误逻辑...
