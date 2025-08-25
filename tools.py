# tools.py
from langchain_core.tools import tool, ToolException

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
    print(f"\n[INFO] {status}")
    logger.info(f"{status}")
    try:        
        response = input("Do you approve this plan? (y/n): ").lower()
        if response == 'y':
            status = "Approved."
            print(status)
            logger.info(status)
            return status
        status = "Denied."
        print(status)
        logger.info(status)
        return status
    except Exception as e:
        status = f"Error in human_approval: {e}"
        print(status)
        logger.error(status)
        raise ToolException(status)
