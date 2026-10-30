from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Example:
    """
    Example类表示每个示例的标题和描述。
    """
    # 示例的标题，描述了示例的类型或内容
    title: Optional[str] = None
    # 示例的描述，具体说明了示例的内容或问题
    describe: Optional[str] = None

@dataclass
class SessionVO:
    """
    SessionVO类用于表示AI助手会话的相关信息。
    """
    # 会话ID，用于唯一标识当前的AI助手会话
    sessionId: Optional[str] = None
    # AI助手的标题，用于显示助手的名称或身份
    title: Optional[str] = None
    # AI助手的描述，简要介绍助手的功能或特点
    describe: Optional[str] = None
    # 示例列表，包含一些使用助手的示例
    examples: Optional[List[Example]] = None