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
    initial_task = "Start your workflow. Begin by understanding the existing lightrag knowledge base by querying it using the lightrag_mcp server and create a plan."
    
    print(f"\n--- Sending initial task to agent ---\nTask: {initial_task}\n")
    
    # 4. Invoke the agent and stream the response
    async for chunk in knowledge_agent.astream(
        {"messages": [{"role": "user", "content": initial_task}]},
        stream_mode="values"
    ):
        if "messages" in chunk:
            chunk["messages"][-1].pretty_print()

if __name__ == "__main__":
    asyncio.run(main())