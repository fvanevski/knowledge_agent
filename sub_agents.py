# sub_agents.py
from langchain_openai.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import Tool
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import List

def create_sub_agent(llm: ChatOpenAI, tools: list, system_prompt: str):
    """Helper function to create a sub-agent."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

class ResearcherAgentArgs(BaseModel):
    topics: List[str] = Field(description="A list of topics or knowledge gaps to research.")

class CuratorAgentArgs(BaseModel):
    urls: List[str] = Field(description="A list of URLs to ingest.")

class FixerAgentArgs(BaseModel):
    auditor_report: str = Field(description="The detailed report from the Auditor identifying data quality issues.")

class AdvisorAgentArgs(BaseModel):
    auditor_report: str = Field(description="The report from the Auditor.")
    fixer_report: str = Field(description="The report from the Fixer.")

def get_sub_agent_tools(all_tools: list, model: ChatOpenAI):
    """Initializes and returns a list of all sub-agents as tools."""

    # Filter tools for each agent
    analyst_tools = [t for t in all_tools if t.name in ["query", "graphs_get"]]
    researcher_tools = [t for t in all_tools if t.name == "google_search"]
    curator_tools = [t for t in all_tools if t.name in ["fetch", "documents_upload_file", "documents_upload_files", "documents_insert_text", "documents_pipeline_status"]]
    auditor_tools = [t for t in all_tools if t.name in ["graphs_get", "query"]]
    fixer_tools = [t for t in all_tools if t.name in ["human_approval", "graph_update_entity", "documents_delete_entity", "graph_update_relation", "documents_delete_relation", "graph_entity_exists"]]
    advisor_tools = [t for t in all_tools if t.name == "read_file"]

    # 1. The Analyst Agent Tool
    analyst_prompt = '''Your goal is to perform a comprehensive analysis of the LightRAG knowledge base and identify high-value knowledge gaps. You must follow this specific workflow:

1.  **Step 1: Discover Existing Topics.** Your first action is to get a high-level overview of the knowledge base. Use your `graph_labels` tool to retrieve all existing topic labels. If needed, use the `query` tool with broad queries to understand the main subject matter.
2.  **Step 2: Create a Thematic Summary.** Take the raw list of topics from Step 1 and synthesize it. Group the topics into 5-10 high-level themes or categories to form a clear picture of what the knowledge base is about.
3.  **Step 3: Identify Knowledge Gaps.** Based on your thematic summary, critically reason about what is missing. Consider these types of gaps:
    *   **Temporal Gaps:** Are there topics that are clearly outdated (e.g., policies from 2 years ago, technologies that have been superseded)?
    *   **Logical Gaps:** Are there missing logical components of a topic (e.g., the KB has 'user authentication' but not 'user authorization')?
    *   **Comparative Gaps:** Does the KB cover one technology (e.g., 'React') but lack information on its major alternatives (e.g., 'Vue', 'Svelte')?
4.  **Step 4: Produce a Report.** Consolidate your findings into a structured list of the most important gaps. Each item in the list should clearly state the missing topic. This report will be passed to the Researcher, so it must be clear and actionable.

You must base your analysis exclusively on the output of your tools. Do not use your general knowledge to fill in blanks; if the tools return no information, report that.'''
    analyst_agent = create_sub_agent(model, analyst_tools, analyst_prompt)
    analyst_tool = Tool(
        name="analyst_agent",
        func=lambda input_str: analyst_agent.invoke({"input": input_str}),
        coroutine=lambda input_str: analyst_agent.ainvoke({"input": input_str}),
        description="Use this agent to identify knowledge gaps and stale information in the knowledge base. Provide a clear instruction as input."
    )

    # 2. The Researcher Agent Tool
    researcher_prompt = "Your goal is to find new, relevant sources to fill knowledge gaps. You will receive a list of topics from the Orchestrator. For each topic, you are limited to performing a maximum of 3 independent Google searches. From the combined results, you must identify and return no more than the top 5 most relevant URLs to the Orchestrator."
    researcher_agent = create_sub_agent(model, researcher_tools, researcher_prompt)
    researcher_tool = Tool.from_function(
        name="researcher_agent",
        description="Use this agent to search the internet for new, relevant sources for a given list of topics.",
        func=lambda topics: researcher_agent.invoke({"input": f"Research the following topics: {topics}"}),
        coroutine=lambda topics: researcher_agent.ainvoke({"input": f"Research the following topics: {topics}"}),
        args_schema=ResearcherAgentArgs
    )

    # 3. The Curator Agent Tool
    curator_prompt = '''Your goal is to review and ingest new sources into the LightRAG knowledge base. You will receive a list of URLs from the Orchestrator. For each URL, fetch the content and evaluate its relevance. For sources you approve, use your assigned tools to ingest them via the lightrag_mcp server. You must monitor the ingestion process using the `documents_pipeline_status` tool until it is complete. Finally, report a summary of what was successfully ingested to the Orchestrator.'''
    curator_agent = create_sub_agent(model, curator_tools, curator_prompt)
    curator_tool = Tool.from_function(
        name="curator_agent",
        description="Use this agent to review and ingest new sources from a list of URLs.",
        func=lambda urls: curator_agent.invoke({"input": f"Ingest the following URLs: {urls}"}),
        coroutine=lambda urls: curator_agent.ainvoke({"input": f"Ingest the following URLs: {urls}"}),
        args_schema=CuratorAgentArgs
    )

    # 4. The Auditor Agent Tool
    auditor_prompt = "Your goal is to review the LightRAG knowledge base to identify data quality issues. You must use your assigned tools (`graphs_get`, `query`) to scan the graph for duplicate entities, irregular normalization, messy relationships, and label inconsistencies. Your report should be concise and focus on the top 5-10 most critical data quality issues you discover. Produce this detailed report for the Orchestrator."
    auditor_agent = create_sub_agent(model, auditor_tools, auditor_prompt)
    auditor_tool = Tool(
        name="auditor_agent",
        func=lambda input_str: auditor_agent.invoke({"input": input_str}),
        coroutine=lambda input_str: auditor_agent.ainvoke({"input": input_str}),
        description="Use this agent to review the knowledge base and identify data quality issues. Provide a clear instruction as input."
    )

    # 5. The Fixer Agent Tool
    fixer_prompt = '''Your goal is to correct data quality issues in the LightRAG knowledge base. You will be given a report of issues from the Auditor. First, create a detailed, step-by-step plan for how you will fix the issues using your assigned lightrag_mcp server tools. Your plan should address a manageable number of issues at a time, containing no more than 10 distinct correction steps. 

Then, you MUST use the `human_approval` tool to get permission to execute your plan. 

Do NOT make any changes until you have received approval. Once all approved changes are made, report a summary of the corrections to the Orchestrator.'''
    fixer_agent = create_sub_agent(model, fixer_tools, fixer_prompt)
    fixer_tool = Tool.from_function(
        name="fixer_agent",
        description="Use this agent to correct data quality issues based on a report from the Auditor.",
        func=lambda auditor_report: fixer_agent.invoke({"input": auditor_report}),
        coroutine=lambda auditor_report: fixer_agent.ainvoke({"input": auditor_report}),
        args_schema=FixerAgentArgs
    )

    # 6. The Advisor Agent Tool
    advisor_prompt = "Your goal is to provide recommendations for systemic improvements. Review the reports from the Auditor and Fixer to identify recurring error patterns. Based on these patterns, generate specific, actionable recommendations. Provide these recommendations in a clear, final report to the Orchestrator, focusing on the top 3-5 most impactful and actionable suggestions."
    advisor_agent = create_sub_agent(model, advisor_tools, advisor_prompt)
    advisor_tool = Tool.from_function(
        name="advisor_agent",
        description="Use this agent to provide recommendations for systemic improvements based on reports from the Auditor and Fixer.",
        func=lambda auditor_report, fixer_report: advisor_agent.invoke({"input": f"Auditor Report:\n{auditor_report}\n\nFixer Report:\n{fixer_report}"}),
        coroutine=lambda auditor_report, fixer_report: advisor_agent.ainvoke({"input": f"Auditor Report:\n{auditor_report}\n\nFixer Report:\n{fixer_report}"}),
        args_schema=AdvisorAgentArgs
    )

    return [analyst_tool, researcher_tool, curator_tool, auditor_tool, fixer_tool, advisor_tool]
