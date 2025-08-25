# sub_agents.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
from langchain_core.messages import AIMessage
import json
import os
import re
from state import AgentState

@tool
def load_report(filename: str) -> str:
    """Loads the most recent report from a file in the state directory."""
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    filepath = f"state/{filename}"
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        status = f"[ERROR] No report found at {filepath}."
        print(status)
        logger.warning(status)
        return status
    with open(filepath, "r") as f:
        data = json.load(f)
    if "reports" in data and isinstance(data["reports"], list) and data["reports"]:
        status = f"Loaded report from {filepath}: {json.dumps(data['reports'][-1], indent=2)}"
        print(status)
        logger.info(status)
        return json.dumps(data["reports"][-1])
    else:
        status = "[ERROR] No reports found in the file."
        print(status)
        logger.error(status)
        return status

@tool
def human_approval(plan: str) -> str:
    """
    Asks for human approval for a given plan.
    The plan is a string that describes the actions to be taken.
    Returns 'approved' or 'denied'.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    status = f"PROPOSED PLAN:\n{plan}"
    print(f"\n{status}")
    logger.info(f"{status}")
    response = input("Do you approve this plan? (y/n): ").lower()
    if response == 'y':
        status = "Approved."
        print(status)
        logger.info(status)
        return "approved"
    status = "Denied."
    print(status)
    logger.info(status)
    return "denied"

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
        report_json = _extract_and_clean_json_fixer(final_message_from_agent.content)
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
