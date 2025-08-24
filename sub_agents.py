# sub_agents.py
from langchain_openai.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
import json
import os
import re
from state import AgentState

# --- Start of new helper function ---
def _extract_and_clean_json(llm_output: str) -> dict:
    """
    Extracts, cleans, and reconstructs a valid JSON object from the LLM's output.
    """
    try:
        # First, try to parse the whole output as-is
        return json.loads(llm_output)
    except json.JSONDecodeError:
        # If that fails, try to find all search objects and reconstruct the JSON
        try:
            # This regex will find all dictionaries that look like search objects
            searches = re.findall(r'\{\s*"rationale":.*?"results":.*?\}\s*\}', llm_output, re.DOTALL)
            
            if not searches:
                raise ValueError("No search objects found in the output.")

            # Reconstruct the JSON object
            reconstructed_json_string = f'{{"searches": [{", ".join(searches)}]}}'
            
            return json.loads(reconstructed_json_string)

        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse or reconstruct JSON: {e}")
# --- End of new helper function ---


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

    print("\n--- save_analyst_report tool called ---")
    logger.info("\n--- save_analyst_report tool called ---")
    filepath = "state/analyst_report.json"
    file_data = {"reports": []}
    print(f"Loading existing analyst reports into memory from {filepath}")
    logger.info(f"Loading existing analyst reports into memory from {filepath}")
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        with open(filepath, "r") as f:
            file_data = json.load(f)
    print(f"Appending new analyst report to data structure")
    logger.info(f"Appending new analyst report to data structure")
    file_data["reports"].append(analyst_report)
    try:
        with open(filepath, "w") as f:
            json.dump(file_data, f, indent=2)
    except Exception as e:
        print(f"Error saving analyst report: {e}")
        logger.error(f"Error saving analyst report: {e}")
        raise ToolException(f"Error saving analyst report: {e}")
    
    print(f"Successfully wrote analyst report to {filepath}")
    logger.info(f"Successfully wrote analyst report to {filepath}")
    return {
        "analyst_status": f"Successfully wrote analyst report to `state/analyst_report.json`"
    }

@tool
def initialize_researcher_report(timestamp: str) -> dict:
    """
    Initializes the researcher's report.
    This tool should be called once at the beginning of the researcher's workflow.
    It reads the analyst's report, creates the initial structure for the researcher_report.json,
    and returns the report_id and the list of gaps to be populated into the AgentState.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    print("\n--- initialize_researcher_report tool called, attempting to load analyst_report.json ---")
    logger.info("\n--- initialize_researcher_report tool called, attempting to load analyst_report.json ---")

    try:
        analyst_report_str = load_report('analyst_report.json')
    except Exception as e:
        logger.error(f"Error loading analyst report: {e}")
        print(f"Error loading analyst report: {e}")
        raise ToolException(f"Error loading analyst report: {e}")

    if "No report found" in analyst_report_str:
        logger.error("Analyst report not found.")
        print("Analyst report not found.")
        raise ToolException("Analyst report not found.")
    
    print(f"Loaded analyst report:\n{analyst_report_str}")
    logger.info(f"Loaded analyst report:\n{analyst_report_str}")

    analyst_report = json.loads(analyst_report_str)
    
    report_id = f"res_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
    print(f"Generated researcher report ID: {report_id}")
    logger.info(f"Generated researcher report ID: {report_id}")

    gaps_to_do = [
        {"gap_id": gap["gap_id"], "description": gap["description"], "research_topic": gap["research_topic"], "searches": []}
        for gap in analyst_report.get("identified_gaps", [])
    ]
    
    new_report = {
        "report_id": report_id,
        "gaps": gaps_to_do
    }

    print(f"Initialized new researcher report:\n{json.dumps(new_report, indent=2)}")
    logger.info(f"Initialized new researcher report:\n{json.dumps(new_report, indent=2)}")

    filepath = "state/researcher_report.json"

    print(f"Loading researcher reports into memory from {filepath}")
    logger.info(f"Loading researcher reports into memory from {filepath}")
    try:
        with open(filepath, "r") as f:
            file_data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        print(f"Error reading {filepath}: {e}")
        raise ToolException(f"Error reading {filepath}: {e}")

    file_data = {"reports": []}
    print(f"Loading researcher reports into data structure")
    logger.info(f"Loading researcher reports into data structure")
    try:
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            with open(filepath, "r") as f:
                file_data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading {filepath} into data structure: {e}")
        print(f"Error loading {filepath} into data structure: {e}")
        raise ToolException(f"Error loading {filepath} into data structure: {e}")

    print(f"Appending new report to researcher reports data structure")
    logger.info(f"Appending new report to researcher reports data structure")
    try:
        file_data["reports"].append(new_report)
        print(f"Successfully appended new report to researcher reports data structure")
        logger.info(f"Successfully appended new report to researcher reports data structure")
    except Exception as e:
        logger.error(f"Error appending new report to researcher reports data structure: {e}")
        print(f"Error appending new report to researcher reports data structure: {e}")
        raise ToolException(f"Error appending new report to researcher reports data structure: {e}")

    print(f"Writing updated researcher reports to {filepath}")
    logger.info(f"Writing updated researcher reports to {filepath}")
    try:
        with open(filepath, "w") as f:
            json.dump(file_data, f, indent=2)
        print(f"Successfully wrote updated researcher reports to {filepath}")
        logger.info(f"Successfully wrote updated researcher reports to {filepath}")
    except Exception as e:
        logger.error(f"Error writing updated researcher reports to {filepath}: {e}")
        print(f"Error writing updated researcher reports to {filepath}: {e}")
        raise ToolException(f"Error writing updated researcher reports to {filepath}: {e}")

    return {
        "researcher_report_id": report_id,
        "researcher_gaps_todo": gaps_to_do
    }

@tool
def update_researcher_report(report_id: str, current_gap: dict, searches: dict):
    """
    Updates the researcher's report with the results of a single search.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    print(f"Updating researcher report {report_id} with new gap data.")
    logger.info(f"Updating researcher report {report_id} with new gap data.")

    filepath = "state/researcher_report.json"
    try:
        with open(filepath, "r") as f:
            file_data = json.load(f)
    except Exception as e:
        logger.error(f"Could not read or parse {filepath}. Error: {str(e)}")
        print(f"[ERROR] Could not read or parse {filepath}. Error: {str(e)}")
        raise ToolException(f"Could not read or parse {filepath}: {e}")

    # Find the report index
    report_list = file_data.get("reports", [])
    report_index = next((i for i, r in enumerate(report_list) if r.get("report_id") == report_id), None)
    if report_index is None:
        print(f"Report with ID {report_id} not found.")
        logger.error(f"Report with ID {report_id} not found.")
        raise ToolException(f"Report with ID {report_id} not found.")

    # Find the gap index
    gap_list = report_list[report_index].get("gaps", [])
    gap_id = current_gap.get("gap_id")
    gap_index = next((i for i, g in enumerate(gap_list) if g.get("gap_id") == gap_id), None)
    if gap_index is None:
        print(f"Gap with ID {gap_id} not found in report {report_id}.")
        logger.error(f"Gap with ID {gap_id} not found in report {report_id}.")
        raise ToolException(f"Gap with ID {gap_id} not found in report {report_id}.")

    # Update the gap's searches

    print(f"Updating {report_id}/{gap_id} in the data structure with new search results.")
    logger.info(f"Updating {report_id}/{gap_id} in the data structure with new search results.")
    try:
        file_data("reports")[report_index]("gaps")[gap_index].set("searches", searches)
    except Exception as e:
        logger.error(f"Error updating {report_id}/{gap_id} in the data structure: {e}")
        print(f"[ERROR] Error updating {report_id}/{gap_id} in the data structure: {e}")
        raise ToolException(f"Error updating {report_id}/{gap_id} in the data structure: {e}")
    print(f"Inserted {len(searches)} search results to {report_id}/{gap_id} in the data structure.")
    logger.info(f"Inserted {len(searches)} search results to {report_id}/{gap_id} in the data structure.")

    # Write back to file
    try:
        with open(filepath, "w") as f:
            json.dump(file_data, f, indent=2)
        logger.info(f"Successfully wrote updated data for report {report_id} to {filepath}")
        print(f"Successfully wrote updated data for report {report_id} to {filepath}")
        return f"Successfully updated report {report_id} with search for gap {gap_id}."
    except Exception as e:
        logger.error(f"Failed to write to {filepath}: {e}")
        print(f"[ERROR] Failed to write to {filepath}: {e}")
        raise ToolException(f"Failed to write to {filepath}: {e}")

@tool
def load_report(filename: str) -> str:
    """Loads the most recent report from a file in the state directory."""
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    filepath = f"state/{filename}"
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        print(f"[ERROR] No report found at {filepath}.")
        logger.warning(f"No report found at {filepath}.")
        return "No report found."
    with open(filepath, "r") as f:
        data = json.load(f)
    if "reports" in data and isinstance(data["reports"], list) and data["reports"]:
        print(f"Loaded report from {filepath}: {json.dumps(data['reports'][-1], indent=2)}")
        logger.info(f"Loaded report from {filepath}: {json.dumps(data['reports'][-1], indent=2)}")
        return json.dumps(data["reports"][-1])
    else:
        print(f"[ERROR] No reports found in the file.")
        logger.error(f"No reports found in the file.")
        return "No reports found in the file."

@tool
def human_approval(plan: str) -> str:
    """
    Asks for human approval for a given plan.
    The plan is a string that describes the actions to be taken.
    Returns 'approved' or 'denied'.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    print(f"\nPROPOSED PLAN:\n{plan}")
    logger.info(f"PROPOSED PLAN:\n{plan}")
    response = input("Do you approve this plan? (y/n): ").lower()
    if response == 'y':
        print("Approved.")
        logger.info("Approved.")
        return "approved"
    print("Denied.")
    logger.info("Denied.")
    return "denied"

def create_agent_executor(llm: ChatOpenAI, tools: list, system_prompt: str):
    """Helper function to create a sub-agent executor."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, handle_parsing_errors=True, max_iterations=20)

# --- Agent Node Functions ---

async def run_analyst(state: AgentState):

    print("--- Running Analyst Node ---")
    logger = state['logger']
    timestamp = state['timestamp']

    # One-time initialization of the report and state
    if not state.get("analyst_report_id"):
        print("--- State not initialized. Performing initialization of analyst now. ---")
        try:
            report_id = f"ana_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
            if report_id:
                state["analyst_report_id"] = report_id
                logger.info(f"Successfully initialized report with ID: {state['analyst_report_id']}")
            else:
                logger.error(f"Failed to initialize analyst report: {report_id}")
                return {"status": f"Failed to initialize analyst report {report_id}."}
        except Exception as e:
            logger.error(f"Failed to initialize analyst report: {e}")
            return {"status": f"Failed to initialize analyst report {report_id}."}

    analyst_tools = [t for t in state['mcp_tools'] if t.name in ["query", "graphs_get", "graph_labels"]]

    with open("prompt_templates/analyst_prompt.txt", "r") as f:
        analyst_prompt = f.read()

    agent_executor = create_agent_executor(state['model'], analyst_tools, analyst_prompt)
    
    task_input = "Your task is to identify knowledge gaps. Begin now."

    analyst_result = await agent_executor.ainvoke({"input": task_input})

    try:
        json_output = analyst_result.get("output", "")
        print(f"Attempting to save analyst report:\n{json_output}")
        logger.info(f"Attempting to save analyst report:\n{json_output}")
        save_analyst_report(json_output)
    except Exception as e:
        print(f"[ERROR] Failed to process analyst result: {e}")
        logger.error(f"Failed to process analyst result: {e}")

    final_status = f"Successfully completed analysis and wrote report with ID {state['analyst_report_id']} to file `state/analyst_report.json`."
    print(final_status)
    logger.info(final_status)
    return {"status": final_status}

async def run_researcher(state: AgentState):
    """
    The main node for the researcher workflow. It manages the state and calls
    a specialized agent to perform research for each knowledge gap.
    """
    print("--- Running Researcher Node ---")
    logger = state['logger']  # Ensure logger is retrieved from state

    # One-time initialization of the report and state
    if not state.get("researcher_report_id"):
        print("--- State not initialized. Calling initialize_researcher_report directly. ---")
        try:
            init_result = initialize_researcher_report(state['timestamp'])
            if isinstance(init_result, dict):
                state["researcher_report_id"] = init_result.get("researcher_report_id")
                state["researcher_gaps_todo"] = init_result.get("researcher_gaps_todo")
                state["researcher_gaps_complete"] = []
                print(f"Initialized researcher state: {init_result}")
                logger.info(f"Successfully initialized report with ID: {state['researcher_report_id']} and gaps to research: {state['researcher_gaps_todo']}")
            else:
                print(f"[ERROR] Failed to initialize researcher report: {init_result}")
                logger.error(f"Failed to initialize researcher report: {init_result}")
                return {"status": f"Failed to initialize researcher report: {init_result}."}
        except Exception as e:
            logger.error(f"Failed to initialize researcher report: {e}")
            return {"status": f"Failed to initialize researcher report: {e}."}

    # Create the specialized agent for performing searches
    with open("prompt_templates/search_agent_prompt.txt", "r") as f:
        search_agent_prompt = f.read()

    search_tools = [tool for tool in state['mcp_tools'] if tool.name in ['google_search', 'fetch']]
    search_agent = create_agent_executor(state['model'], search_tools, search_agent_prompt)

    # Main control loop, managed by the node
    gaps_todo = state.get("researcher_gaps_todo", [])
    if isinstance(gaps_todo, list):
        for current_gap in gaps_todo:
            state['researcher_current_gap'] = current_gap
            gap_id = current_gap['gap_id']
            research_topic = current_gap['research_topic']

            print(f"\n--- Starting research for gap: {gap_id}, research topic: {research_topic} ---")
            logger.info(f"--- Starting research for gap: {gap_id}, research topic: {research_topic} ---")

            try:
                # Invoke the specialized agent for just ONE gap
                agent_result = await search_agent.ainvoke({"input": research_topic})
                print(f"\nAgent for gap {gap_id} finished. Raw output:\n{agent_result.get('output')}")
                logger.info(f"Agent for gap {gap_id} finished. Raw output:\n{agent_result.get('output')}")
                
                # --- Start of modified block ---
                # The node, not the agent, saves the results
                try:
                    # Use the new helper function to extract and clean the JSON
                    json_output = _extract_and_clean_json(agent_result.get("output", ""))
                    print(f"Successfully parsed searches for gap {gap_id}: {json_output}")
                    logger.info(f"Successfully parsed searches for gap {gap_id}: {json_output}")

                except (ValueError, json.JSONDecodeError) as e:
                    print(f"[ERROR] Agent for gap {gap_id} returned invalid JSON: {agent_result.get('output')}. Error: {e}")
                    logger.error(f"Agent for gap {gap_id} returned invalid JSON: {agent_result.get('output')}. Error: {e}")
                    continue
                # --- End of modified block ---

                logger.info(f"Preparing to update report for gap {gap_id} with payload")
                print(f"Preparing to update report for gap {gap_id} with payload")
                try:
                    report_id = state['researcher_report_id']
                    current_gap = state['researcher_current_gap']
                    result = update_researcher_report(report_id, current_gap, json_output)
                    print(f"update_researcher_report returned: {result}")
                    logger.info(f"update_researcher_report returned: {result}")
                except Exception as e:
                    print(f"[ERROR] update_researcher_report failed for gap {gap_id}: {e}")
                    logger.error(f"update_researcher_report failed for gap {gap_id}: {e}", exc_info=True)
                    continue
                
                print(f"--- Successfully completed research and report writing for gap: {gap_id} ---")
                logger.info(f"--- Successfully completed research and report writing for gap: {gap_id} ---")
                if "researcher_gaps_complete" not in state or state["researcher_gaps_complete"] is None:
                    state["researcher_gaps_complete"] = []
                state["researcher_gaps_complete"].append(gap_id)

            except Exception as e:
                print(f"[ERROR] An unexpected error occurred while processing gap {gap_id}: {e}")
                logger.error(f"An unexpected error occurred while processing gap {gap_id}: {e}", exc_info=True)
                continue


    final_status = f"Successfully and incrementally completed researcher report with ID {state['researcher_report_id']} and wrote report to researcher_report.json."
    logger.info(final_status)
    return {"status": final_status}

async def run_curator(state: AgentState):
    print("--- Running Curator Agent ---")
    all_tools = state['mcp_tools']
    model = state['model']
    logger = state['logger']
    timestamp = state['timestamp']

    curator_tools = [t for t in all_tools if t.name in ["fetch", "documents_upload_file", "documents_upload_files", "documents_insert_text", "documents_pipeline_status"]] + [load_report]
    curator_prompt = '''Your goal is to review and ingest new sources into the LightRAG knowledge base. 
1.  **Load the researcher report**: Use the `load_report` tool with `researcher_report.json`.
2.  **Process URLs**: For each URL in the report, fetch the content.
3.  **Ingest Sources**: Ingest the successfully fetched and relevant content.
4.  **Report Results**: Save a report of your actions to `curator_report.json`.'''
    
    agent_executor = create_agent_executor(model, curator_tools, curator_prompt)
    
    task_input = "Your task is to curate the latest research report. Begin now."

    result = await agent_executor.ainvoke({"input": task_input, "timestamp": timestamp})

    logger.info(f"Curator Agent finished with output: {result['output']}")
    return {"status": result['output']}

async def run_auditor(state: AgentState):
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

    agent_executor = create_agent_executor(model, auditor_tools, auditor_prompt)
    
    task_input = "Your task is to audit the knowledge base. Begin now."

    result = await agent_executor.ainvoke({"input": task_input, "timestamp": timestamp})
    
    logger.info(f"Auditor Agent finished with output: {result['output']}")
    return {"status": result['output']}

async def run_fixer(state: AgentState):
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

    agent_executor = create_agent_executor(model, fixer_tools, fixer_prompt)

    task_input = "Your task is to fix issues from the auditor's report. Begin now."

    result = await agent_executor.ainvoke({"input": task_input, "timestamp": timestamp})

    logger.info(f"Fixer Agent finished with output: {result['output']}")
    return {"status": result['output']}


async def run_advisor(state: AgentState):
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

    agent_executor = create_agent_executor(model, advisor_tools, advisor_prompt)
    
    task_input = "Your task is to provide recommendations based on the latest audit and fix reports. Begin now."

    result = await agent_executor.ainvoke({"input": task_input, "timestamp": timestamp})

    logger.info(f"Advisor Agent finished with output: {result['output']}")
    return {"status": result['output']}