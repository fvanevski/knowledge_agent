# advisor.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
from langchain_core.messages import AIMessage
import json
import os
import re
from state import AgentState
from tools import load_report, extract_and_clean_json

async def advisor_agent_node(state: AgentState):
    print("--- Running Advisor Agent ---")
    all_tools = state['mcp_tools']
    model = state['model']
    logger = state['logger']
    timestamp = state['timestamp']
    
    advisor_tools = [t for t in all_tools if t.name in ["list_allowed_directories", "list_directory", "search_files", "read_text_file"]] + [load_report]
    advisor_prompt = '''Your goal is to provide recommendations for systemic improvements.
1.  **Analyze Reports**: Load and analyze `auditor_report.json` and `fixer_report.json`.
2.  **Generate Recommendations**: Based on recurring patterns, generate actionable recommendations for ingestion prompts or server configuration.
3.  **Compile Report**: Save a final report with your top 3-5 suggestions to `advisor_report.json`.'''

    prompt = ChatPromptTemplate.from_template(advisor_prompt)
    agent_executor = create_openai_tools_agent(model, advisor_tools, prompt)
    
    task_input = "Your task is to provide recommendations based on the latest audit and fix reports. Begin now."

    result = await agent_executor.ainvoke({"input": task_input, "timestamp": timestamp})

    logger.info(f"Advisor Agent finished with output: {result['output']}")
    return {"messages": state['messages'] + [AIMessage(content=result['output'])]}

def save_advisor_report_node(state: AgentState):
    """Saves the final report from the last AI message."""
    logger = state['logger']
    final_message_from_agent = state['messages'][-1]

    status = f"--- Saving Advisor Report ---\n{final_message_from_agent.content}"
    print(f"[INFO] {status}")
    logger.info(status)

    try:
        report_json = extract_and_clean_json(final_message_from_agent.content)
        if 'report_id' not in report_json:
            report_json['report_id'] = state.get('advisor_report_id', 'unknown_id')
        save_advisor_report.invoke({"advisor_report": json.dumps(report_json)})
        status = f"Successfully saved advisor report with ID {report_json.get('report_id')}"
        print(f"[INFO] {status}")
        logger.info(status)
    except (ValueError, KeyError) as e:
        status = f"Error processing or saving advisor report: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)

    return {"messages": state['messages'] + [AIMessage(content=status)]}
