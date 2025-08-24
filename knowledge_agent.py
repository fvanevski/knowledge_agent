# knowledge_agent.py

import os
import json
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai.chat_models import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from sub_agents import (
    analyst_agent_node,
    save_analyst_report_node, # New node for saving the report
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

def should_continue(state: AgentState) -> str:
    """
    Conditional edge to determine whether to continue the agent loop or finish.
    """
    last_message = state['messages'][-1]
    if not last_message.tool_calls:
        return "end"
    return "continue"

def create_knowledge_agent_graph(task: str, all_tools: list):
    """Creates the Knowledge Agent as a LangGraph StateGraph."""
    
    workflow = StateGraph(AgentState)
    
    tool_node = ToolNode(all_tools)

    workflow.add_node("analyst", analyst_agent_node)
    workflow.add_node("save_analyst_report", save_analyst_report_node)
    workflow.add_node("researcher", run_researcher)
    workflow.add_node("tools", tool_node)

    workflow.add_node("curator", run_curator)
    workflow.add_node("auditor", run_auditor)
    workflow.add_node("fixer", run_fixer)
    workflow.add_node("advisor", run_advisor)


    # Define the workflow based on the task
    
    if task == "maintenance":
        # Full workflow with loops for each agent
        workflow.set_entry_point("analyst")

        # Add conditional edges for the analyst
        workflow.add_conditional_edges(
            "analyst",
            should_continue,
            {
                "continue": "tools",
                "end": "save_analyst_report"
            }
        )
        workflow.add_edge("tools", "analyst") # Loop back after tools
        workflow.add_edge("save_analyst_report", "researcher")

        # Add conditional edges for the researcher
        workflow.add_conditional_edges(
            "researcher",
            should_continue,
            {
                "continue": "tools",
                "end": "save_researcher_report"
            }
        )
        workflow.add_edge("tools", "researcher") # Loop back after tools
        workflow.add_edge("save_researcher_report", "curator")

        # Add conditional edges for the curator
        workflow.add_conditional_edges(
            "curator",
            should_continue,
            {
                "continue": "tools",
                "end": "save_curator_report"
            }
        )
        workflow.add_edge("tools", "curator") # Loop back after tools
        workflow.add_edge("save_curator_report", "auditor")

        # Add conditional edges for the auditor
        workflow.add_conditional_edges(
            "auditor",
            should_continue,
            {
                "continue": "tools",
                "end": "save_auditor_report"
            }
        )
        workflow.add_edge("tools", "auditor") # Loop back after tools
        workflow.add_edge("save_auditor_report", "fixer")

        # Add conditional edges for the fixer
        workflow.add_conditional_edges(
            "fixer",
            should_continue,
            {
                "continue": "tools",
                "end": "save_fixer_report"
            }
        )
        workflow.add_edge("tools", "fixer") # Loop back after tools
        workflow.add_edge("save_fixer_report", "advisor")

        # Add conditional edges for the advisor
        workflow.add_conditional_edges(
            "advisor",
            should_continue,
            {
                "continue": "tools",
                "end": "save_advisor_report"
            }
        )
        workflow.add_edge("tools", "advisor") # Loop back after tools

        workflow.add_edge("advisor", END)

    elif task == "analyze":
        workflow.set_entry_point("analyst")
        workflow.add_conditional_edges(
            "analyst",
            should_continue,
            {
                "continue": "tools",
                "end": "save_analyst_report"  # Route to save the report when done
            }
        )
        workflow.add_edge("tools", "analyst")
        workflow.add_edge("save_analyst_report", END) # End after saving
    
    elif task == "research":
        workflow.set_entry_point("researcher")
        workflow.add_conditional_edges(
            "researcher",
            should_continue,
            {
                "continue": "tools",
                "end": "save_researcher_report"
            }
        )
        workflow.add_edge("tools", "researcher")
        workflow.add_edge("save_researcher_report", END)
    
    elif task == "curate":
        workflow.set_entry_point("curator")
        workflow.add_conditional_edges(
            "curator",
            should_continue,
            {
                "continue": "tools",
                "end": "save_curator_report"
            }
        )
        workflow.add_edge("tools", "curator")
        workflow.add_edge("save_curator_report", END)
    
    elif task == "audit":
        workflow.set_entry_point("auditor")
        workflow.add_conditional_edges(
            "auditor",
            should_continue,
            {
                "continue": "tools",
                "end": "save_auditor_report"
            }
        )
        workflow.add_edge("tools", "auditor")
        workflow.add_edge("save_auditor_report", END)
    
    elif task == "fix":
        workflow.set_entry_point("fixer")
        workflow.add_conditional_edges(
            "fixer",
            should_continue,
            {
                "continue": "tools",
                "end": "save_fixer_report"
            }
        )
        workflow.add_edge("tools", "fixer")
        workflow.add_edge("save_fixer_report", END)
    
    elif task == "advise":
        workflow.set_entry_point("advisor")
        workflow.add_conditional_edges(
            "advisor",
            should_continue,
            {
                "continue": "tools",
                "end": "save_advisor_report"
            }
        )
        workflow.add_edge("tools", "advisor")
        workflow.add_edge("save_advisor_report", END)

    # Compile the graph
    app = workflow.compile()
    return app