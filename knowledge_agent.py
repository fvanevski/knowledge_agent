# knowledge_agent.py

import os
import json
import logging
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai.chat_models import ChatOpenAI
from langgraph.graph import StateGraph, END
from sub_agents import (
    run_analyst, run_researcher, run_curator,
    run_auditor, run_fixer, run_advisor
)
from state import AgentState

async def get_mcp_tools():
    """Initializes the MCP client and fetches the available tools."""
    with open('mcp.json', 'r') as f:
        mcp_server_config = json.load(f)
    
    mcp_client = MultiServerMCPClient(mcp_server_config)
    tools = await mcp_client.get_tools()
    print(f"Successfully loaded {len(tools)} tools from MCP server.")
    return tools

def create_knowledge_agent_graph(task: str):
    """Creates the Knowledge Agent as a LangGraph StateGraph."""
    
    workflow = StateGraph(AgentState)

    # Add nodes for each sub-agent
    workflow.add_node("analyst", run_analyst)
    workflow.add_node("researcher", run_researcher)
    workflow.add_node("curator", run_curator)
    workflow.add_node("auditor", run_auditor)
    workflow.add_node("fixer", run_fixer)
    workflow.add_node("advisor", run_advisor)

    # Define the workflow based on the task
    if task == "maintenance":
        workflow.add_edge("analyst", "researcher")
        workflow.add_edge("researcher", "curator")
        workflow.add_edge("curator", "auditor")
        workflow.add_edge("auditor", "fixer")
        workflow.add_edge("fixer", "advisor")
        workflow.add_edge("advisor", END)
        workflow.set_entry_point("analyst")
    elif task == "analyze":
        workflow.set_entry_point("analyst")
        workflow.add_edge("analyst", END)
    elif task == "research":
        workflow.set_entry_point("researcher")
        workflow.add_edge("researcher", END)
    elif task == "curate":
        workflow.set_entry_point("curator")
        workflow.add_edge("curator", END)
    elif task == "audit":
        workflow.set_entry_point("auditor")
        workflow.add_edge("auditor", END)
    elif task == "fix":
        workflow.set_entry_point("fixer")
        workflow.add_edge("fixer", END)
    elif task == "advise":
        workflow.set_entry_point("advisor")
        workflow.add_edge("advisor", END)

    # Compile the graph
    app = workflow.compile()
    return app