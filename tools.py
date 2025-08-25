# tools.py
import re
import json_repair
from langchain_core.tools import tool, ToolException
import json
import os

def extract_and_clean_json(llm_output: str) -> dict:
    
    # Use json_repair.loads() directly as a robust, drop-in replacement for json.loads()
    try:
        return json_repair.loads(llm_output)
    except Exception as e:
        raise ValueError(f"Failed to repair or parse JSON: {e}")

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

@tool
def save_analyst_report(analyst_report: str) -> dict:
    """
    Saves the analyst's report.
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
