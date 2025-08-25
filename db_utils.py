# db_utils.py
import os
import psycopg2
import json
from psycopg2.extras import Json
from contextlib import contextmanager

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
    """Creates the necessary tables in the database if they don't exist."""
    commands = (
        """
        CREATE TABLE IF NOT EXISTS analyst_reports (
            id SERIAL PRIMARY KEY,
            report_id VARCHAR(255) UNIQUE NOT NULL,
            report JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS researcher_reports (
            id SERIAL PRIMARY KEY,
            report_id VARCHAR(255) UNIQUE NOT NULL,
            report JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS curator_reports (
            id SERIAL PRIMARY KEY,
            report_id VARCHAR(255) UNIQUE NOT NULL,
            report JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
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

def save_analyst_report(report_data: dict):
    """Saves the analyst's report to the database."""
    report_id = report_data.get("report_id")
    if not report_id:
        raise ValueError("Report data must include a 'report_id'")
    
    ordered_report = {
        "report_id": report_id,
        "knowledge_base_summary": report_data.get("knowledge_base_summary"),
        "identified_gaps": report_data.get("identified_gaps")
    }
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO analyst_reports (report_id, report) VALUES (%s, %s);",
                (report_id, Json(ordered_report))
            )
        conn.commit()

def initialize_researcher(timestamp: str) -> dict:
    """Initializes the researcher's report in the database."""
    analyst_report_str = load_latest_report('analyst')
    analyst_report = json.loads(analyst_report_str)
    
    report_id = f"res_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
    
    gaps_to_do = [
        {"gap_id": gap["gap_id"], "description": gap["description"], "research_topic": gap["research_topic"], "searches": []}
        for gap in analyst_report.get("identified_gaps", [])
    ]
    
    new_report = {"report_id": report_id, "gaps": gaps_to_do}

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO researcher_reports (report_id, report) VALUES (%s, %s);",
                (report_id, Json(new_report))
            )
        conn.commit()
        
    return {"researcher_report_id": report_id, "researcher_gaps_todo": gaps_to_do}

def update_researcher_report(report_id: str, gap_id: str, searches: list):
    """Updates a researcher report in the database with search results."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            sql = """
            UPDATE researcher_reports
            SET report = jsonb_set(
                report,
                (
                    SELECT ARRAY['gaps', (elem_index - 1)::text, 'searches']
                    FROM researcher_reports, jsonb_array_elements(report->'gaps') WITH ORDINALITY arr(elem, elem_index)
                    WHERE report_id = %s AND elem->>'gap_id' = %s
                ),
                %s::jsonb
            )
            WHERE report_id = %s AND EXISTS (
                SELECT 1 FROM jsonb_array_elements(report->'gaps') WHERE value->>'gap_id' = %s
            );
            """
            cur.execute(sql, (report_id, gap_id, Json(searches), report_id, gap_id))
        conn.commit()

def initialize_curator(timestamp: str) -> dict:
    """Initializes the curator's report in the database."""
    researcher_report_str = load_latest_report('researcher')
    researcher_report = json.loads(researcher_report_str)
    
    report_id = f"cur_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
    
    searches_todo = [
        search for gap in researcher_report.get("gaps", [])
        for search in gap.get("searches", [])
    ]
    
    new_report = {
        "report_id": report_id,
        "urls_for_ingestion": [],
        "url_ingestion_status": []
    }

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO curator_reports (report_id, report) VALUES (%s, %s);",
                (report_id, Json(new_report))
            )
        conn.commit()
        
    return {"curator_report_id": report_id, "curator_searches_todo": searches_todo}

def update_curator_report(report_id: str, job: str, results: list):
    """Appends results to a job list in a curator report."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            sql = """
            UPDATE curator_reports
            SET report = jsonb_set(
                report,
                ARRAY[%s],
                (report->%s) || %s::jsonb
            )
            WHERE report_id = %s;
            """
            cur.execute(sql, (job, job, Json(results), report_id))
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
            