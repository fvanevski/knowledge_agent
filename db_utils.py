# db_utils.py
import os
import psycopg2
import json
from psycopg2.extras import Json
from contextlib import contextmanager
import json_repair

# --- Database Connection ---
@contextmanager
def get_db_connection():
    """Provides a database connection using a context manager."""
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        yield conn
    finally:
        conn.close()

# --- Table Creation ---
def create_tables():
    """Creates all necessary tables in the database if they don't exist."""
    commands = (
        """CREATE TABLE IF NOT EXISTS analyst_reports (id SERIAL PRIMARY KEY, report_id VARCHAR(255) UNIQUE NOT NULL, report JSONB, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);""",
        """CREATE TABLE IF NOT EXISTS researcher_reports (id SERIAL PRIMARY KEY, report_id VARCHAR(255) UNIQUE NOT NULL, report JSONB, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);""",
        """CREATE TABLE IF NOT EXISTS curator_reports (id SERIAL PRIMARY KEY, report_id VARCHAR(255) UNIQUE NOT NULL, report JSONB, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);""",
        """CREATE TABLE IF NOT EXISTS auditor_reports (id SERIAL PRIMARY KEY, report_id VARCHAR(255) UNIQUE NOT NULL, report JSONB, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);""",
        """CREATE TABLE IF NOT EXISTS fixer_reports (id SERIAL PRIMARY KEY, report_id VARCHAR(255) UNIQUE NOT NULL, report JSONB, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);""",
        """CREATE TABLE IF NOT EXISTS advisor_reports (id SERIAL PRIMARY KEY, report_id VARCHAR(255) UNIQUE NOT NULL, report JSONB, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);"""
    )
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for command in commands:
                cur.execute(command)
        conn.commit()

# --- Utility Functions ---

def extract_and_clean_json(llm_output: str) -> dict:
    
    # Use json_repair.loads() directly as a robust, drop-in replacement for json_repair.loads()
    try:
        return json_repair.loads(llm_output)
    except Exception as e:
        raise ValueError(f"Failed to repair or parse JSON: {e}")

# --- Report Handling Functions ---
def _save_report(table_name: str, report_data: dict):
    """Generic function to save a report to a specified table."""
    report_id = report_data.get("report_id")
    if not report_id:
        raise ValueError("Report data must include a 'report_id'")
    
    report_json_string = json.dumps(report_data)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {table_name} (report_id, report) VALUES (%s, %s);",
                (report_id, report_json_string)
            )
        conn.commit()

def save_analyst_report(report_data: dict):
    _save_report("analyst_reports", report_data)

def save_auditor_report(report_data: dict):
    _save_report("auditor_reports", report_data)

def save_fixer_report(report_data: dict):
    _save_report("fixer_reports", report_data)

def save_advisor_report(report_data: dict):
    _save_report("advisor_reports", report_data)

def initialize_researcher(timestamp: str) -> dict:
    """Initializes the researcher's report in the database."""
    analyst_report_str = load_latest_report('analyst')
    analyst_report = json.loads(analyst_report_str)
    
    report_id = f"res_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
    
    gaps_to_do = [
        {"gap_id": gap["gap_id"], "description": gap["description"], "research_topic": gap["research_topic"], "searches": [" "]}
        for gap in analyst_report.get("identified_gaps", [])
    ]
    
    new_report = {"report_id": report_id, "gaps": gaps_to_do}
    report_json_string = json.dumps(new_report)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO researcher_reports (report_id, report) VALUES (%s, %s);",
                (report_id, report_json_string)
            )
        conn.commit()
        
    return {"researcher_report_id": report_id, "researcher_gaps_todo": gaps_to_do}

def update_researcher_report(report_id: str, gap_id: str, searches: list):
    """Updates a researcher report in the database with search results."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Read the existing report
            cur.execute("SELECT report FROM researcher_reports WHERE report_id = %s FOR UPDATE;", (report_id,))
            result = cur.fetchone()
            if not result:
                raise ValueError(f"No researcher report found with id {report_id}")
            
            report_data = result[0]

            # Modify the report in Python
            gaps = report_data.get("gaps", [])
            gap_found = False
            for gap in gaps:
                if gap.get("gap_id") == gap_id:
                    gap["searches"] = searches
                    gap_found = True
                    break
            
            if not gap_found:
                # This case should ideally not be reached if initialization is correct
                raise ValueError(f"Gap with id {gap_id} not found in report {report_id}")

            # Write the modified report back
            report_json_string = json.dumps(report_data)
            cur.execute(
                "UPDATE researcher_reports SET report = %s WHERE report_id = %s;",
                (report_json_string, report_id)
            )
        conn.commit()

def initialize_curator(timestamp: str) -> dict:
    """Initializes the curator's report in the database."""
    researcher_report_str = load_latest_report('researcher')
    researcher_report = json.loads(researcher_report_str)
    
    report_id = f"cur_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
    
    searches_todo = []
    for gap in researcher_report.get("gaps", []):
        research_topic = gap.get("research_topic", {})
        for search in gap.get("searches", []):
            searches_todo.append({
                "search": search,
                "research_topic": research_topic
            })

    new_report = {
        "report_id": report_id,
        "urls_for_ingestion": [],
        "url_ingestion_status": []
    }
    report_json_string = json.dumps(new_report)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO curator_reports (report_id, report) VALUES (%s, %s);",
                (report_json_string, report_id)
            )
        conn.commit()
        
    return {"curator_report_id": report_id, "curator_searches_todo": searches_todo}

def update_curator_report(report_id: str, job: str, results: list):
    """Appends results to a job list in a curator report."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Read the existing report
            cur.execute("SELECT report FROM curator_reports WHERE report_id = %s FOR UPDATE;", (report_id,))
            result = cur.fetchone()
            if not result:
                raise ValueError(f"No curator report found with id {report_id}")
            
            report_data = result[0]

            # Modify the report in Python
            if job not in report_data:
                report_data[job] = []
            
            report_data[job].extend(results)

            # Write the modified report back
            report_json_string = json.dumps(report_data)
            cur.execute(
                "UPDATE curator_reports SET report = %s WHERE report_id = %s;",
                (report_json_string, report_id)
            )
        conn.commit()

def load_latest_report(report_type: str) -> str:
    """Loads the most recent report from the database."""
    table_map = {
        "analyst": "analyst_reports",
        "researcher": "researcher_reports",
        "curator": "curator_reports"
    }
    table_name = table_map.get(report_type)
    if not table_name:
        raise ValueError(f"Invalid report_type '{report_type}'.")
        
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT report FROM {table_name} ORDER BY created_at DESC LIMIT 1;")
            result = cur.fetchone()
            if result:
                return json.dumps(result[0])
            else:
                raise FileNotFoundError(f"No reports found in table {table_name}")
            