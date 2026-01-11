import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from chase.agents.deobfuscator.deobfuscator import init_deobfuscator_agent
from chase.agents.web_researcher.web_researcher import init_web_researcher_agent
from chase.state import DetectorAgentState


def init_worker_agents(
    model: BaseChatModel,
) -> list[
    tuple[
        CompiledStateGraph[DetectorAgentState, DetectorAgentState, DetectorAgentState],
        list[str],
    ]
]:
    agents_and_tool_names = [
        init_web_researcher_agent(model=model),
        init_deobfuscator_agent(model=model),
    ]
    logging.info(f"loaded agents: {[a.name for a, _ in agents_and_tool_names]}")
    return agents_and_tool_names
