# state.py
from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    """
    Represents the state of the agent graph.
    """
    task: str
    status: str
    timestamp: str
    mcp_tools: List[any]
    model: any
    logger: any
    # Fields for the researcher agent's stateful workflow
    researcher_report_id: Optional[str]
    researcher_gaps_todo: Optional[List[dict]]
    researcher_gaps_complete: Optional[List[str]]
