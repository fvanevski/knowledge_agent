# sub_agents.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
from langchain_core.messages import AIMessage
import json
import os
import re
from state import AgentState
from tools import load_report, human_approval, _extract_and_clean_json


async def fixer_agent_node(state: AgentState):
    print("--- Running Fixer Agent ---")
    all_tools = state['mcp_tools']
    model = state['model']
    logger = state['logger']
    timestamp = state['timestamp']
    
    fixer_tools = [t for t in all_tools if t.name in ["graph_update_entity", "documents_delete_entity", "graph_update_relation", "documents_delete_relation", "graph_entity_exists"]] + [load_report, human_approval]
    fixer_prompt = '''Your goal is to correct data quality issues.
1.  **Load Auditor's Report**: Load `auditor_report.json`.
2.  **Create a Plan**: Create a step-by-step plan to correct the issues.
3.  **Get Human Approval**: Use `human_approval` to get your plan approved by calling the tool with the plan.
4.  **Execute**: Execute the approved plan.
5.  **Save Report**: Save a report of your actions to `fixer_report.json`.'''

    prompt = ChatPromptTemplate.from_template(fixer_prompt)
    agent_executor = create_openai_tools_agent(model, fixer_tools, prompt)

    task_input = "Your task is to fix issues from the auditor's report. Begin now."

    result = await agent_executor.ainvoke({"input": task_input, "timestamp": timestamp})

    logger.info(f"Fixer Agent finished with output: {result['output']}")
    return {"messages": state['messages'] + [AIMessage(content=result['output'])]}

def save_fixer_report_node(state: AgentState):
    """Saves the final report from the last AI message."""
    logger = state['logger']
    final_message_from_agent = state['messages'][-1]

    status = f"--- Saving Fixer Report ---\n{final_message_from_agent.content}"
    print(f"[INFO] {status}")
    logger.info(status)

    try:
        report_json = _extract_and_clean_json(final_message_from_agent.content)
        if 'report_id' not in report_json:
            report_json['report_id'] = state.get('fixer_report_id', 'unknown_id')
        save_fixer_report.invoke({"fixer_report": json.dumps(report_json)})
        status = f"Successfully saved fixer report with ID {report_json.get('report_id')}"
        print(f"[INFO] {status}")
        logger.info(status)
    except (ValueError, KeyError) as e:
        status = f"Error processing or saving fixer report: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)

    return {"messages": state['messages'] + [AIMessage(content=status)]}
