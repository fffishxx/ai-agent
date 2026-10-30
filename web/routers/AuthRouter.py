from fastapi import APIRouter
from pydantic import BaseModel

from dao import app_dao  # 导入 AppDAO 实例，用于生成 token

# ========================= 创建路由对象 =========================
auth_router = APIRouter()

# ========================= 请求体模型 =========================
class AuthChatRequest(BaseModel):
    """
    请求体参数，用于生成 token
    """
    app_key: str                # 应用 key，必填
    app_secret: str | None = None  # 应用 secret，可选（可能用于某些场景）

# ========================= 路由接口 =========================
@auth_router.post("/token")
async def create_token(req: AuthChatRequest):
    """
    POST /auth/token
    根据 app_key 和 app_secret 生成 JWT Token

    请求示例：
    {
        "app_key": "xxx",
        "app_secret": "xxx"
    }

    返回示例：
    {
        "token": "eyJhbGciOiJSUzI1NiIsInR...",
        "expire_hours": 24,
        "app_id": 123
    }
    """
    # 调用 AppDAO 的 create_token 方法生成 token 并返回
    return app_dao.create_token(req.app_key, req.app_secret)