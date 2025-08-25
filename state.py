# state.py
from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """
    Represents the state of the agent graph.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    task: str
    status: str
    timestamp: str
    mcp_tools: List[any]
    model: any
    logger: any

    # Fields for the analyst agent's stateful workflow
    analyst_report_id: Optional[str]
    analyst_report: Optional[str]

    # Fields for the researcher agent's stateful workflow
    researcher_report_id: Optional[str]
    researcher_gaps_todo: Optional[List[dict]]
    researcher_gaps_complete: Optional[List[str]]
    researcher_report: Optional[str]


    # Fields for the curator agent's stateful workflow
    curator_report_id: Optional[str]
    curator_urls_for_ingestion: Optional[List[str]]
    curator_url_ingestion_status: Optional[List[dict]]
    curator_report: Optional[str]

    # Fields for the auditor agent's stateful workflow
    auditor_report_id: Optional[str]
    auditor_report: Optional[str]

    # Fields for the fixer agent's stateful workflow
    fixer_report_id: Optional[str]
    fixer_report: Optional[str]

    # Fields for the advisor agent's stateful workflow
    advisor_report_id: Optional[str]
    advisor_report: Optional[str]