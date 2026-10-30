from datetime import date
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig

from agent.tripAgent.node.BaseTripNode import BaseTripNode
from agent.tripAgent.TripState import TripState
from agent.prompts import system_prompt_config


class KnowledgeNode(BaseTripNode):
    """旅游知识问答"""

    async def execute(self, state: TripState, config: RunnableConfig) -> Dict[str, Any]:

        return await self.answer(
            state,
            config,
            system_prompt_config.knowledge_prompt.format(
                today=date.today().isoformat(),
                trip_context=self.trip_context(state),
            ),
        )
