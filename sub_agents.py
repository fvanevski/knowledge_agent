# sub_agents.py
from langchain_openai.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
import json
import os
from state import AgentState

@tool
def save_report(report: dict, filename: str):
    """Saves a report to a file in the state directory, appending to the 'reports' list within a JSON object."""
    print(f"\n--- save_report tool called for {filename} ---")
    
    # Ensure the 'state' directory exists
    if not os.path.exists('state'):
        os.makedirs('state')
        
    filepath = f"state/{filename}"
    
    try:
        # The agent often passes a string, so we must parse it.
        if isinstance(report, str):
            print("DEBUG: 'report' is a string, parsing as JSON.")
            try:
                report = json.loads(report)
            except json.JSONDecodeError as e:
                raise ToolException(f"Tool input 'report' was a string but is not valid JSON. Error: {e}. Content: '{report}'")

        if not isinstance(report, dict):
            raise TypeError(f"The 'report' argument must be a dictionary or a valid JSON string, but got {type(report)}.")

        # Read existing data
        file_data = {"reports": []}
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            with open(filepath, "r") as f:
                file_data = json.load(f)
                if "reports" not in file_data or not isinstance(file_data["reports"], list):
                    file_data["reports"] = []
        
        # Append new report
        file_data["reports"].append(report)
        
        # Write data back to file
        with open(filepath, "w") as f:
            json.dump(file_data, f, indent=4)

        # Verification step
        with open(filepath, "r") as f:
            verify_data = json.load(f)
        
        if verify_data["reports"][-1] == report:
            print(f"--- File write to {filename} VERIFIED ---")
            return f"Successfully saved and verified report to {filepath}"
        else:
            raise ToolException(f"Verification failed. The saved data in {filename} does not match the input report.")

    except (IOError, TypeError, json.JSONDecodeError, ToolException) as e:
        print(f"--- ERROR in save_report: {e} ---")
        raise ToolException(f"An error occurred in save_report: {e}")

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
    return AgentExecutor(agent=agent, tools=tools, handle_parsing_errors=True, max_iterations=25)

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
    all_tools = state['mcp_tools']
    model = state['model']
    logger = state['logger']
    timestamp = state['timestamp']

    # **ADD THE `write_text_file` TOOL**
    researcher_tools = [t for t in all_tools if t.name in ["google_search", "fetch", "write_text_file"]] + [load_report, save_report]
    
    with open("prompt_templates/researcher_prompt.txt", "r") as f:
        researcher_prompt = f.read()

    agent_executor = create_agent_executor(model, researcher_tools, researcher_prompt)

    task_input = "Your task is to conduct research based on the latest analyst report. Begin now."

    result = await agent_executor.ainvoke({"input": task_input, "timestamp": timestamp})

    logger.info(f"Researcher Agent finished with output: {result['output']}")
    return {"status": result['output']}

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
