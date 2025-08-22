# run.py
import asyncio
import logging
import json
from datetime import datetime
import os
import argparse
from knowledge_agent import get_mcp_tools, create_knowledge_agent

# Create a logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Create a custom JSON formatter
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "agent_name": getattr(record, 'agent_name', 'orchestrator'),
            "message": record.getMessage(),
        }
        if hasattr(record, 'input'):
            log_record['input'] = record.input
        if hasattr(record, 'output'):
            log_record['output'] = record.output
        return json.dumps(log_record)

# Configure the logger
log_file = f"logs/knowledge_agent_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
handler = logging.FileHandler(log_file)
handler.setFormatter(JsonFormatter())

logger = logging.getLogger('KnowledgeAgent')
logger.setLevel(logging.INFO)
logger.addHandler(handler)


async def main():
    parser = argparse.ArgumentParser(description="Run the Knowledge Agent with a specific workflow.")
    parser.add_argument("--maintenance", action="store_true", help="Run the full maintenance workflow.")
    parser.add_argument("--analyze", action="store_true", help="Run the analysis workflow.")
    parser.add_argument("--research", action="store_true", help="Run the research workflow.")
    parser.add_argument("--curate", action="store_true", help="Run the curation workflow.")
    parser.add_argument("--audit", action="store_true", help="Run the audit workflow.")
    parser.add_argument("--fix", action="store_true", help="Run the fix workflow.")
    parser.add_argument("--advise", action="store_true", help="Run the advise workflow.")

    args = parser.parse_args()

    task = "maintenance"  # Default task
    if args.analyze:
        task = "analyze"
    elif args.research:
        task = "research"
    elif args.curate:
        task = "curate"
    elif args.audit:
        task = "audit"
    elif args.fix:
        task = "fix"
    elif args.advise:
        task = "advise"

    logger.info(f"Initializing Knowledge Agent for task: {task}...")

    try:
        # 1. Fetch the tools from your running MCP server
        mcp_tools = await get_mcp_tools()

        # 2. Create the agent with the loaded tools
        knowledge_agent = create_knowledge_agent(mcp_tools, logger, task)

        # 3. Define the initial task for the agent
        initial_task = f"Your task is to execute the {task} workflow. Begin now."

        logger.info(f"--- Sending initial task to agent ---", extra={'input': initial_task})

        # 4. Invoke the agent and stream the response
        async for chunk in knowledge_agent.astream(
            {"input": initial_task}
        ):
            # The agent's output will be logged by the agent itself
            pass
    finally:
        logging.shutdown()

if __name__ == "__main__":
    asyncio.run(main())