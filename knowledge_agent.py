# knowledge_agent.py

import os
import json
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai.chat_models import ChatOpenAI
from sub_agents import get_sub_agent_tools
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate
import logging

async def get_mcp_tools():
    """Initializes the MCP client and fetches the available tools."""
    with open('mcp.json', 'r') as f:
        mcp_server_config = json.load(f)
    
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

def create_knowledge_agent(mcp_tools, logger: logging.Logger, task: str):

    """Creates the Knowledge Agent."""

    knowledge_agent_instructions = {
        "maintenance": '''Your task is to coordinate a group of sub-agents to maintain a lightrag knowledge base periodically. You must handle errors gracefully.

When you are called, you must follow this sequence precisely:
1.  Call the `analyst_agent` to identify knowledge gaps and stale information. The analyst will save its report to `state/analyst_report.json` and return a status update.
2.  Call the `researcher_agent` to conduct research based on the latest analyst report. The researcher will save its report to `state/researcher_report.json` and return a status update.
3.  Use the `load_report` tool to load the latest report from `state/researcher_report.json`. Provide this report to the `curator_agent` and instruct it to review the URLs, select which ones to ingest, carry out the ingestion, and report task completion.
    *   **If the `curator_agent` returns an error,** analyze the error. If it is a single URL that is failing, remove that URL from the research report and call the `curator_agent` again with the modified report. If the `curator_agent` fails repeatedly, you should stop the workflow and report the error.
4.  Once the curator reports that ingestion is complete, you will call the `auditor_agent` to begin its review of the newly modified knowledge base. The auditor will return a report of data quality issues. Save this report to `auditor_report.json`.
5.  Provide the auditor's report to the `fixer_agent` and instruct it to correct the issues. Save the fixer's report to `fixer_report.json`.
6.  After the fixer reports that its tasks are complete, you will call the `advisor_agent`, providing it with the reports from both the auditor and the fixer to analyze. The advisor will return its own report with recommendations for addressing the underlying causes of any identified issues (such as by modifying the ingestion prompts or LightRAG server configuration).
7.  Finally, based on the report from the advisor, you must provide a session summary to the user as your response, covering all the actions taken by the various sub-agents and any recommendations provided by the advisor.''',
        "analyze": "Your task is to call the `analyst_agent` to identify knowledge gaps and stale information. The analyst will save its report to `state/analyst_report.json` and return a status update. Your final output should be the status update from the analyst agent.",
        "research": "Your task is to first check if the `analyst_report.json` file exists in the `state` directory. If it does not exist, you should inform the user that the analyst report is missing and the research workflow cannot proceed. If the file exists, you will then call the `researcher_agent` to conduct research based on the latest analyst report. The researcher will save its report to `state/researcher_report.json` and return a status update. Your final output should be the status update from the researcher agent.",
        "curate": "Your task is to call the `curator_agent` to carry out its workflow based on the research report. The curator will save its report to `state/curator_report.json` and return a status update.",
        "audit": "Your task is to call the `auditor_agent` to review the knowledge base for data quality issues. You should then save the auditor's report to a file named `auditor_report.json` in the `state` directory.",
        "fix": "Your task is to read the `auditor_report.json` file from the `state` directory, then call the `fixer_agent` with the auditor's report. You should then save the fixer's report to a file named `fixer_report.json` in the `state` directory.",
        "advise": "Your task is to read the `auditor_report.json` and `fixer_report.json` files from the `state` directory, then call the `advisor_agent` with the reports.",
    }
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", knowledge_agent_instructions[task]),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    model = ChatOpenAI(
        model="openai/gpt-oss-20b",
        base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:8002/v1"),
    )

    sub_agent_tools = get_sub_agent_tools(mcp_tools, model, logger, task)
    
    all_tools = sub_agent_tools + [human_approval]

    agent = create_openai_tools_agent(model, all_tools, prompt)

    agent_executor = AgentExecutor(agent=agent, tools=all_tools, handle_parsing_errors=True)

    return agent_executor
