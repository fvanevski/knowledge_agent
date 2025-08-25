# auditor.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
from langchain_core.messages import AIMessage
import json
import os
import re
from state import AgentState
from tools import load_report, extract_and_clean_json

async def auditor_agent_node(state: AgentState):
    print("--- Running Auditor Agent ---")
    all_tools = state['mcp_tools']
    model = state['model']
    logger = state['logger']
    timestamp = state['timestamp']
    
    auditor_tools = [t for t in all_tools if t.name in ["graphs_get", "query"]]
    auditor_prompt = '''Your goal is to review the LightRAG knowledge base for data quality issues.
1.  **Identify issues**: Scan the graph for duplicates, irregular normalization, etc.
2.  **Generate Report**: Create a report of your findings.
3.  **Save Report**: Use `save_report` to save the findings to `auditor_report.json`.'''

    prompt = ChatPromptTemplate.from_template(auditor_prompt)
    agent_executor = create_openai_tools_agent(model, auditor_tools, prompt)

    task_input = "Your task is to audit the knowledge base. Begin now."

    result = await agent_executor.ainvoke({"input": task_input, "timestamp": timestamp})
    
    logger.info(f"Auditor Agent finished with output: {result['output']}")
    return {"messages": state['messages'] + [AIMessage(content=result['output'])]}

def save_auditor_report_node(state: AgentState):
    """Saves the final report from the last AI message."""
    logger = state['logger']
    final_message_from_agent = state['messages'][-1]

    status = f"--- Saving Auditor Report ---\n{final_message_from_agent.content}"
    print(f"[INFO] {status}")
    logger.info(status)

    try:
        report_json = extract_and_clean_json(final_message_from_agent.content)
        if 'report_id' not in report_json:
            report_json['report_id'] = state.get('auditor_report_id', 'unknown_id')
        save_auditor_report({"auditor_report": json.dumps(report_json)})
        status = f"Successfully saved auditor report with ID {report_json.get('report_id')}"
        print(f"[INFO] {status}")
        logger.info(status)
    except (ValueError, KeyError) as e:
        status = f"Error processing or saving auditor report: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)

    return {"messages": state['messages'] + [AIMessage(content=status)]}
