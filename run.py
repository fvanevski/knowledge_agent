# run.py
import asyncio
import logging
import json
from datetime import datetime, timezone
import os
import argparse
import langchain
from langchain_openai.chat_models import ChatOpenAI
from knowledge_agent import get_mcp_tools, create_knowledge_agent_graph
from state import AgentState

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
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno
        }
        if hasattr(record, 'input'):
            log_record['input'] = record.input
        if hasattr(record, 'output'):
            log_record['output'] = record.output
        return json.dumps(log_record)

# Configure the logger
log_file = f"logs/knowledge_agent_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(JsonFormatter())

# Console logger for immediate feedback
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Get the root logger for this application
logger = logging.getLogger('KnowledgeAgent')
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Get the root logger for langchain and add our handler to it
langchain_logger = logging.getLogger('langchain')
langchain_logger.addHandler(file_handler)
langchain_logger.setLevel(logging.INFO) # Set level for langchain logger as well

# Enable verbose logging for LangChain to see the agent's thoughts
langchain.verbose = True

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
        mcp_tools = await get_mcp_tools()

        model = ChatOpenAI(
            model="openai/gpt-oss-20b",
            base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:8002/v1"),
        )
        
        app = create_knowledge_agent_graph(task)

        run_timestamp = datetime.now(timezone.utc).isoformat()

        initial_state = {
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