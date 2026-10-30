import sys
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=1) # 缓存第一次查找结果，后续调用不再重复遍历父目录，提高性能。
def get_project_root(
    start: Path | None = None,
    markers: tuple[str, ...] = (".git", "main.py", "requirements.txt")
) -> Path:
    """
    自动查找项目根目录。

    查找逻辑：
    1. 从指定起始路径 start（默认是当前文件所在路径）向上递归。
    2. 遇到包含任意 markers 文件或文件夹的目录即返回该目录。
       markers 默认包含: .git, main.py, requirements.txt
    3. 若未找到，返回 start 的父目录。

    Args:
        start (Path | None): 起始查找路径
        markers (tuple[str, ...]): 标识项目根目录的文件或文件夹

    Returns:
        Path: 项目根目录
    """
    if start is None:
        # 默认使用当前文件路径
        start = Path(__file__).resolve()
    elif not isinstance(start, Path):
        start = Path(start).resolve()

    # 遍历当前路径及所有父路径
    for parent in [start, *start.parents]:
        if any((parent / marker).exists() for marker in markers):
            return parent

    # 未找到标记文件，则返回起始路径的父目录
    return start.parent


def add_project_root_to_sys_path() -> Path:
    """
    将项目根目录添加到 sys.path。

    作用：
    - 保证在任意子目录运行脚本时，都能正确导入顶层模块。
    - 如果根目录已经在 sys.path 中，不重复添加。

    Returns:
        Path: 项目根目录
    """
    root = get_project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))  # 插入到 sys.path 最前面优先查找
    return root


# === 示例运行 ===
if __name__ == "__main__":
    root = add_project_root_to_sys_path()
    print(f"项目根目录: {root}")
    print("sys.path 前几项：", sys.path[:3])
