# researcher.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
from langchain_core.messages import AIMessage
import json
import os
import re
from state import AgentState

def _extract_and_clean_json_researcher(llm_output: str) -> dict:
    """
    Extracts, cleans, and reconstructs a valid JSON object from the LLM's output.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')
    
    status = f"Extracting and cleaning JSON from researcher LLM output"
    print(status)
    logger.info(status)
    try:
        # First, try to parse the whole output as-is
        return json.loads(llm_output)
    except json.JSONDecodeError:
        # If that fails, try to find all search objects and reconstruct the JSON
        status = f"Initial JSON parsing failed, attempting to reconstruct JSON from partial outputs."
        print(status)
        logger.info(status)
        try:
            # This regex will find all dictionaries that look like search objects
            searches = re.findall(r'\{\s*"rationale":.*?"results":.*?\}\s*\}', llm_output, re.DOTALL)
            status = f"Found {len(searches)} search objects in the output."
            print(status)
            logger.info(status)

            if not searches:
                # If no search objects are found, return a valid JSON with an empty list
                status = f"No search objects found in the output, returning empty searches list."
                print(status)
                logger.info(status)
                return {"searches": []}

            # Reconstruct the JSON object
            status = f"Reconstructing JSON from found search objects."
            print(status)
            logger.info(status)
            reconstructed_json_string = f'{{"searches": [{", ".join(searches)}]}}'
            
            status = f"Reconstructed JSON: {reconstructed_json_string}"
            print(status)
            logger.info(status)
            return json.loads(reconstructed_json_string)

        except (json.JSONDecodeError, ValueError) as e:
            status = f"Failed to parse or reconstruct JSON: {e}"
            print(status)
            logger.error(status)
            raise ValueError(status)

@tool
def initialize_researcher(timestamp: str) -> dict:
    """
    Initializes the researcher's report.
    This tool should be called once at the beginning of the researcher's workflow.
    It reads the analyst's report, creates the initial structure for the researcher_report.json,
    and returns the report_id and the list of gaps to be populated into the AgentState.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    status = f"Initializing researcher report tool called, attempting to load analyst_report.json ---"
    print(status)
    logger.info(status)

    try:
        analyst_report_str = load_report('analyst_report.json')
    except Exception as e:
        status = f"[ERROR] Error loading analyst report: {e}"
        logger.error(status)
        print(status)
        raise ToolException(status)

    if "No report found" in analyst_report_str:
        status = f"[ERROR] Analyst report not found."
        logger.error(status)
        print(status)
        raise ToolException(status)

    status = f"Loaded analyst report:\n{analyst_report_str}"
    print(status)
    logger.info(status)

    analyst_report = json.loads(analyst_report_str)
    
    report_id = f"res_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
    status = f"Generated researcher report ID: {report_id}"
    print(status)
    logger.info(status)

    gaps_to_do = [
        {"gap_id": gap["gap_id"], "description": gap["description"], "research_topic": gap["research_topic"], "searches": []}
        for gap in analyst_report.get("identified_gaps", [])
    ]
    
    new_report = {
        "report_id": report_id,
        "gaps": gaps_to_do
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
def update_researcher_report(report_id: str, current_gap: dict, search_results: list) -> str:
    """
    Updates the researcher's report with the results of a single search.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    status = f"Updating researcher report {report_id} with new gap data."
    print(status)
    logger.info(status)

    filepath = "state/researcher_report.json"
    try:
        with open(filepath, "r") as f:
            file_data = json.load(f)
    except Exception as e:
        status = f"[ERROR] Could not read or parse {filepath}. Error: {str(e)}"
        logger.error(status)
        print(status)
        raise ToolException(status)

    # Find the report index
    report_list = file_data.get("reports", [])
    report_index = next((i for i, r in enumerate(report_list) if r.get("report_id") == report_id), None)
    if report_index is None:
        status = f"[ERROR] Report with ID {report_id} not found."
        print(status)
        logger.error(status)
        raise ToolException(status)

    # Find the gap index
    gap_list = report_list[report_index].get("gaps", [])
    gap_id = current_gap.get("gap_id")
    gap_index = next((i for i, g in enumerate(gap_list) if g.get("gap_id") == gap_id), None)
    if gap_index is None:
        status = f"[ERROR] Gap with ID {gap_id} not found in report {report_id}."
        print(status)
        logger.error(status)
        raise ToolException(status)

    # Update the gap's searches

    status = f"Updating {report_id}/{gap_id} in the data structure with new search results."
    print(status)
    logger.info(status)
    try:
        file_data['reports'][report_index]['gaps'][gap_index]['searches'] = search_results
    except Exception as e:
        status = f"[ERROR] Error updating {report_id}/{gap_id} in the data structure: {e}"
        logger.error(status)
        print(status)
        raise ToolException(status)
    status = f"Inserted {len(search_results)} search results to {report_id}/{gap_id} in the data structure."
    print(status)
    logger.info(status)

    # Write back to file
    try:
        with open(filepath, "w") as f:
            json.dump(file_data, f, indent=2)
        status = f"Successfully wrote updated data for report {report_id} to {filepath}"
        logger.info(status)
        print(status)
        return status
    except Exception as e:
        status = f"[ERROR] Failed to write to {filepath}: {e}"
        logger.error(status)
        print(status)
        raise ToolException(status)

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

async def researcher_agent_node(state: AgentState):
    logger = state['logger']

    # One-time initialization of the report and state
    if not state.get("researcher_report_id"):
        status = f"--- Researcher state not initialized. Calling initialize_researcher directly. ---"
        print(status)
        logger.info(status)
        try:
            init_result = initialize_researcher(state['timestamp'])
            if isinstance(init_result, dict):
                state["researcher_report_id"] = init_result.get("researcher_report_id")
                state["researcher_gaps_todo"] = init_result.get("researcher_gaps_todo")
                state["researcher_gaps_complete"] = []
                status = f"--- Initialized researcher state: {init_result} ---"
                print(f"[INFO] {status}")
                logger.info(status)
        except Exception as e:
            status = f"Failed to initialize researcher state: {e}"
            print(f"[ERROR] {status}")
            logger.error(status)
            return {"status": status}

    # Create the specialized agent for performing searches
    searcher_prompt = ChatPromptTemplate.from_template(open("prompts/searcher_prompt.txt", "r").read())
    searcher_tools = [tool for tool in state['mcp_tools'] if tool.name == 'google_search']

    status = f"Attempting to invoke searcher agent executor with tools: {searcher_tools}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        agent_runnable = create_openai_tools_agent(state['model'], searcher_tools, searcher_prompt)
        executor = AgentExecutor(agent=agent_runnable, tools=searcher_tools, verbose=True)
    except Exception as e:
        status = f"Failed to create searcher agent executor: {e}"
        print(f"[ERROR] {status}")
        logger.error(status)
        return {"status": status}

    # Main control loop, managed by the node
    gaps_todo = state.get("researcher_gaps_todo", [])
    if isinstance(gaps_todo, list):
        for current_gap in gaps_todo:
            state['researcher_current_gap'] = current_gap
            gap_id = current_gap['gap_id']
            research_topic = current_gap['research_topic']

            status = f"Starting research for gap: {gap_id}, research topic: {research_topic}"
            print(f"[INFO] {status}")
            logger.info(status)

            try:
                # Invoke the specialized agent for just ONE gap
                searcher_result = await executor.ainvoke({"input": research_topic})
                status = f"Agent for gap {gap_id} finished. Raw output:\n{searcher_result.get('output')}"
                print(f"[INFO] {status}")
                logger.info(status)

                # The node, not the agent, saves the results
                try:
                    # Use the new helper function to extract and clean the JSON
                    json_output = _extract_and_clean_json_researcher(searcher_result.get("output", ""))
                    searches = json_output.get("searches", [])
                    status = f"Successfully parsed searches for gap {gap_id}: {searches}"
                    print(f"[INFO] {status}")
                    logger.info(status)

                except (ValueError, json.JSONDecodeError) as e:
                    status = f"Agent for gap {gap_id} returned invalid JSON: {searcher_result.get('output')}. Error: {e}"
                    print(f"[ERROR] {status}")
                    logger.error(status)
                    continue

                status = f"Preparing to update report for gap {gap_id} with {len(searches)} searches"
                print(f"[INFO] {status}")
                logger.info(status)
                try:
                    report_id = state['researcher_report_id']
                    current_gap = state['researcher_current_gap']
                    tool_input = {
                        "report_id": report_id,
                        "current_gap": current_gap,
                        "search_results": searches
                    }
                    result = update_researcher_report.invoke(tool_input)
                    status = f"Updated researcher report for gap {gap_id}: {result}"
                    print(f"[INFO] {status}")
                    logger.info(status)
                except Exception as e:
                    status = f"update_researcher_report failed for gap {gap_id}: {e}"
                    print(f"[ERROR] {status}")
                    logger.error(status, exc_info=True)
                    continue

                status = f"--- Successfully completed research and report writing for gap: {gap_id} ---"
                print(f"[INFO] {status}")
                logger.info(status)
                if "researcher_gaps_complete" not in state or state["researcher_gaps_complete"] is None:
                    state["researcher_gaps_complete"] = []
                state["researcher_gaps_complete"].append(gap_id)

            except Exception as e:
                status = f"An unexpected error occurred while processing gap {gap_id}: {e}"
                print(f"[ERROR] {status}")
                logger.error(status, exc_info=True)
                continue


    final_status = f"Successfully and incrementally completed researcher report with ID {state['researcher_report_id']} and wrote report to researcher_report.json."
    logger.info(final_status)
    return {"messages": state['messages'] + [AIMessage(content=final_status)]}
