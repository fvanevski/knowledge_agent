# state.py
from typing import TypedDict, List

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