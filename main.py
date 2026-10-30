import asyncio
import os
import uvicorn
from config import config_manager  # 配置管理器
from common import *
from web import app  # FastAPI 应用实例

# ========================= 异步主入口 =========================
async def main():
    """异步主入口函数，用于启动 Web 服务"""
    await start_web()

# ========================= 启动 Web 服务 =========================
async def start_web():
    """启动 FastAPI Web 服务"""
    # 获取配置中的 host 和 port
    host = config_manager.get(SERVER_HOST)
    port = int(config_manager.get(SERVER_PORT))

    # 创建 uvicorn 配置
    config = uvicorn.Config(
        app,            # FastAPI 应用
        host=host,      # 绑定主机
        port=port,      # 绑定端口
        log_level="info",  # 日志等级
        access_log=False,  # 关闭访问日志
    )

    # 创建 uvicorn 异步服务器实例
    server = uvicorn.Server(config)

    # 异步启动服务器
    await server.serve()

# ========================= 项目入口 =========================
if __name__ == "__main__":
    # ⚠️ Windows 上需要使用 SelectorEventLoop 才能兼容 psycopg 异步
    # 注意:不要直接实例化 SelectorEventLoop —— PyCharm Debug 时(ASYNCIO_DEBUGGER_ENV=True)
    # pydevd 的 nest_asyncio 补丁会重写 Task.__init__,通过 call_soon 直接调度 Task 对象,
    # 而 call_soon 的配套补丁只作用于经 asyncio.new_event_loop()/事件循环策略创建的循环。
    # 直接构造的循环缺少该补丁,启动时会报 "TypeError: 'Task' object is not callable"。
    # 改用 WindowsSelectorEventLoopPolicy(底层同样是 SelectSelector)则两种模式都正常。
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 执行异步主入口
    loop.run_until_complete(main())
