# run.py
import asyncio
from knowledge_agent import get_mcp_tools, create_knowledge_agent

async def main():
    print("Initializing Knowledge Agent...")
    
    # 1. Fetch the tools from your running MCP server
    mcp_tools = await get_mcp_tools()
    
    # 2. Create the agent with the loaded tools
    knowledge_agent = create_knowledge_agent(mcp_tools)

    # 3. Define the initial task for the agent
    initial_task = "Your task is to execute one full run of your maintenance and curation workflow. Begin now."
    
    print(f"\n--- Sending initial task to agent ---\nTask: {initial_task}\n")
    
    # 4. Invoke the agent and stream the response
    async for chunk in knowledge_agent.astream(
        {"input": initial_task}
    ):
        print(chunk)

if __name__ == "__main__":
    asyncio.run(main())
