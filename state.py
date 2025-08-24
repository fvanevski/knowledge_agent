# state.py
from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """
    Represents the state of the agent graph.
    The `messages` field is the primary channel for agent communication.
    The `Annotated` type with `operator.add` ensures that new messages are
    appended to the list, rather than overwriting it.
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

    # Fields for the researcher agent's stateful workflow
    researcher_report_id: Optional[str]
    researcher_gaps_todo: Optional[List[dict]]
    researcher_current_gap: Optional[dict]
    researcher_gaps_complete: Optional[List[str]]