from typing import Any, Dict

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from agent.tripAgent import prompts
from agent.tripAgent.node.BaseTripNode import BaseTripNode
from agent.tripAgent.TripState import TripState


class ClarifyNode(BaseTripNode):
    """目的地缺失时输出追问话术"""

    async def execute(self, state: TripState, config: RunnableConfig) -> Dict[str, Any]:
        question = state.get("clarification_question") or prompts.CLARIFY_DESTINATION
        return {"messages": [AIMessage(
            content=question,
            response_metadata={"need_clarification": True},
        )]}
