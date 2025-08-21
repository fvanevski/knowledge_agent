# knowledge_agent.py

import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from deepagents import create_deep_agent
from langchain_openai.chat_models import ChatOpenAI
from dotenv import load_dotenv
from sub_agents import get_sub_agents


# Load environment variables from .env file
load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")

mcp_server_config = {
    "google_search": {
        "command": "uv",
        "args": ["run", "--with", "requests,python-dotenv,pydantic,mcp", "--", "python3", "/workspace/mcp_servers/google_search_mcp/google_search_mcp.py"],
        "env": {
            "GOOGLE_API_KEY": GOOGLE_API_KEY,
            "GOOGLE_CSE_ID": GOOGLE_CSE_ID
        },
        "transport": "stdio"
    },
    "lightrag": {
        "command": "uv",
        "args": [
            "run",
            "--with",
            "httpx,python-dotenv,pydantic,mcp,pyyaml",
            "--",
            "python3",
            "/workspace/mcp_servers/lightrag_mcp/lightrag_mcp.py"
        ],
        "transport": "stdio"
    },
    "fetch": {
        "command": "uvx",
        "args": [
            "mcp-server-fetch"
        ],
        "transport": "stdio"
    },
    "file_tools": {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            "/workspace/models/filesystem"
        ],
        "transport": "stdio"
    }
}

async def get_mcp_tools():
    """Initializes the MCP client and fetches the available tools."""
    # This assumes your lightrag_mcp server is configured in the standard MCP way
    # We will need to create a simple mcp-config.json for this to work.

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

def create_knowledge_agent(tools):
    """Creates the Knowledge Gardener deep agent."""

    # The main instructions for our agent
    knowledge_agent_instructions = """your task is to coordinate a group of sub-agents to maintain a lightrag knowledge base periodically. when you are called, you should first initiate an analyst sub-agent to identify knowledge gaps and stale information in the knowledge base. based on the response from the analyst, you should call a research sub-agent to search the internet for new, relevant sources. based on the response from the researcher, you should call a curator sub-agent to review the new sources and decide what to ingest. once the curator returns the ingestion pipeline status as commplete you should call an auditor sub-agent to review the newly modified knowledge base to identify data quality issues. based on the response from the auditor, you should call a fixer sub-agent to correct any data quality issues identified. once the fixer returns its task status as complete you should call an advisor sub-agent to provide recommendations for systemic improvements. based on the response from the advisor, you should provide a session summary to the user as your response, covering all the actions taken by the various sub-agents and any recommendations provided by the advisor."""
    # Create the chat model for the agent
    # Initialize the chat model
    model = ChatOpenAI(
        model="openai/gpt-oss-20b",
        base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:8002/v1"),
    )

    # Get the sub-agents
    sub_agents = get_sub_agents(model)

    # Add the human approval tool to the list of tools
    tools.append(human_approval)

    # Create the deep agent instance
    agent = create_deep_agent(
        tools=tools,
        instructions=knowledge_agent_instructions,
        subagents=sub_agents, 
        model=model,
    ).with_config({"recursion_limit": 1000})

    return agent


# We will add a main execution block later in run.py
