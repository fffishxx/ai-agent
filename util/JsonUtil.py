import orjson
from dataclasses import is_dataclass, asdict, dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Type, TypeVar

T = TypeVar("T")


class JsonUtil:

    @staticmethod
    def to_str(data: Any) -> str:
        """
        将 Python 对象序列化为 JSON 字符串。
        支持 dataclass、datetime、date、Decimal。
        """

        def default(obj):
            if is_dataclass(obj):
                return asdict(obj)  # 将 dataclass 转为 dict
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()  # datetime/date 转 ISO 格式字符串
            if isinstance(obj, Decimal):
                return float(obj)  # Decimal 转 float
            raise TypeError(f"对象类型 {type(obj)} 不可序列化")

        return orjson.dumps(data, default=default).decode("utf-8")

    @staticmethod
    def to_obj(json_str: str, cls: Type[T] = None) -> Any:
        """
        将 JSON 字符串反序列化为 Python 对象。
        如果 cls 是 dataclass，则返回 dataclass 实例。
        否则返回 dict/list 等原生类型。
        """
        obj = orjson.loads(json_str)
        if cls and is_dataclass(cls):
            return cls(**obj)
        return obj
