import json
import re
from typing import Final, Type, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages.human import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import RunnablePassthrough, RunnableSerializable
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from langgraph.utils.runnable import RunnableCallable
from pydantic import BaseModel, Field

from chase.state import DetectorAgentState, FinalSummary, WorkerAgent
from chase.supervisor_prompts import (
    FINAL_SUMMARIZE_PROMPT,
    FIRST_PLANNING_PROMPT,
    FORMAT_PLANNING_PROMPT,
    REFRESH_PLANNING_PROMPT,
    SUPERVISOR_PROMPT,
)

SUPERVISOR_NAME: Final[str] = "malware_analyst_team_supervisor"

reasoning_tokens_remover = RunnableCallable(
    lambda reasoning_model_output: re.sub(
        pattern=r".+?<\/think>",
        repl="",
        string=reasoning_model_output,
        flags=re.DOTALL,
    ).strip(),
    name="remove_reasoning_tokens",
)

state_dict_converter = RunnableCallable(
    lambda state: state.model_dump(), name="convert_state_into_dict"
)  # NOTE: ChatPromptTemplate and RunnablePassthrough.assign requires the input to be a dictionary

T = TypeVar("T", bound=BaseModel)


def get_reason_and_format_chain(
    reasoning_llm: BaseChatModel,
    prompts_for_reasoning_llm: ChatPromptTemplate,
    formatter_llm: BaseChatModel,
    prompt_for_formatter_llm: str,
    output_schema: Type[T],
) -> RunnableSerializable[DetectorAgentState, T]:
    """If you want to give the reasoning LLM a system prompt, include it in `prompts_for_reasoning_llm`.

    Args:
        reasoning_llm (BaseChatModel): _description_
        prompts_for_reasoning_llm (ChatPromptTemplate): _description_
        formatter_llm (BaseChatModel): _description_
        prompt_for_formatter_llm (str): _description_
        output_schema (Type[T]): _description_

    Raises:
        ValueError: _description_

    Returns:
        RunnableSerializable[DetectorAgentState, T]: _description_
    """

    _keys_in_prompt = [
        "{reasoning_model_output_without_reasoning_token}",
        "{output_json_schema_str}",
    ]
    if any(key not in prompt_for_formatter_llm for key in _keys_in_prompt):
        raise ValueError(
            f"the argument prompt_for_formatter_llm must contain {_keys_in_prompt}"
        )

    return (
        state_dict_converter
        | RunnablePassthrough.assign(
            reasoning_model_output_without_reasoning_token=(
                prompts_for_reasoning_llm
                | reasoning_llm
                | StrOutputParser()
                | reasoning_tokens_remover
            ),
            output_json_schema_str=lambda _: json.dumps(
                output_schema.model_json_schema()
            ),  # https://github.com/langchain-ai/langchain/issues/1660#issuecomment-2205457481
        )
        | ChatPromptTemplate(
            [HumanMessagePromptTemplate.from_template(prompt_for_formatter_llm)]
        )
        | formatter_llm.with_structured_output(output_schema).with_retry(
            stop_after_attempt=20  # NOTE: structured output sometimes fails, so retry on exceptions
        )
    )  # type: ignore


class AnalysisPlan(BaseModel):
    plan: list[tuple[WorkerAgent, str]] = Field(
        description="list of pairs (agent_name, task_description) describing each step of the plan"
    )


def get_refresh_plan_node(reasoning_llm: BaseChatModel, formatter_llm: BaseChatModel):
    first_planning_prompt = ChatPromptTemplate(
        [
            SystemMessagePromptTemplate.from_template(SUPERVISOR_PROMPT),
            HumanMessagePromptTemplate.from_template(FIRST_PLANNING_PROMPT),
        ]
    )

    refresh_planning_prompt = ChatPromptTemplate(
        [
            SystemMessagePromptTemplate.from_template(SUPERVISOR_PROMPT),
            HumanMessagePromptTemplate.from_template(REFRESH_PLANNING_PROMPT),
        ]
    )

    def refresh_plan(state: DetectorAgentState, config: RunnableConfig):
        planning_prompt = (
            refresh_planning_prompt if state.past_steps else first_planning_prompt
        )
        plan = get_reason_and_format_chain(
            reasoning_llm=reasoning_llm,
            prompts_for_reasoning_llm=planning_prompt,
            formatter_llm=formatter_llm,
            prompt_for_formatter_llm=FORMAT_PLANNING_PROMPT,
            output_schema=AnalysisPlan,
        ).invoke(state)
        if not plan.plan:  # when empty plan is returned
            # go back to this state again
            return Command(goto="refresh_plan")
        next_node = plan.plan[0][0]
        return Command(
            goto=next_node,
            update={
                "plan": plan.plan,
                "remaining_tasks": state.remaining_tasks - 1,
            },
            graph=None if next_node == "final_summarizer" else Command.PARENT,
        )

    return refresh_plan


def get_final_summarize_node(
    summarizer_llm: BaseChatModel, formatter_llm: BaseChatModel
):
    summarization_plan_retriever = RunnableCallable(
        lambda state: "\n".join(
            state["plan"][i][1]
            for i in range(len(state["plan"]))
            if state["plan"][i][0] == "final_summarizer"
        ),  # extract the remaining plan's description
        name="organize_final_summarization_plan",
    )

    final_summarization_prompt = ChatPromptTemplate(
        [
            SystemMessagePromptTemplate.from_template(SUPERVISOR_PROMPT),
            HumanMessagePromptTemplate.from_template(FINAL_SUMMARIZE_PROMPT),
        ]
    )
    summarization_chain = (
        state_dict_converter
        | RunnablePassthrough.assign(summarization_plan=summarization_plan_retriever)
        | final_summarization_prompt
        | summarizer_llm
        | StrOutputParser()
        | reasoning_tokens_remover
    )

    def final_summarize(state: DetectorAgentState, config: RunnableConfig):
        final_summary_text: str = summarization_chain.invoke(state)
        final_summary_structured: FinalSummary = (
            formatter_llm.with_structured_output(FinalSummary)
            .with_retry(
                stop_after_attempt=20  # NOTE: structured output sometimes fails, so retry on exceptions
            )
            .invoke(
                [
                    HumanMessage(
                        f"Convert the following summary into JSON:\n\n{final_summary_text}"
                        + f"\n\n\nOutput a JSON object strictly matching the following schema, without any surrounding text or symbols:\n{json.dumps(FinalSummary.model_json_schema())}"
                    )
                ]
            )
        )  # type: ignore

        return {
            "final_summary": final_summary_text,
            "final_summary_structured": final_summary_structured,
        }

    return final_summarize


def create_supervisor(
    supervisor_llm: BaseChatModel,
    formatter_llm: BaseChatModel,
) -> CompiledStateGraph[DetectorAgentState, DetectorAgentState, DetectorAgentState]:
    return (
        StateGraph(DetectorAgentState)
        .add_node(
            "refresh_plan",
            get_refresh_plan_node(
                reasoning_llm=supervisor_llm, formatter_llm=formatter_llm
            ),
        )
        .add_node(
            "final_summarizer",
            get_final_summarize_node(
                summarizer_llm=supervisor_llm, formatter_llm=formatter_llm
            ),
        )
        .add_edge(START, "refresh_plan")
        .add_edge("final_summarizer", END)
        .compile(name=SUPERVISOR_NAME)
    )
