import hashlib
import socket
from snowflake import SnowflakeGenerator


# ---------------- 生成 worker_id ----------------
def get_worker_id():
    """
    根据本机 IP 生成一个 worker_id（0~31 范围），用于 Snowflake ID 生成器。

    流程：
    1. 获取主机名
    2. 获取对应 IP 地址
    3. 对 IP 地址做 MD5 哈希，并转为整数
    4. 对 32 取模，确保 worker_id 在 0~31 之间
    """
    hostname = socket.gethostname()  # 获取本机主机名
    ip = socket.gethostbyname(hostname)  # 获取主机名对应的 IP
    hash_val = int(hashlib.md5(ip.encode()).hexdigest(), 16)  # MD5 哈希并转整数
    return hash_val % 32  # Snowflake worker_id 限制在 0~31


# 获取当前机器的 worker_id
worker_id = get_worker_id()

# ---------------- 创建 Snowflake ID 生成器 ----------------
# SnowflakeGenerator 是基于 Twitter Snowflake 算法的唯一 ID 生成器
# worker_id 用于区分不同机器，保证分布式环境下 ID 唯一性
generator = SnowflakeGenerator(worker_id)


# ---------------- 获取全局唯一 ID ----------------
def get_id():
    """
    获取下一个全局唯一 ID。
    每次调用返回一个 64 位整数，保证全局唯一。
    """
    return next(generator)


# ---------------- 测试 / 示例 ----------------
if __name__ == '__main__':
    for i in range(10):
        print(get_id())  # 输出 10 个唯一 ID
