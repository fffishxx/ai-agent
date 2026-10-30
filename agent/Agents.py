from agent.BaseAgent import BaseAgent
from agent.tripAgent import trip_agent


# 智能体id 与 对应的智能体实例
AGENTS: dict[int, BaseAgent] = {
    trip_agent.id(): trip_agent  # 1004
}