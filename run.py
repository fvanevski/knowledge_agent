# run.py
import asyncio
import logging
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import argparse
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage
from knowledge_agent import get_mcp_tools, create_knowledge_agent_graph

# Create a custom JSON formatter
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno
        }
        return json.dumps(log_record)

# Create a logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure the logger
log_file = f"logs/knowledge_agent_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w"),
        logging.StreamHandler()
    ]
)

# Get a specific logger for our application's own messages
logger = logging.getLogger('KnowledgeAgent')


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
        # 1. Load tools asynchronously
        mcp_tools = await get_mcp_tools()

        model = ChatOpenAI(
            model="chat",
            base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:8002/v1"),
        )
        
        # 2. Pass tools into the graph creation function
        app = create_knowledge_agent_graph(task, mcp_tools)

        run_timestamp = datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()

        # 3. Initialize the state with the messages list and the first message
        initial_state = {
            "messages": [HumanMessage(content="Your task is to identify knowledge gaps in the LightRAG knowledge base. Begin now.")],
            "task": task,
            "status": f"Starting '{task}' workflow.",
            "timestamp": run_timestamp,
            "mcp_tools": mcp_tools,
            "model": model,
            "logger": logger
        }
        
        logger.info(f"--- Invoking graph for task: {task} ---")
        
        final_state = await app.ainvoke(initial_state)

        print("--- Workflow Complete ---")
        print(f"Final Status: {final_state['status']}")
        logger.info(f"--- Workflow finished with final status: {final_state['status']} ---")

    finally:
        logging.shutdown()

if __name__ == "__main__":
    asyncio.run(main())