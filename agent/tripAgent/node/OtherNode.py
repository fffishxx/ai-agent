from datetime import date
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig

from agent.prompts import system_prompt_config
from agent.tripAgent.node.BaseTripNode import BaseTripNode
from agent.tripAgent.TripState import TripState


class OtherNode(BaseTripNode):
    """其他意图兜底"""

    async def execute(self, state: TripState, config: RunnableConfig) -> Dict[str, Any]:
        return await self.answer(
            state,
            config,
            system_prompt_config.other_prompt.format(
                today=date.today().isoformat(),
                trip_context=self.trip_context(state),
            ),
        )
