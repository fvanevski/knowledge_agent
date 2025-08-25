# curator.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
from langchain_core.messages import AIMessage
import json
import os
import re
from state import AgentState

@tool
def initialize_curator(timestamp: str) -> dict:
    """
    Initializes the curator's report.
    This tool should be called once at the beginning of the curator's workflow.
    It reads the researcher's report, creates the initial structure for the curator_report.json,
    and returns the report_id and the list of searches to be populated into the AgentState.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    status = f"Initialize curator tool called, attempting to load researcher_report.json ---"
    print(status)
    logger.info(status)

    try:
        researcher_report_str = load_report('researcher_report.json')
    except Exception as e:
        status = f"[ERROR] Error loading researcher report: {e}"
        logger.error(status)
        print(status)
        raise ToolException(status)

    if "No report found" in researcher_report_str:
        status = f"[ERROR] Researcher report not found."
        logger.error(status)
        print(status)
        raise ToolException(status)

    status = f"Loaded researcher report:\n{researcher_report_str}"
    print(status)
    logger.info(status)

    researcher_report = json.loads(researcher_report_str)

    report_id = f"cur_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
    status = f"Generated curator report ID: {report_id}"
    print(status)
    logger.info(status)

    searches_todo = []
    for gap in researcher_report.get("gaps", []):
        for search in gap.get("searches", []):
            searches_todo.append({
                "search_id": search["search_id"],
                "rationale": search["rationale"],
                "parameters": search["parameters"],
                "results": search["results"]
            })
    status = f"Compiled {len(searches_todo)} searches to be curated."
    print(f"[INFO] {status}")
    logger.info(status)

    new_report = {
        "report_id": report_id,
        "searches": searches_todo
    }

    status = f"Initialized new researcher report:\n{json.dumps(new_report, indent=2)}"
    print(status)
    logger.info(status)

    filepath = "state/researcher_report.json"

    status = f"Loading researcher reports into memory from {filepath}"
    print(status)
    logger.info(status)
    try:
        with open(filepath, "r") as f:
            file_data = json.load(f)
    except Exception as e:
        status = f"[ERROR] Error reading {filepath}: {e}"
        logger.error(status)
        print(status)
        raise ToolException(status)

    file_data = {"reports": []}
    status = f"Loading researcher reports into data structure"
    print(status)
    logger.info(status)
    try:
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            with open(filepath, "r") as f:
                file_data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading {filepath} into data structure: {e}")
        print(f"Error loading {filepath} into data structure: {e}")
        raise ToolException(f"Error loading {filepath} into data structure: {e}")

    status = f"Loaded researcher reports from {filepath} into data structure"
    print(status)
    logger.info(status)

    status = f"Appending new report to researcher reports data structure"
    print(status)
    logger.info(status)

    try:
        file_data["reports"].append(new_report)
        status = f"Successfully appended new report to researcher reports data structure"
        print(status)
        logger.info(status)
    except Exception as e:
        status = f"[ERROR] Error appending new report to researcher reports data structure: {e}"
        logger.error(status)
        print(status)
        raise ToolException(status)

    status = f"Writing updated researcher reports to {filepath}"
    print(status)
    logger.info(status)
    try:
        with open(filepath, "w") as f:
            json.dump(file_data, f, indent=2)
        status = f"Successfully wrote updated researcher reports to {filepath}"
        print(status)
        logger.info(status)
    except Exception as e:
        status = f"[ERROR] Error writing updated researcher reports to {filepath}: {e}"
        logger.error(status)
        print(status)
        raise ToolException(status)

    return {
        "researcher_report_id": report_id,
        "researcher_gaps_todo": gaps_to_do
    }

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

async def curator_agent_node(state: AgentState):
    logger = state['logger']

    if not state.get("curator_report_id"):
        status = f"--- Curator state not initialized. Calling initialize_curator. ---"
        print(status)
        logger.info(status)
        try:
            init_result = initialize_curator(state['timestamp'])
            if isinstance(init_result, dict):
                state["curator_report_id"] = init_result.get("curator_report_id")
                state["curator_searches_todo"] = init_result.get("curator_searches_todo")
                state["curator_current_search"] = {}
                state["curator_urls_to_ingest"] = []
                status = f"--- Initialized curator state: {init_result} ---"
                print(f"[INFO] {status}")
                logger.info(status)
        except Exception as e:
            status = f"Failed to initialize curator report: {e}"
            print(f"[ERROR] {status}")
            logger.error(status, exc_info=True)
            return {"status": status}

    # Create the specialized agent for search ranking
    search_ranker_prompt = ChatPromptTemplate.from_template(open("prompts/search_ranker_prompt.txt", "r").read())
    search_ranker_tools = [t for t in state['mcp_tools'] if t.name in ["google_search", "fetch"]]
    status = f"Attempting to invoke search ranker agent executor with tools: {search_ranker_tools}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        agent_runnable = create_openai_tools_agent(state['model'], search_ranker_tools, search_ranker_prompt)
        executor = AgentExecutor(agent=agent_runnable, tools=search_ranker_tools, verbose=True)
    except Exception as e:
        status = f"Failed to create search ranker agent executor: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        return {"status": status}

    # Main control loop for search ranking


    ingester_prompt = ChatPromptTemplate.from_template(open("prompts/ingester_prompt.txt", "r").read())
    ingester_tools = [t for t in state['mcp_tools'] if t.name in ["fetch", "documents_upload_file", "documents_upload_files", "documents_insert_text", "documents_pipeline_status"]]

    status = f"Attempting to invoke curator agent executor with tools: {[t.name for t in curator_tools]}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        agent_runnable = create_openai_tools_agent(state['model'], curator_tools, prompt)
        executor = AgentExecutor(agent=agent_runnable, tools=curator_tools, verbose=True)
    except Exception as e:
        status = f"Failed to create agent runnable: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        return {"status": status}

    status = f"Attempting to run agent executor with input: {state['messages'][0].content}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        # The executor handles the entire loop of tool calls and reasoning.
        result = await executor.ainvoke({
            "input": state['messages'][0].content,
            "curator_report_id": state.get("curator_report_id", "")
        })
        final_output = result.get('output', '')
    except Exception as e:
        status = f"AgentExecutor failed: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        final_output = f"Error in Curator Agent: {e}"

    # The node returns a single AIMessage with the final report.
    # This message is then passed to the next node in the graph.
    status = f"Successfully generated curator report: {final_output}"
    print(f"[INFO] {status}")
    logger.info(status)
    return {"messages": state['messages'] + [AIMessage(content=final_output)]}


def save_curator_report_node(state: AgentState):
    """Saves the final report from the last AI message."""
    logger = state['logger']
    final_message_from_agent = state['messages'][-1]

    status = f"--- Saving Curator Report ---\n{final_message_from_agent.content}"
    print(f"[INFO] {status}")
    logger.info(status)

    try:
        report_json = _extract_and_clean_json_curator(final_message_from_agent.content)
        if 'report_id' not in report_json:
            report_json['report_id'] = state.get('curator_report_id', 'unknown_id')
        save_curator_report.invoke({"curator_report": json.dumps(report_json)})
        status = f"Successfully saved curator report with ID {report_json.get('report_id')}"
        print(f"[INFO] {status}")
        logger.info(status)
    except (ValueError, KeyError) as e:
        status = f"Error processing or saving curator report: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)

    return {"messages": state['messages'] + [AIMessage(content=status)]}
