# knowledge_agent.py

import os
import json
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, END
from sub_agents import (
    analyst_agent_node,
    save_analyst_report_node,
    run_researcher, run_curator,
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

def create_knowledge_agent_graph(task: str, all_tools: list):
    """Creates the Knowledge Agent as a LangGraph StateGraph."""
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("analyst", analyst_agent_node)
    workflow.add_node("save_analyst_report", save_analyst_report_node)
    workflow.add_node("researcher", run_researcher)
    workflow.add_node("curator", run_curator)
    workflow.add_node("auditor", run_auditor)
    workflow.add_node("fixer", run_fixer)
    workflow.add_node("advisor", run_advisor)


    # Define the workflow based on the task
    
    if task == "maintenance":
        # Full workflow with loops for each agent
        workflow.set_entry_point("analyst")
        workflow.add_edge("analyst", "save_analyst_report")
        workflow.add_edge("save_analyst_report", "researcher")
        workflow.add_edge("researcher", "save_researcher_report")
        workflow.add_edge("save_researcher_report", "curator")
        workflow.add_edge("curator", "save_curator_report")
        workflow.add_edge("save_curator_report", "auditor")
        workflow.add_edge("auditor", "save_auditor_report")
        workflow.add_edge("save_auditor_report", "fixer")
        workflow.add_edge("fixer", "save_fixer_report")
        workflow.add_edge("save_fixer_report", "advisor")
        workflow.add_edge("advisor", "save_advisor_report")
        workflow.add_edge("save_advisor_report", END)

    elif task == "analyze":
        workflow.set_entry_point("analyst")
        workflow.add_edge("analyst", "save_analyst_report")
        workflow.add_edge("save_analyst_report", END)
    
    elif task == "research":
        workflow.set_entry_point("researcher")
        workflow.add_edge("researcher", "save_researcher_report")
        workflow.add_edge("save_researcher_report", END)
    
    elif task == "curate":
        workflow.set_entry_point("curator")
        workflow.add_edge("curator", "save_curator_report")
        workflow.add_edge("save_curator_report", END)
    
    elif task == "audit":
        workflow.set_entry_point("auditor")
        workflow.add_edge("auditor", "save_auditor_report")
        workflow.add_edge("save_auditor_report", END)
    
    elif task == "fix":
        workflow.set_entry_point("fixer")
        workflow.add_edge("fixer", "save_fixer_report")
        workflow.add_edge("save_fixer_report", END)
    
    elif task == "advise":
        workflow.set_entry_point("advisor")
        workflow.add_edge("advisor", "save_advisor_report")
        workflow.add_edge("save_advisor_report", END)

    # Compile the graph
    app = workflow.compile()
    return app