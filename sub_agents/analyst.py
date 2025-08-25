# analyst.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from state import AgentState
from db_utils import save_analyst_report, extract_and_clean_json

async def analyst_agent_node(state: AgentState):
    """This node encapsulates the entire agent execution loop."""
    logger = state['logger']
    
    if not state.get("analyst_report_id"):
        timestamp = state['timestamp']
        report_id = f"ana_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
        state["analyst_report_id"] = report_id
        status = f"Initialized analyst report with ID: {report_id}"
        print(f"[INFO] {status}")
        logger.info(status)

    analyst_prompt = ChatPromptTemplate.from_template(open("prompts/analyst_prompt.txt", "r").read())    
    analyst_tools = [t for t in state['mcp_tools'] if t.name in ["query", "graphs_get", "graph_labels", "google_search", "fetch"]]

    status = f"Attempting to invoke analyst agent executor with tools: {analyst_tools}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        agent_runnable = create_openai_tools_agent(state['model'], analyst_tools, analyst_prompt)
        executor = AgentExecutor(agent=agent_runnable, tools=analyst_tools, verbose=True)
    except Exception as e:
        status = f"Failed to create agent executor: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        return {"status": status}


    task = state['messages'][0].content
    status = f"Attempting to run agent executor with input: {task}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        analyst_result = await executor.ainvoke({
            "input": task,
            "analyst_report_id": state.get("analyst_report_id", "")
        })
        raw_report = analyst_result.get("output", "")
        status = f"Analyst agent completed.\nRaw output: {state['analyst_report']}"
        print(f"[INFO] {status}")
        logger.info(status)
        state['status'] = f"Successfully generated analyst report: {state['analyst_report_id']}"

    except Exception as e:
        status = f"Analyst agent failed: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        state['status'] = status

    return {"analyst_report": raw_report}

def save_analyst_report_node(state: AgentState):
    """Saves the final report from the last AI message."""
    logger = state['logger']
    raw_report_content = state.get("analyst_report")

    status = f"--- Saving Analyst Report ---"
    print(f"[INFO] {status}")
    logger.info(status)

    try:
        report_json = extract_and_clean_json(raw_report_content)
        if 'report_id' not in report_json:
            report_json['report_id'] = state.get('analyst_report_id', 'unknown_id')
        save_analyst_report(report_json)
        status = f"Successfully saved analyst report with ID {report_json.get('report_id')}"
        print(f"[INFO] {status}")
        logger.info(status)
    except (ValueError, KeyError) as e:
        status = f"Error processing or saving analyst report: {e}"
        print(f"[ERROR] {status}")
        logger.error(status)
    
    return {"status": status}
