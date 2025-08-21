# knowledge_agent.py

import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from deepagents import create_deep_agent
from langchain_openai.chat_models import ChatOpenAI
from dotenv import load_dotenv


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

def create_knowledge_agent(tools):
    """Creates the Knowledge Gardener deep agent."""

    # The main instructions for our agent
    knowledge_agent_instructions = """
    You are the "Knowledge Agent," an autonomous AI agent responsible for maintaining and curating a knowledge base.

    Your primary goal is to ensure the knowledge graph is accurate, up-to-date, and free of duplicate or poorly formatted information.

    Your workflow is as follows:
    1.  **Understand:** Start by understanding the current topics in the knowledge base.
    2.  **Expand:** Search for new, relevant information on the internet.
    3.  **Ingest:** Add your new findings to the knowledge base.
    4.  **Curate:** After ingestion, check for duplicate entities or normalization issues and correct them.
    5.  **Learn:** Based on the mistakes you correct, suggest improvements to the system's extraction prompts.

    Use your `write_todos` tool to plan and track your progress through these steps.
    """
    # Create the chat model for the agent
    # Initialize the chat model
    model = ChatOpenAI(
        model="openai/gpt-oss-20b",
        base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:8002/v1"),
    )

    # Create the deep agent instance
    agent = create_deep_agent(
        tools=tools,
        instructions=knowledge_agent_instructions,
        # We will define sub-agents later
        subagents=[], 
        model=model,
    ).with_config({"recursion_limit": 1000})

    return agent

# We will add a main execution block later in run.py