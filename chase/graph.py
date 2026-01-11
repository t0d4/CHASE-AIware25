import textwrap

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.utils.runnable import RunnableCallable

from chase.agents import init_worker_agents
from chase.state import DetectorAgentState
from chase.supervisor import (
    SUPERVISOR_NAME,
    create_supervisor,
    reasoning_tokens_remover,
)

REASONING_FAILED_RESPONSE = """\
**Error during agent execution!**
Reasoning did not finish within the agent's context window due to excessive complexity of the task.
Please further break the task into smaller steps and pass it to me again.
"""

TOOLCALL_FAILED_RESPONSE = """\
**Error during agent's tool calling!**
Agent's tool calling failed due to excessive length of the value that the agent attempted to give \
to its tool. This may be because of overly complex string which is challenging for LLM to write down precisely.
"""


def get_wrapped_worker_agent(
    worker_agent: CompiledStateGraph[
        DetectorAgentState, DetectorAgentState, DetectorAgentState
    ],
):
    last_message_extractor = RunnableCallable(
        lambda state: state["messages"][-1], name="extract_last_message"
    )
    unfinished_reasoning_replacer = RunnableCallable(
        lambda maybe_cleaned_output: REASONING_FAILED_RESPONSE
        if maybe_cleaned_output.strip().startswith("<think>")
        and "</think>"
        not in maybe_cleaned_output  # the start of reasoning tokens remain in the output
        else maybe_cleaned_output,
        name="insert_error_if_reasoning_failed",
    )
    unfinished_tool_call_replacer = RunnableCallable(
        lambda maybe_cleaned_output: TOOLCALL_FAILED_RESPONSE
        if maybe_cleaned_output.strip().startswith("<tool_call>")
        and "</tool_call>" not in maybe_cleaned_output
        else maybe_cleaned_output,
        name="insert_error_if_tool_calling_failed",
    )

    def execute_worker_agent(state: DetectorAgentState, config: RunnableConfig):
        task = state.plan[0][1]
        task_formatted = textwrap.dedent(f"""\
            You are a specialized analysis agent responsible for executing a specific step in a security analysis workflow of a Python package.

            ## Source Code Under Analysis

            **Package Name:** {state.package_name}

            {state.source_codes_str}

            ## Entire Analysis Plan from Supervisor

            {state.plan_str}

            ## Your Current Task

            You are tasked to complete **Step {1}:** {task}

            ## Instructions

            Execute the task described above and generate a concise report summarizing your findings. \
            This report will be sent back to the supervisor for further planning and decision-making.""")
        agent_response: str = (
            worker_agent
            | last_message_extractor
            | StrOutputParser()
            | reasoning_tokens_remover
            | unfinished_reasoning_replacer
            | unfinished_tool_call_replacer
        ).invoke(state.model_copy(update={"messages": [HumanMessage(task_formatted)]}))
        return {"past_steps": [(worker_agent.name, task, agent_response)]}

    return execute_worker_agent


def create_global_agents_graph(
    supervisor_llm: BaseChatModel,
    workers_llm: BaseChatModel,
    formatter_llm: BaseChatModel,
    name: str = "malware-analyst-team",
) -> CompiledStateGraph[DetectorAgentState, DetectorAgentState, DetectorAgentState]:
    subordinate_agents_and_tool_names: list[
        tuple[
            CompiledStateGraph[
                DetectorAgentState, DetectorAgentState, DetectorAgentState
            ],
            list[str],
        ]
    ] = init_worker_agents(model=workers_llm)

    graph = StateGraph(DetectorAgentState).add_node(
        SUPERVISOR_NAME,
        create_supervisor(
            supervisor_llm=supervisor_llm,
            formatter_llm=formatter_llm,
        ),
        destinations=tuple(s.get_name() for s, _ in subordinate_agents_and_tool_names),
    )
    # add all subordinate agents as nodes
    for s in [s for s, _ in subordinate_agents_and_tool_names]:
        graph = graph.add_node(s.get_name(), get_wrapped_worker_agent(worker_agent=s))
    # add edges
    graph = graph.add_edge(START, SUPERVISOR_NAME)
    for s in [s for s, _ in subordinate_agents_and_tool_names]:
        graph = graph.add_edge(s.get_name(), SUPERVISOR_NAME)

    return graph.compile(name=name)
