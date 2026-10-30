import requests


class HttpClientUtil:

    """
    一个用于调用微服务的通用 HTTP 客户端工具类，
    支持 GET / POST 请求，并带 token 头以及失败降级处理。
    """

    @staticmethod
    def get(url, token, params=None, timeout=20, fallback=None):
        """
        发送 GET 请求
        :param url: 请求地址
        :param token: 鉴权 token
        :param params: URL 参数 dict
        :param timeout: 超时时间(秒)
        :param fallback: 失败时的降级函数，要求为可调用对象
        :return: 响应数据（成功）或降级数据
        """
        headers = {"Authorization": token}
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()  # 如果非 200 直接抛异常
            response.encoding = "utf-8"
            return response.json()
        except Exception as e:
            from config import logger
            logger.error(f"[GET] 请求失败: {url}, 错误: {e}")
            if callable(fallback):
                return fallback()  # 降级处理
            raise  # 如果没有降级方案则继续抛异常

    @staticmethod
    def post(url, token, data=None, json=None, timeout=20, fallback=None):
        """
        发送 POST 请求
        :param url: 请求地址
        :param token: 鉴权 token
        :param data: 表单数据
        :param json: JSON 结构体
        :param timeout: 超时时间
        :param fallback: 降级方案
        :return: 响应数据或降级数据
        """
        headers = {"Authorization": token}
        try:
            response = requests.post(url, data=data, json=json, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            from config import logger
            logger.error(f"[POST] 请求失败: {url}, 错误: {e}")
            if callable(fallback):
                return fallback()
            raise
