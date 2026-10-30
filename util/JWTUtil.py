import datetime
from typing import Dict, Any, Optional

import jwt

# 加密算法，使用 RSA 的 SHA256
algorithm: str = "RS256"


class JWTUtil:
    """
    使用 RSA Base64 公钥/私钥字符串生成和验证 JWT Token 工具类。

    功能：
    1. Base64 -> PEM 转换
    2. 创建 JWT Token
    3. 验证 JWT Token
    """

    @staticmethod
    def b64_to_pem(b64_str: str, key_type: str) -> str:
        """
        将纯 Base64 字符串转换为 PEM 格式。

        Args:
            b64_str (str): 不带头尾的 Base64 字符串
            key_type (str): "PRIVATE" 或 "PUBLIC"

        Returns:
            str: PEM 格式字符串
        """
        # 每64字符换行，符合 PEM 标准
        formatted_key = "\n".join([b64_str[i:i + 64] for i in range(0, len(b64_str), 64)])
        if key_type == "PRIVATE":
            return f"-----BEGIN PRIVATE KEY-----\n{formatted_key}\n-----END PRIVATE KEY-----"
        elif key_type == "PUBLIC":
            return f"-----BEGIN PUBLIC KEY-----\n{formatted_key}\n-----END PUBLIC KEY-----"
        else:
            raise ValueError("key_type 必须是 PRIVATE 或 PUBLIC")

    @staticmethod
    def create_token(data: Dict[str, Any], private_key_b64: str, expire_hours: int = 24) -> str:
        """
        生成 JWT Token

        Args:
            data (Dict[str, Any]): 自定义 payload
            private_key_b64 (str): 私钥 Base64 字符串
            expire_hours (int): Token 有效时间（小时），默认 24h

        Returns:
            str: JWT 字符串
        """
        # 获取当前 UTC 时间
        now = datetime.datetime.now(datetime.timezone.utc)

        # 复制 payload 并添加 iat、exp
        payload = data.copy()
        payload.update({
            "iat": now,  # 签发时间
            "exp": now + datetime.timedelta(hours=expire_hours)  # 过期时间
        })

        # Base64 -> PEM
        private_key = JWTUtil.b64_to_pem(private_key_b64, key_type="PRIVATE")

        # 返回编码后的 JWT
        return jwt.encode(payload, private_key, algorithm=algorithm)

    @staticmethod
    def verify_token(token: str, public_key_b64: str) -> Optional[Dict[str, Any]]:
        """
        验证并解析 JWT Token

        Args:
            token (str): JWT 字符串
            public_key_b64 (str): 公钥 Base64 字符串

        Returns:
            dict 或 None: payload 信息，如果过期或无效则返回 None
        """
        try:
            public_key = JWTUtil.b64_to_pem(public_key_b64, key_type="PUBLIC")
            return jwt.decode(token, public_key, algorithms=algorithm)
        except jwt.ExpiredSignatureError:
            print("❌ Token 已过期")
            return None
        except jwt.InvalidTokenError:
            print("❌ 无效的 Token")
            return None


if __name__ == "__main__":
    # 示例 Base64 公私钥
    private_key_b64 = "MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAKIIk0LxLhUHchzhJ8A607DYSeAgSrPSS5GPdh8vDJshIkgK9YBxEBcqv5km/xyHgpE45FsyQSB5/fXph/ywwgNumYTZUUyt3yi+ygvfZyvpwo4Cz6Jzwp5M2doiG7lKryv0MbIsM3Rs5KU0BOAsMiVVt5LdeM3SSb1lHaQj5zdNAgMBAAECgYACCmxoYTpv8110wnUwtTNc79LTKs6MczwwA7si62gtb/5kvLAydobgWjgT74TMN2MY/YfXijHkMDhXNFWNHi2WiyScGaN3+YesxFUoG5H/2hQAUcDzj1Rryh+gerkWdqoFbGu3d+v5kur+w36VTCD3qpHyADycM//UA7yKb+8i4QJBANQyPNwOUJabDlLjTd42GzvAZTE6gmPrOopsRnHW8TVIHkHXexCMQLQ4TTg6Ct5ShuSTAgYUGPQv3jxpLts+fcUCQQDDe22AtsqnKVaG2KYVYWFLnI3hYNw8wePepZbt/87MPgYtkEc5WjFF/QUlHwLcpc7YW6hrJYwMbZvOB7YVHrPpAkAlbQLs8R1nosuA9RRb2AEvpbxzVVWAGBIILhayp219r02e4UmUXphe8Ps1qo8WLUobcI5P0iWgk/zHfOnFw5zdAkEAh2o+PfbiRZAeT4VO7+qocq99nY3yougRiU+eUTpusA+bSf7zR+iRz5Dp+oAUBHOb6Ub9UVQOQyG+16eB2/mL2QJBAIMjhAu5kTZAWVDpuJ6AtDodscuZQs8EOCdU7hx+aJUMC4K1aeuwD9QhkOZtpA/V2BzgNcqWt5dfntU2ovQ0g1U="
    public_key_b64 = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCiCJNC8S4VB3Ic4SfAOtOw2EngIEqz0kuRj3YfLwybISJICvWAcRAXKr+ZJv8ch4KROORbMkEgef316Yf8sMIDbpmE2VFMrd8ovsoL32cr6cKOAs+ic8KeTNnaIhu5Sq8r9DGyLDN0bOSlNATgLDIlVbeS3XjN0km9ZR2kI+c3TQIDAQAB"

    # 生成 Token
    token = JWTUtil.create_token({"user_id": 123, "role": "admin"}, private_key_b64)
    print("✅ 生成的 token：", token)

    # 验证 Token
    decoded = JWTUtil.verify_token(token, public_key_b64)
    print("✅ 解码结果：", decoded)
