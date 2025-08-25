# sub_agents/analyst.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from state import AgentState
from db_utils import save_analyst_report, extract_and_clean_json

async def analyst_agent_node(state: AgentState):
    """Runs the analyst agent and returns its raw output and the new report ID."""
    logger = state['logger']
    timestamp = state['timestamp']
    report_id = f"ana_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
    status = f"Initialized analyst report with ID: {report_id}"
    print(f"[INFO] {status}")
    logger.info(status)

    with open("prompts/analyst_prompt.txt", "r") as f:
        analyst_prompt_template = f.read()
        
    analyst_prompt = ChatPromptTemplate.from_template(analyst_prompt_template)    
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
            "analyst_report_id": report_id
        })
        raw_report = analyst_result.get('output', '')
        status = f"Analyst agent completed.\nRaw output: {raw_report}"
        print(f"[INFO] {status}")
        logger.info(status)

    except Exception as e:
        status = f"Analyst agent failed: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        raw_report = f"Error in Analyst Agent: {e}"

    return {
        "analyst_report_id": report_id,
        "analyst_report": raw_report,
        "status": status
    }

def save_analyst_report_node(state: AgentState):
    """Saves the final report and updates the main status field."""
    logger = state['logger']
    raw_report_content = state.get("analyst_report")

    report_id = state.get("analyst_report_id")
    status = f"--- Saving Analyst Report: {report_id} ---"
    print(f"[INFO] {status}")
    logger.info(status)

    try:
        report_json = extract_and_clean_json(raw_report_content)
        if 'report_id' not in report_json:
            report_json['report_id'] = report_id
        
        save_analyst_report(report_json)
        status = f"Successfully saved analyst report with ID {report_json.get('report_id')}"
        print(f"[INFO] {status}")
        logger.info(status)
    except (ValueError, KeyError) as e:
        status = f"Error processing or saving analyst report: {e}"
        print(f"[ERROR] {status}")
        logger.error(status)
    
    return {"status": status}
