# curator.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
from langchain_core.messages import AIMessage
import json
import os
import re
from state import AgentState

def _extract_and_clean_json_curator(llm_output: str) -> dict:
    """
    Extracts and cleans a JSON object from the Curator LLM's output.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    status = f"Extracting and cleaning JSON from curator LLM output"
    print(status)
    logger.info(status)
    # Use a regex to find the JSON blob
    match = re.search(r"\{.*\}", llm_output, re.DOTALL)
    status = f"Regex match for JSON: {match}"
    print(status)
    logger.info(status)
    if not match:
        status = f"No JSON object found in the output."
        print(status)
        logger.error(status)
        raise ValueError(status)

    json_string = match.group(0)
    status = f"Extracted JSON string: {json_string}"
    print(status)
    logger.info(status)

    # Try to parse the JSON
    status = f"Attempting to parse JSON: {json_string}"
    print(status)
    logger.info(status)
    try:
        parsed_json = json.loads(json_string)
        status = f"Successfully parsed JSON: {parsed_json}"
        print(status)
        logger.info(status)
        return parsed_json
    except json.JSONDecodeError as e:
        status = f"Failed to parse JSON: {e}"
        print(status)
        logger.error(status)
        raise ValueError(status)
    
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
        "urls_for_ingestion": [],
        "url_ingestion_status": [],
    }

    status = f"Initialized new curator report:\n{json.dumps(new_report, indent=2)}"
    print(status)
    logger.info(status)

    filepath = "state/curator_report.json"

    status = f"Loading curator reports into memory from {filepath}"
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
    status = f"Loading curator reports into data structure"
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

    status = f"Loaded curator reports from {filepath} into data structure"
    print(status)
    logger.info(status)

    status = f"Appending new report to curator reports data structure"
    print(status)
    logger.info(status)

    try:
        file_data["reports"].append(new_report)
        status = f"Successfully appended new report to curator reports data structure"
        print(status)
        logger.info(status)
    except Exception as e:
        status = f"[ERROR] Error appending new report to curator reports data structure: {e}"
        logger.error(status)
        print(status)
        raise ToolException(status)

    status = f"Writing updated curator reports to {filepath}"
    print(status)
    logger.info(status)
    try:
        with open(filepath, "w") as f:
            json.dump(file_data, f, indent=2)
        status = f"Successfully wrote updated curator reports to {filepath}"
        print(status)
        logger.info(status)
    except Exception as e:
        status = f"[ERROR] Error writing updated curator reports to {filepath}: {e}"
        logger.error(status)
        print(status)
        raise ToolException(status)

    return {
        "curator_report_id": report_id,
        "curator_searches_todo": searches_todo
    }

@tool
def update_curator_report(report_id: str, current_search: dict, job: str, results: list) -> str:
    """
    Updates the curator's report with the job results (urls_for_ingestion, or url_ingestion_status) for a single search.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    status = f"Updating curator report {report_id} with new results for: {job}.\n{results}"
    print(status)
    logger.info(status)

    filepath = "state/curator_report.json"
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

    # Update the job results

    status = f"Updating {report_id} in the data structure with the new results."
    print(status)
    logger.info(status)
    try:
        file_data['reports'][report_index][job].append(results)
    except Exception as e:
        status = f"[ERROR] Error updating {report_id} in the data structure: {e}"
        logger.error(status)
        print(status)
        raise ToolException(status)
    status = f"Inserted {len(results)} results to {report_id} in the data structure."
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

async def curator_agent_node(state: AgentState):
    logger = state['logger']

    # One-time initialization of the curator state
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
                state["curator_urls_for_ingestion"] = []
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
    task = "Rank the search results in `{search_results}` based on relevance to the rationale in `{search_rationale}`"
    searches_todo = state.get("curator_searches_todo", [])
    if isinstance(searches_todo, list) and searches_todo:
        for current_search in searches_todo:
            state["curator_current_search"] = current_search
            search_rationale = current_search['rationale']
            search_results = current_search['results']

            status = f"Processing search: {current_search['search_id']}"
            print(f"[INFO] {status}")
            logger.info(status)
            try:
                search_ranker_result = await executor.ainvoke({
                    "input": task,
                    "search_rationale": search_rationale,
                    "search_results": search_results
                })
                status = f"Curator agent for search {current_search['search_id']} completed. Raw output: {search_ranker_result.get('output', '')}"
                print(f"[INFO] {status}")
                logger.info(status)
                
                try:
                    json_output = _extract_and_clean_json_curator(search_ranker_result.get('output', ''))
                    ranked_urls = json_output.get("urls_for_ingestion", [])
                    state["curator_urls_for_ingestion"].extend(ranked_urls)
                    status = f"Successfully parsed ranked URLs for search {current_search['search_id']}: {ranked_urls}."
                    print(f"[INFO] {status}")
                    logger.info(status)
                except Exception as e:
                    status = f"Failed to parse ranked URLs for search {current_search['search_id']}: {e}"
                    print(f"[ERROR] {status}")
                    logger.error(status, exc_info=True)
                    continue

                status = f"Preparing to update report for search {current_search['search_id']} with {len(ranked_urls)} URLs."
                print(f"[INFO] {status}")
                logger.info(status)
                try:
                    tool_input = {
                        "curator_report_id": state.get("curator_report_id", ""),
                        "current_search": current_search,
                        "job": "urls_for_ingestion",
                        "results": ranked_urls
                    }
                    result = update_curator_report.invoke(tool_input)
                    status = f"Updated report for search {current_search['search_id']} with {len(ranked_urls)} URLs."
                    print(f"[INFO] {status}")
                    logger.info(status)
                except Exception as e:
                    status = f"Failed to update report for search {current_search['search_id']}: {e}"
                    print(f"[ERROR] {status}")
                    logger.error(status, exc_info=True)
                    continue

                status = f"Successfully updated report for search {current_search['search_id']} with {len(ranked_urls)} URLs."
                print(f"[INFO] {status}")
                logger.info(status)

            except Exception as e:
                status = f"AgentExecutor failed: {e}"
                print(f"[ERROR] {status}")
                logger.error(status, exc_info=True)
                continue

    status = f"Successfully completed ranking of all searches for report: {state.get('curator_report_id', 'unknown_id')}"
    print(f"[INFO] {status}")
    logger.info(status)

    # Create the specialized agent for url ingestion
    ingester_prompt = ChatPromptTemplate.from_template(open("prompts/ingester_prompt.txt", "r").read())
    ingester_tools = [t for t in state['mcp_tools'] if t.name in ["fetch", "documents_upload_file", "documents_upload_files", "documents_insert_text", "documents_pipeline_status"]]
    status = f"Attempting to invoke url ingestion agent executor with tools: {ingester_tools}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        agent_runnable = create_openai_tools_agent(state['model'], ingester_tools, ingester_prompt)
        executor = AgentExecutor(agent=agent_runnable, tools=ingester_tools, verbose=True)
    except Exception as e:
        status = f"Failed to create url ingestion agent executor: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        return {"status": status}

   # Main control for url ingestion

    task = "Ingest the URLs in `{urls_for_ingestion}` and return the ingestion status for each URL."
    status = f"Attempting to run agent executor for url ingestion"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        # The executor handles the entire loop of tool calls and reasoning.
        ingestion_result = await executor.ainvoke({
            "input": task,
            "urls_for_ingestion": state.get("curator_urls_for_ingestion", [])
        })
        status = f"Curator agent ingestion for report {state.get('curator_report_id', 'unknown_id')} completed.\nRaw output: {ingestion_result.get('output', '')}"
        print(f"[INFO] {status}")
        logger.info(status)
        
        try:
            json_output = _extract_and_clean_json_curator(ingestion_result.get('output', ''))
            url_ingestion_status = json_output.get("url_ingestion_status", [])
            status = f"Successfully parsed URL ingestion status: {url_ingestion_status}."
            print(f"[INFO] {status}")
            logger.info(status)
        except Exception as e:
            status = f"Failed to parse URL ingestion status: {e}"
            print(f"[ERROR] {status}")
            logger.error(status, exc_info=True)
            return {"status": status}

        status = f"Preparing to update report: {state.get('curator_report_id', 'unknown_id')} with ingestion status for {len(url_ingestion_status)} URLs."
        print(f"[INFO] {status}")
        logger.info(status)
        try:
            tool_input = {
                "curator_report_id": state.get("curator_report_id", ""),
                "current_search": current_search,
                "job": "url_ingestion_status",
                "results": url_ingestion_status
            }
            ingestion_result = update_curator_report.invoke(tool_input)
            status = f"Updated report {state.get('curator_report_id', 'unknown_id')} with ingestions status for {len(url_ingestion_status)} URLs."
            print(f"[INFO] {status}")
            logger.info(status)
        except Exception as e:
            status = f"Failed to update report {state.get('curator_report_id', 'unknown_id')}: {e}"
            print(f"[ERROR] {status}")
            logger.error(status, exc_info=True)
            return {"status": status}

        status = f"Successfully updated report {state.get('curator_report_id', 'unknown_id')} with {len(url_ingestion_status)} URLs."
        print(f"[INFO] {status}")
        logger.info(status)
    except Exception as e:
        status = f"Curator agent failed to run ingestion of ranked URLs: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        return {"status": status}

    # The node returns a single AIMessage with the final report.
    # This message is then passed to the next node in the graph.
    status = f"Curator successfully ranked and ingested URLs, generating curator report summary written to file `state/curator_report.json`"
    print(f"[INFO] {status}")
    logger.info(status)
    return {"messages": state['messages'] + [AIMessage(content=status)]}
