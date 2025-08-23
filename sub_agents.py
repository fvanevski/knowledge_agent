# sub_agents.py
from langchain_openai.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
import json
import os
from datetime import datetime
from state import AgentState

@tool
def initialize_researcher_report(timestamp: str) -> dict:
    """
    Initializes the researcher's report.
    This tool should be called once at the beginning of the researcher's workflow.
    It reads the analyst's report, creates the initial structure for the researcher_report.json,
    and returns the report_id and the list of gaps to be populated into the AgentState.
    """
    print("\n--- initialize_researcher_report tool called ---")
    analyst_report_str = load_report('analyst_report.json')
    if "No report found" in analyst_report_str:
        raise ToolException("Analyst report not found.")
    
    analyst_report = json.loads(analyst_report_str)
    
    report_id = f"res_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
    
    gaps_to_do = [
        {"gap_id": gap["gap_id"], "description": gap["description"], "research_topic": gap["research_topic"]}
        for gap in analyst_report.get("identified_gaps", [])
    ]
    
    new_report = {
        "report_id": report_id,
        "timestamp": timestamp,
        "gaps": []
    }
    
    filepath = "state/researcher_report.json"
    file_data = {"reports": []}
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        with open(filepath, "r") as f:
            file_data = json.load(f)
    
    file_data["reports"].append(new_report)
    
    with open(filepath, "w") as f:
        json.dump(file_data, f, indent=4)
        
    return {
        "researcher_report_id": report_id,
        "researcher_gaps_todo": gaps_to_do
    }

@tool
def update_researcher_report(report_id: str, gap_id: str, description: str, search_rationale: str, search_parameters: dict, search_results: list):
    """
    Updates the researcher's report with the results of a single search.
    """
    print(f"\n--- update_researcher_report tool called for gap_id: {gap_id} ---")
    filepath = "state/researcher_report.json"
    
    with open(filepath, "r") as f:
        file_data = json.load(f)
        
    report_found = False
    for report in file_data["reports"]:
        if report["report_id"] == report_id:
            report_found = True
            gap_found = False
            for gap in report["gaps"]:
                if gap["gap_id"] == gap_id:
                    gap_found = True
                    search_id = f"search_{gap_id}_{len(gap['searches']) + 1}"
                    gap["searches"].append({
                        "search_id": search_id,
                        "rationale": search_rationale,
                        "parameters": search_parameters,
                        "results": search_results
                    })
                    break
            if not gap_found:
                search_id = f"search_{gap_id}_1"
                report["gaps"].append({
                    "gap_id": gap_id,
                    "description": description,
                    "searches": [{
                        "search_id": search_id,
                        "rationale": search_rationale,
                        "parameters": search_parameters,
                        "results": search_results
                    }]
                })
            break
            
    if not report_found:
        raise ToolException(f"Report with ID {report_id} not found in {filepath}")

    with open(filepath, "w") as f:
        json.dump(file_data, f, indent=4)
        
    return f"Successfully updated report {report_id} with search for gap {gap_id}."

@tool
def load_report(filename: str) -> str:
    """Loads the most recent report from a file in the state directory."""
    filepath = f"state/{filename}"
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return "No report found."
    with open(filepath, "r") as f:
        data = json.load(f)
    if "reports" in data and isinstance(data["reports"], list) and data["reports"]:
        return json.dumps(data["reports"][-1])
    else:
        return "No reports found in the file."

@tool
def human_approval(plan: str) -> str:
    """
    Asks for human approval for a given plan.
    The plan is a string that describes the actions to be taken.
    Returns 'approved' or 'denied'.
    """
    print(f"\nPROPOSED PLAN:\n{plan}")
    response = input("Do you approve this plan? (y/n): ").lower()
    if response == 'y':
        return "approved"
    return "denied"

def create_agent_executor(llm: ChatOpenAI, tools: list, system_prompt: str):

    """Helper function to create a sub-agent executor."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, handle_parsing_errors=True, max_iterations=150)

# --- Agent Node Functions ---

async def run_analyst(state: AgentState):
    print("--- Running Analyst Agent ---")
    all_tools = state['mcp_tools']
    model = state['model']
    logger = state['logger']
    timestamp = state['timestamp']
    
    analyst_tools = [t for t in all_tools if t.name in ["query", "graphs_get", "graph_labels"]] + [save_report]
    with open("prompt_templates/analyst_prompt.txt", "r") as f:
        analyst_prompt = f.read()
    
    agent_executor = create_agent_executor(model, analyst_tools, analyst_prompt)
    
    task_input = "Your task is to identify knowledge gaps. Begin now."
    
    result = await agent_executor.ainvoke({"input": task_input, "timestamp": timestamp})
    
    logger.info(f"Analyst Agent finished with output: {result['output']}")
    return {"status": result['output']}

async def run_researcher(state: AgentState):
    print("--- Running Researcher Agent ---")
    model = state['model']
    logger = state['logger']
    timestamp = state['timestamp']
    all_tools = state['mcp_tools']

    # 1. Explicitly check if the state needs initialization
    if not state.get("researcher_report_id"):
        print("--- State not initialized. Calling initialize_researcher_report directly. ---")
        # Call the tool directly from the node, not through the agent
        init_result = initialize_researcher_report(timestamp)
        # Update the state with the results from the initialization
        state.update(init_result)
        state["status"] = "Initialized researcher report. Starting research."
        logger.info("Researcher report initialized.")
        # Now, the state is guaranteed to be initialized for the next steps.

    # 2. Setup and run the main research agent
    # The agent now assumes the state is already initialized.
    researcher_tools = [t for t in all_tools if t.name in ["google_search", "fetch"]] + [update_researcher_report]

    with open("prompt_templates/researcher_prompt.txt", "r") as f:
        researcher_prompt = f.read()

    agent_executor = create_agent_executor(model, researcher_tools, researcher_prompt)

    input_data = {
        "input": "Your task is to conduct research based on the latest analyst report. Begin now.",
        "researcher_report_id": state.get("researcher_report_id"),
        "researcher_gaps_todo": state.get("researcher_gaps_todo"),
        "researcher_gaps_complete": state.get("researcher_gaps_complete", [])
    }

    result = await agent_executor.ainvoke(input_data)

    # The final state update will just be the status from the agent
    final_status = result.get('output', 'Researcher finished with no output.')
    logger.info(f"Researcher Agent finished with output: {final_status}")
    return {"status": final_status}

async def run_curator(state: AgentState):
    print("--- Running Curator Agent ---")
    all_tools = state['mcp_tools']
    model = state['model']
    logger = state['logger']
    timestamp = state['timestamp']

    curator_tools = [t for t in all_tools if t.name in ["fetch", "documents_upload_file", "documents_upload_files", "documents_insert_text", "documents_pipeline_status"]] + [load_report, save_report]
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
    
    auditor_tools = [t for t in all_tools if t.name in ["graphs_get", "query"]] + [save_report]
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
    
    fixer_tools = [t for t in all_tools if t.name in ["graph_update_entity", "documents_delete_entity", "graph_update_relation", "documents_delete_relation", "graph_entity_exists"]] + [load_report, human_approval, save_report]
    fixer_prompt = '''Your goal is to correct data quality issues.
1.  **Load Auditor's Report**: Load `auditor_report.json`.
2.  **Create a Plan**: Create a step-by-step plan to correct the issues.
3.  **Get Human Approval**: Use `human_approval` to get your plan approved.
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
    
    advisor_tools = [t for t in all_tools if t.name in ["list_allowed_directories", "list_directory", "search_files", "read_text_file"]] + [load_report, save_report]
    advisor_prompt = '''Your goal is to provide recommendations for systemic improvements.
1.  **Analyze Reports**: Load and analyze `auditor_report.json` and `fixer_report.json`.
2.  **Generate Recommendations**: Based on recurring patterns, generate actionable recommendations for ingestion prompts or server configuration.
3.  **Compile Report**: Save a final report with your top 3-5 suggestions to `advisor_report.json`.'''

    agent_executor = create_agent_executor(model, advisor_tools, advisor_prompt)
    
    task_input = "Your task is to provide recommendations based on the latest audit and fix reports. Begin now."

    result = await agent_executor.ainvoke({"input": task_input, "timestamp": timestamp})

    logger.info(f"Advisor Agent finished with output: {result['output']}")
    return {"status": result['output']}
