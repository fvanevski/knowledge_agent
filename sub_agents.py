# sub_agents.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
from langchain_core.messages import AIMessage
import json
import os
import re
from state import AgentState

def _extract_and_clean_json_analyst(llm_output: str) -> dict:
    """
    Extracts and cleans a JSON object from the Analyst LLM's output.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    status = f"Extracting and cleaning JSON from analyst LLM output"
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
def save_analyst_report(analyst_report: str) -> dict:
    """
    Saves the analyst's report.
    This tool should be called once at the beginning of the analyst's workflow.
    It reads the analyst's report, creates the initial structure for the analyst_report.json,
    and returns the report_id and the list of gaps to be populated into the AgentState.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    status = f"Save analyst report tool called ---"
    print(status)
    logger.info(status)
    filepath = "state/analyst_report.json"
    file_data = {"reports": []}
    status = f"Loading existing analyst reports into memory from {filepath}"
    print(status)
    logger.info(status)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        with open(filepath, "r") as f:
            file_data = json.load(f)
    status = f"Appending new analyst report to data structure"
    print(status)
    logger.info(status)
    try:
        # Parse the incoming analyst_report string into a dictionary
        report_object = json.loads(analyst_report)
        file_data["reports"].append(report_object)
    except json.JSONDecodeError as e:
        status = f"Error parsing analyst report string: {e}"
        print(status)
        logger.error(status)
        raise ToolException(status)
    try:
        with open(filepath, "w") as f:
            json.dump(file_data, f, indent=2)
    except Exception as e:
        status = f"Error saving analyst report: {e}"
        print(status)
        logger.error(status)
        raise ToolException(status)

    status = f"Successfully wrote analyst report to {filepath}"
    print(status)
    logger.info(status)
    return {
        "analyst_status": status
    }

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

# --- Agent Node Functions ---

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

    status = f"Attempting to run agent executor with input: {state['messages'][0].content}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        # The executor handles the entire loop of tool calls and reasoning.
        analyst_result = await executor.ainvoke({
            "input": state['messages'][0].content,
            "analyst_report_id": state.get("analyst_report_id", "")
        })
        final_output = analyst_result.get('output', '')
    except Exception as e:
        status = f"AgentExecutor failed: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        final_output = f"Error in Analyst Agent: {e}"

    # The node returns a single AIMessage with the final report.
    # This message is then passed to the next node in the graph.
    status = f"Successfully generated analyst report: {final_output}"
    print(f"[INFO] {status}")
    logger.info(status)
    return {"messages": state['messages'] + [AIMessage(content=final_output)]}

def save_analyst_report_node(state: AgentState):
    """Saves the final report from the last AI message."""
    logger = state['logger']
    final_message_from_agent = state['messages'][-1]

    status = f"--- Saving Analyst Report ---\n{final_message_from_agent.content}"
    print(f"[INFO] {status}")
    logger.info(status)

    try:
        report_json = _extract_and_clean_json_analyst(final_message_from_agent.content)
        if 'report_id' not in report_json:
            report_json['report_id'] = state.get('analyst_report_id', 'unknown_id')
        save_analyst_report.invoke({"analyst_report": json.dumps(report_json)})
        status = f"Successfully saved analyst report with ID {report_json.get('report_id')}"
        print(f"[INFO] {status}")
        logger.info(status)
    except (ValueError, KeyError) as e:
        status = f"Error processing or saving analyst report: {e}"
        print(f"[ERROR] {status}")
        logger.error(status)
    
    return {"messages": state['messages'] + [AIMessage(content=status)]}

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
        report_json = _extract_and_clean_json_auditor(final_message_from_agent.content)
        if 'report_id' not in report_json:
            report_json['report_id'] = state.get('auditor_report_id', 'unknown_id')
        save_auditor_report.invoke({"auditor_report": json.dumps(report_json)})
        status = f"Successfully saved auditor report with ID {report_json.get('report_id')}"
        print(f"[INFO] {status}")
        logger.info(status)
    except (ValueError, KeyError) as e:
        status = f"Error processing or saving auditor report: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)

    return {"messages": state['messages'] + [AIMessage(content=status)]}

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
        report_json = _extract_and_clean_json_advisor(final_message_from_agent.content)
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
