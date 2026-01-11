import os

from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_tavily import TavilySearch
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from chase.agents.web_researcher.mytools import (
    fetch_content_at_url,
    fetch_package_info_from_pypi,
    inspect_domain_or_url_using_virustotal,
)
from chase.state import DetectorAgentState

# Create DuckDuckGo tool with cybersecurity-focused description
ddg_search = DuckDuckGoSearchResults(
    name="search_web_with_duckduckgo",
    description=(
        "CRITICAL tool to search the web for gathering threat intelligence and validating security findings. "
        "Use this to search for: malware signatures, domain reputation, IOC reports, "
        "security bulletins, and threat actor information. Input: specific security-focused search terms."
    ),
    num_results=5,
    output_format="json",
)


def init_web_researcher_agent(
    model: BaseChatModel,
) -> tuple[
    CompiledStateGraph[DetectorAgentState, DetectorAgentState, DetectorAgentState],
    list[str],
]:
    tools: list[BaseTool] = [
        fetch_content_at_url,
        fetch_package_info_from_pypi,
    ]
    match os.getenv("WEB_RESEARCHER_SEARCH_TOOL"):
        case "tavily":
            tools.append(
                TavilySearch(name="search_web_using_tavily", max_results=5),
            )
        case "duckduckgo":
            tools.append(ddg_search)
        case _:
            raise ValueError(
                "Environmental variable WEB_RESEARCHER_SEARCH_TOOL is not set or set to invalid value"
            )
    use_virustotal_tool = os.getenv("WEB_RESEARCHER_USE_VIRUSTOTAL_TOOL") == "true"
    if use_virustotal_tool:
        tools.append(inspect_domain_or_url_using_virustotal)

    prompt = (
        'You are "Web Researcher", a security OSINT specialist providing intelligence to a security analyst supervisor. '
        "Use tools strategically to gather information about web-related indicators, then provide concise findings.\n\n"
        f"## Available Tools:\n"
        f"• {tools[0].name}: Fetch content from URLs\n"
        f"• {tools[1].name}: Fetch PyPI package metadata (author, version, description)\n"
        f"• {tools[2].name}: Search web for security intelligence\n\n"
        f"{f'• {tools[3].name}: Analyze domains/URLs using VirusTotal threat intelligence\n' if use_virustotal_tool else ''}"
        "## Investigation Approach:\n"
        "1. **Identify what to investigate** from the input (URLs, domains, packages, IPs)\n"
        "2. **Use relevant tools** - avoid repeating identical queries\n"
        "3. **Gather complementary data** using different tools or search terms\n"
        "4. **Stop when you have sufficient evidence** or hit technical limitations\n\n"
        "## Tool Usage Guidelines:\n"
        f"{'- For domains: Use VirusTotal analysis and optionally fetch content if URL provided\n' if use_virustotal_tool else '- For domains: Use web search and fetch content if URL provided\n'}"
        f'- For PyPI packages: Use {tools[1].name} with package_version="latest" for latest info, or specific version like "2.28.0"\n'
        "- For packages: Search for reputation, known issues, or security reports\n"
        "- For general investigation: Search with specific relevant terms\n"
        "- If a tool fails or returns no results, try a different approach rather than repeating\n\n"
        "## Output Format\n"
        "**Key Findings:**\n"
        "- [Bullet point of relevant security insights]\n"
        "- [Specific indicators or notable information if discovered]\n"
        "- [Risk level assessment: Low/Medium/High with brief justification]\n\n"
        "Keep response under 200 words. Focus on actionable intelligence for the supervisor's next decision.\n\n"
        "## CRITICAL - What NOT to Include:\n"
        '- DO NOT suggest next steps (e.g., "Next step: ...", "Proceed with ...", "Recommend ...")\n'
        "- DO NOT make recommendations about what to do next\n"
        "- The supervisor will determine the next steps based on your findings\n"
        "- Your role is ONLY to report findings, not to guide the investigation direction"
    )

    return (
        create_react_agent(
            model=model,
            tools=tools,
            state_schema=DetectorAgentState,
            name="web_researcher",
            prompt=prompt,
        ),
        [t.name for t in tools],
    )
