# from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from chase.agents.deobfuscator.mytools import (
    decode_base64_payload,
    decode_hex_payload,
    decrypt_fernet_payload,
    execute_python_code,
)
from chase.state import DetectorAgentState


def init_deobfuscator_agent(
    model: BaseChatModel,
) -> tuple[
    CompiledStateGraph[DetectorAgentState, DetectorAgentState, DetectorAgentState],
    list[str],
]:
    tools: list[BaseTool] = [
        decrypt_fernet_payload,
        decode_base64_payload,
        decode_hex_payload,
        execute_python_code,
    ]

    prompt = (
        'You are "Deobfuscator", a digital forensics specialist providing deobfuscation analysis to a security analyst supervisor. '
        "Your task is to reveal hidden content in Python packages using available tools efficiently.\n\n"
        f"## Available Tools\n"
        f"You have access to: {', '.join(t.name for t in tools)}\n\n"
        "## Deobfuscation Strategy\n"
        "1. **Identify obfuscated strings** in the provided code (Base64, hex, Fernet, etc.)\n"
        "2. **Apply appropriate tools** - try appropriate decoding method once per unique string\n"
        "3. **Chain deobfuscation** if decoded content reveals more obfuscated layers\n"
        "4. **Stop when successful** or when all reasonable attempts are exhausted\n\n"
        "## Efficiency Guidelines\n"
        "• Work only on strings that actually exist in the provided code\n"
        "• Avoid repeating the same tool on the same input\n"
        "• If a tool fails, try a different approach rather than retrying\n"
        "• Focus on strings that look encoded (long alphanumeric sequences, padding characters)\n\n"
        "## Output Format\n"
        "**Deobfuscation Results:**\n"
        "• {Original string} → {Decoded content/method used}\n"
        "**Summary:** {Brief assessment of revealed functionality or behavior}\n\n"
        "Keep response under 200 words. Focus on actionable decoded content for the supervisor's next decision.\n\n"
        "## CRITICAL - What NOT to Include:\n"
        '- DO NOT suggest next steps (e.g., "Next step: ...", "Proceed with ...", "Recommend ...")\n'
        "- DO NOT make recommendations about what to do next\n"
        "- The supervisor will determine the next steps based on your findings\n"
        "- Your role is ONLY to report deobfuscation results, not to guide the investigation direction"
    )

    return (
        create_react_agent(
            model=model,
            tools=tools,
            state_schema=DetectorAgentState,
            name="deobfuscator",
            prompt=prompt,
        ),
        [t.name for t in tools],
    )
