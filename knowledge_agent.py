# knowledge_agent.py

import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai.chat_models import ChatOpenAI
from sub_agents import get_sub_agent_tools
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate
import logging

mcp_server_config = {
    "google_search": {
        "command": "uv",
        "args": ["run", "python", "google_search_mcp.py"],
        "cwd": "/workspace/mcp_servers/google_search_mcp",
        "transport": "stdio"
    },
    "lightrag": {
        "command": "uv",
        "args": ["run", "python", "lightrag_mcp.py"],
        "cwd": "/workspace/mcp_servers/lightrag_mcp",
        "transport": "stdio"
    },
    "fetch": {
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "transport": "stdio"
    },
    "file_tools": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace/knowledge_agent", "/workspace/LightRAG"],
        "transport": "stdio"
    },
    "deepwiki": {
        "url": "https://mcp.deepwiki.com/sse",
        "transport": "sse"
    }
}

async def get_mcp_tools():
    """Initializes the MCP client and fetches the available tools."""
    mcp_client = MultiServerMCPClient(mcp_server_config)
    tools = await mcp_client.get_tools()
    print(f"Successfully loaded {len(tools)} tools from MCP server.")
    return tools

from langchain_core.tools import tool

@tool
def human_approval(plan: str) -> str:
    """
    Asks for human approval for a given plan.
    The plan is a string that describes the actions to be taken.
    Returns 'approved' or 'denied'.
    """
    print(f"\nPROPOSED PLAN:\n{plan}")
    response = input("Do you approve this plan? (y/n): ").lower()
    if response == 'y':
        return "approved"
    return "denied"

def create_knowledge_agent(mcp_tools, logger: logging.Logger):

    """Creates the Knowledge Agent."""

    knowledge_agent_instructions = """Your task is to coordinate a group of sub-agents to maintain a lightrag knowledge base periodically. 
When you are called, you must follow this sequence precisely:
1.  Call the `analyst_agent` to identify knowledge gaps and stale information. The analyst will return a report on knowledge gaps.
2.  Take the report from the analyst and provide it as the input to the `researcher_agent`, instructing it to find new sources for those exact topics. The researcher will return a research report with a list of topics (preserving the full context of the knowledge gap) and associated URLs for each topic.
3.  Provide the research report from the researcher to the `curator_agent` and instruct it to review the URLs, select which ones to ingest, carry out the ingestion, and report task completion.
4.  Once the curator reports that ingestion is complete, you will call the `auditor_agent` to begin its review of the newly modified knowledge base. The auditor will return a report of data quality issues.
5.  Provide the auditor's report to the `fixer_agent` and instruct it to correct the issues. 
6.  After the fixer reports that its tasks are complete, you will call the `advisor_agent`, providing it with the reports from both the auditor and the fixer to analyze. The advisor will return its own report with recommendations for addressing the underlying causes of any identified issues (such as by modifying the ingestion prompts or LightRAG server configuration).
7.  Finally, based on the report from the advisor, you must provide a session summary to the user as your response, covering all the actions taken by the various sub-agents and any recommendations provided by the advisor."""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", knowledge_agent_instructions),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    model = ChatOpenAI(
        model="openai/gpt-oss-20b",
        base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:8002/v1"),
    )

    sub_agent_tools = get_sub_agent_tools(mcp_tools, model, logger)
    
    all_tools = sub_agent_tools + [human_approval]

    agent = create_openai_tools_agent(model, all_tools, prompt)
    
    agent_executor = AgentExecutor(agent=agent, tools=all_tools, verbose=True)

    return agent_executor
