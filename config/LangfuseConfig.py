from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from common import (
    LANGFUSE_BASE_URL,
    LANGFUSE_ENABLED,
    LANGFUSE_ENVIRONMENT,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
)
from config import config_manager, logger


class LangfuseConfig:
    """
    Langfuse 追踪配置管理器。

    功能：
    1. 根据 application.yml 中的 langfuse 配置初始化 Langfuse 客户端（单例）
    2. 提供 LangChain/LangGraph 集成的 CallbackHandler（自动采集 generation/token/model）
    3. 提供 trace_span 上下文管理器，统一设置 trace 名称、session_id、user_id、tags
    4. 未启用或初始化失败时自动降级为 no-op，保证主业务不受观测组件影响

    设计约定（对应 Langfuse 官方最佳实践）：
    - 一次用户请求 = 一条 trace，trace 使用稳定名称（如 "router-agent-chat"）
    - 同一会话的多轮对话通过 session_id 聚合
    - 按智能体 ID 打 tag，便于按功能维度过滤和统计
    """

    def __init__(self):
        # ---------------- Langfuse 配置 ----------------
        self.__enabled = config_manager.get(LANGFUSE_ENABLED, False)
        self.__client = None
        # 延迟导入并缓存引用，langfuse 未安装时本模块仍可正常导入（降级关闭）
        self.__callback_handler = None
        self.__propagate_attributes = None

        if not self.__enabled:
            return

        public_key = config_manager.get(LANGFUSE_PUBLIC_KEY)
        secret_key = config_manager.get(LANGFUSE_SECRET_KEY)
        base_url = config_manager.get(LANGFUSE_BASE_URL)
        environment = config_manager.get(LANGFUSE_ENVIRONMENT, "development")

        # 缺少必要配置时降级关闭，不影响业务启动
        if not public_key or not secret_key or not base_url:
            logger.warning("Langfuse 已启用但缺少 public-key/secret-key/base-url 配置，追踪功能降级关闭")
            self.__enabled = False
            return

        try:
            from langfuse import Langfuse, propagate_attributes
            from langfuse.langchain import CallbackHandler

            self.__callback_handler = CallbackHandler
            self.__propagate_attributes = propagate_attributes
            self.__client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                base_url=base_url,
                environment=environment,
            )
            logger.info("Langfuse 追踪已启用：base_url=%s, environment=%s", base_url, environment)
        except Exception as e:
            # 观测功能不可用不应影响主业务，降级关闭
            logger.warning("Langfuse 初始化失败，追踪功能降级关闭：%s", e)
            self.__enabled = False
            self.__client = None

    # ---------------- 状态查询 ----------------
    def is_enabled(self) -> bool:
        """追踪是否启用"""
        return self.__enabled

    def get_client(self):
        """获取 Langfuse 客户端（未启用时返回 None）"""
        return self.__client

    # ---------------- LangChain 集成 ----------------
    def new_handler(self):
        """
        创建 LangChain CallbackHandler，用于 RunnableConfig 的 callbacks 参数。

        必须在使用它的 with trace_span(...) 代码块内部创建，
        以便自动继承当前 trace 上下文（session_id/user_id/tags）。

        Returns:
            CallbackHandler 或 None：未启用追踪时返回 None，调用方无需挂载回调
        """
        if not self.__enabled:
            return None
        return self.__callback_handler()

    # ---------------- Trace 上下文 ----------------
    @contextmanager
    def trace_span(
            self,
            name: str,
            session_id: Optional[str] = None,
            user_id: Optional[int] = None,
            tags: Optional[List[str]] = None,
            input: Optional[Any] = None,
            metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        根观察（span）上下文管理器：一次用户请求对应一条 Langfuse trace。

        :param name: trace 名称，使用稳定的动作名（如 "router-agent-chat"）
        :param session_id: Langfuse 会话 ID，聚合同一会话的多轮对话
        :param user_id: 用户 ID，用于按用户统计成本和对话质量
        :param tags: 业务维度标签（如 ["agent-1001"]）
        :param input: trace 根输入（用户问题，便于在 trace 列表快速查看）
        :param metadata: 请求上下文（如 request_id），用于关联其他系统日志
        :yield: LangfuseSpan（可调用 update(output=...) 记录最终回答），未启用时为 None
        """
        if not self.__enabled:
            yield None
            return

        kwargs = {"name": name, "as_type": "span"}
        if input is not None:
            kwargs["input"] = input
        if metadata:
            kwargs["metadata"] = metadata

        with self.__client.start_as_current_observation(**kwargs) as span:
            # 将 session/user/tags 传播给 trace 内所有子观察（含 LangChain 回调生成的 generation）
            attrs = {}
            if session_id:
                attrs["session_id"] = session_id
            if user_id is not None:
                attrs["user_id"] = str(user_id)
            if tags:
                attrs["tags"] = tags
            with self.__propagate_attributes(**attrs):
                yield span

    # ---------------- 生命周期 ----------------
    def shutdown(self):
        """服务退出前刷新并关闭客户端，避免未发送的追踪事件丢失"""
        if self.__client is not None:
            try:
                self.__client.shutdown()
            except Exception as e:
                logger.warning("Langfuse shutdown 异常：%s", e)


# ---------------- 全局 Langfuse 配置实例 ----------------
langfuse_config = LangfuseConfig()
