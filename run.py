# run.py
import asyncio
import logging
import json
from datetime import datetime
import os
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
    logger.info("Initializing Knowledge Agent...")

    # 1. Fetch the tools from your running MCP server
    mcp_tools = await get_mcp_tools()

    # 2. Create the agent with the loaded tools
    knowledge_agent = create_knowledge_agent(mcp_tools, logger)

    # 3. Define the initial task for the agent
    initial_task = "Your task is to execute one full run of your maintenance and curation workflow. Begin now."

    logger.info(f"--- Sending initial task to agent ---", extra={'input': initial_task})

    # 4. Invoke the agent and stream the response
    async for chunk in knowledge_agent.astream(
        {"input": initial_task}
    ):
        # The agent's output will be logged by the agent itself
        pass

if __name__ == "__main__":
    asyncio.run(main())