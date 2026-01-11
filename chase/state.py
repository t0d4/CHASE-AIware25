import operator
from typing import Annotated, Literal, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from langgraph.managed import RemainingSteps
from pydantic import BaseModel, Field, computed_field

WorkerAgent = Literal["deobfuscator", "web_researcher", "final_summarizer"]


class SourceCode(BaseModel):
    filename: str
    code: str


class FinalSummary(BaseModel):
    final_verdict: Literal["benign", "malicious"] = Field(
        description="Final verdict indicating if this python code is malicious or not."
    )
    code_description: str = Field(
        description="Brief explanation of the code's behavior and its purpose"
    )
    malicious_actor_goal: Optional[str] = Field(
        description="If this code is malicious, write the attacker's ultimate goal"
    )
    malicious_code_strategy: Optional[str] = Field(
        description="If this code is malicious, write how the the malicious activity is stepwisely carried out from beginning to the completion"
    )
    additional_information: Optional[str] = Field(
        description="Any additional information that is worth mentioning"
    )


class DetectorAgentState(BaseModel):
    today_str: str
    package_name: str
    source_codes: list[SourceCode]
    messages: Annotated[list[AnyMessage], add_messages] = []
    plan: list[tuple[WorkerAgent, str]] = []
    past_steps: Annotated[list[tuple[WorkerAgent, str, str]], operator.add] = []
    final_summary: Optional[str] = None
    final_summary_structured: Optional[FinalSummary] = None
    remaining_steps: RemainingSteps = 25
    remaining_tasks: int = 15

    @computed_field(repr=False)
    @property
    def plan_str(self) -> str:
        return "\n".join(
            f"{i + 1}. {agent_name}: {agent_task}"
            for i, (agent_name, agent_task) in enumerate(self.plan)
        )

    @computed_field(repr=False)
    @property
    def past_steps_str(self) -> str:
        delimiter = "\n---------------\n"
        return (
            delimiter
            + delimiter.join(
                f"## Agent\n\n{ps[0]}\n\n## Task\n\n{ps[1]}\n\n## Response\n\n{ps[2]}"
                for ps in self.past_steps
            )
            + delimiter
        )

    @computed_field(repr=False)
    @property
    def source_codes_str(self) -> str:
        return "\n\n".join(
            f"```python:{c.filename}\n{c.code}\n```" for c in self.source_codes
        )
