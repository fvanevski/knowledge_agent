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

# --- Database Operations ---

def db_save_report(table_name: str, report_id: str, report_data: dict):
    """Saves a report to the specified table."""
    sql = f"INSERT INTO {table_name} (report_id, report) VALUES (%s, %s);"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (report_id, Json(report_data)))
        conn.commit()

def db_load_latest_report(table_name: str) -> str:
    """Loads the most recent report from the specified table."""
    sql = f"SELECT report FROM {table_name} ORDER BY created_at DESC LIMIT 1;"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            result = cur.fetchone()
            if result:
                return json.dumps(result[0])
            else:
                raise FileNotFoundError(f"No reports found in table {table_name}")

def db_update_researcher_report(report_id: str, gap_id: str, searches: list):
    """Updates the searches for a specific gap in a researcher report."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # First, find the index of the gap to update
            cur.execute("SELECT report FROM researcher_reports WHERE report_id = %s;", (report_id,))
            report = cur.fetchone()[0]
            
            gap_index = -1
            for i, gap in enumerate(report.get("gaps", [])):
                if gap.get("gap_id") == gap_id:
                    gap_index = i
                    break
            
            if gap_index == -1:
                raise ValueError(f"Gap with ID {gap_id} not found in report {report_id}")

            # Update the searches for that gap using the found index
            sql = """
                UPDATE researcher_reports
                SET report = jsonb_set(
                    report,
                    ARRAY[%s, 'searches'],
                    %s::jsonb
                )
                WHERE report_id = %s;
            """
            path = f"{{gaps,{gap_index}}}"
            cur.execute(sql, (path, Json(searches), report_id))
        conn.commit()

def db_update_curator_report(report_id: str, job: str, results: list):
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