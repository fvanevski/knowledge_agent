# tools.py
import json_repair
from langchain_core.tools import tool, ToolException
import json
from db_utils import (
    db_save_report, 
    db_load_latest_report, 
    db_update_researcher_report,
    db_update_curator_report
)

def extract_and_clean_json(llm_output: str) -> dict:
    
    # Use json_repair.loads() directly as a robust, drop-in replacement for json_repair.loads()
    try:
        return json_repair.loads(llm_output)
    except Exception as e:
        raise ValueError(f"Failed to repair or parse JSON: {e}")

@tool
def load_report(report_type: str) -> str:
    """Loads the most recent report from the database. `report_type` must be one of 'analyst', 'researcher', or 'curator'."""
    table_map = {
        "analyst": "analyst_reports",
        "researcher": "researcher_reports",
        "curator": "curator_reports"
    }
    table_name = table_map.get(report_type)
    if not table_name:
        raise ToolException(f"Invalid report_type '{report_type}'.")
    try:
        return db_load_latest_report(table_name)
    except FileNotFoundError as e:
        raise ToolException(str(e))

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
    """Saves the analyst's report to the database."""
    import logging
    logger = logging.getLogger('KnowledgeAgent')
    try:
        report_data = json_repair.loads(analyst_report)
        status = f"Parsed analyst report as: {report_data}."
        print(status)
        logger.info(status)
        report_id = report_data.get("report_id")
        print(f"Report ID: {report_id}")
        logger.info(f"Report ID: {report_id}")
        if not report_id:
            raise ValueError("Report data must include a 'report_id'")
        db_save_report("analyst_reports", report_id, report_data)
        status = f"Successfully saved analyst report {report_id} to database."
        print(status)
        logger.info(status)
        return {"status": status}
    except Exception as e:
        status = f"Error saving analyst report: {e}"
        print(status)
        logger.error(status)
        raise ToolException(f"Error saving analyst report: {e}")

@tool
def initialize_researcher(timestamp: str) -> dict:
    """Initializes the researcher's report in the database."""
    try:
        analyst_report_str = db_load_latest_report('analyst_reports')
        analyst_report = json_repair.loads(analyst_report_str)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ToolException(f"Error loading or parsing analyst report: {e}")

    report_id = f"res_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
    gaps_to_do = [
        {"gap_id": gap["gap_id"], "description": gap["description"], "research_topic": gap["research_topic"]}
        for gap in analyst_report.get("identified_gaps", [])
    ]
    
    new_report = {"report_id": report_id, "gaps": gaps_to_do}
    db_save_report("researcher_reports", report_id, new_report)

    return {"researcher_report_id": report_id, "researcher_gaps_todo": gaps_to_do}

@tool
def update_researcher_report(report_id: str, current_gap: dict, search_results: list) -> str:
    """Updates a researcher report in the database with search results."""
    try:
        gap_id = current_gap["gap_id"]
        db_update_researcher_report(report_id, gap_id, search_results)
        return f"Successfully updated searches for gap {gap_id} in report {report_id}."
    except Exception as e:
        raise ToolException(f"Failed to update researcher report: {e}")

@tool
def initialize_curator(timestamp: str) -> dict:
    """Initializes the curator's report in the database."""
    try:
        researcher_report_str = db_load_latest_report('researcher_reports')
        researcher_report = json_repair.loads(researcher_report_str)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ToolException(f"Error loading or parsing researcher report: {e}")

    report_id = f"cur_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
    searches_todo = [
        search for gap in researcher_report.get("gaps", []) 
        for search in gap.get("searches", [])
    ]
    
    new_report = {"report_id": report_id, "urls_for_ingestion": [], "url_ingestion_status": []}
    db_save_report("curator_reports", report_id, new_report)

    return {"curator_report_id": report_id, "curator_searches_todo": searches_todo}

@tool
def update_curator_report(report_id: str, job: str, results: list) -> str:
    """Updates a curator report in the database."""
    try:
        db_update_curator_report(report_id, job, results)
        return f"Successfully updated {job} for report {report_id}."
    except Exception as e:
        raise ToolException(f"Failed to update curator report: {e}")
