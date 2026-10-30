from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from config import config_manager, logger
from util import JWTUtil

# ========================= 不需要校验 JWT 的 URL 列表 =========================
no_check_list = [
    "/auth/token",      # 获取 token 的接口无需验证
    "/docs",            # FastAPI 文档页面无需验证
    "/openapi.json"     # OpenAPI JSON 描述文件无需验证
]

class RequestFilter(BaseHTTPMiddleware):
    """JWT 验证中间件，负责请求来源和 token 的校验"""

    def __init__(self, app):
        # 从配置文件获取 JWT 公钥（Base64）
        self.public_key = config_manager.get("jwt.public_key")
        super().__init__(app)

    def verify_token(self, token: str) -> bool:
        """
        使用 JWTUtil 验证 token 是否有效
        :param token: 请求中的 token 字符串
        :return: True 表示有效，False 表示无效
        """
        try:
            decoded = JWTUtil.verify_token(token, self.public_key)
            return decoded is not None
        except Exception as e:
            logger.error(e)
            return False

    async def dispatch(self, request: Request, call_next):
        """
        中间件核心方法，每次请求都会经过此方法
        :param request: 请求对象
        :param call_next: 下一个中间件或路由函数
        :return: Response 对象
        """
        path = request.url.path
        logger.debug(f"【RequestFilter】接收到请求路径，path = {path}")

        # ========================= 跳过无需验证的接口 =========================
        if path in no_check_list:
            return await call_next(request)

        # ========================= 校验请求来源 =========================
        request_from = request.headers.get("request-from")
        if request_from != "agent-center-gateway":
            # 非网关请求直接拒绝访问
            return Response(
                status_code=401,
                content="请求只能通过网关转发，不能直接访问！"
            )

        # ========================= 校验 Token =========================
        token = request.headers.get("token")
        if not token:
            return Response(
                status_code=401,
                content="请求中缺少 token ！"
            )

        if not self.verify_token(token):
            return Response(
                status_code=401,
                content="token 已失效！"
            )

        # ========================= 请求合法，继续执行后续处理 =========================
        return await call_next(request)