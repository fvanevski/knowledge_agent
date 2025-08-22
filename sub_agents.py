# sub_agents.py
from langchain_openai.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import Tool
from langchain_core.tools import tool, ToolException
from pydantic import BaseModel, Field
from typing import Dict, List
import logging
import asyncio
import json
import os

def create_sub_agent(llm: ChatOpenAI, tools: list, system_prompt: str, logger: logging.Logger, agent_name: str):
    """Helper function to create a sub-agent with structured logging."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_openai_tools_agent(llm, tools, prompt)
    
    # Create a child logger for the sub-agent
    sub_agent_logger = logger.getChild(agent_name)

    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Wrapper to log inputs and outputs
    async def logged_ainvoke(input_data):
        sub_agent_logger.info(f"Invoking agent", extra={'input': json.dumps(input_data), 'agent_name': agent_name})
        try:
            result = await agent_executor.ainvoke({"input": input_data})
            sub_agent_logger.info(f"Agent finished successfully", extra={'output': result, 'agent_name': agent_name})
            return result
        except ToolException as e:
            error_message = f"The tool failed with the following error: {e}. Please try a different tool or a modified call."
            sub_agent_logger.error(error_message, exc_info=True, extra={'agent_name': agent_name})
            return {"error": error_message}
        except Exception as e:
            sub_agent_logger.error(f"Agent failed with an unexpected exception: {e}", exc_info=True, extra={'agent_name': agent_name})
            raise

    return logged_ainvoke

class ResearcherAgentArgs(BaseModel):
    topics: List[str] = Field(description="A list of topics or knowledge gaps to research.")

class CuratorAgentArgs(BaseModel):
    research_report: Dict[str, List[str]] = Field(description="A dictionary where keys are topics (preserving the full context of the knowledge gap) and values are lists of URLs to consider for ingestion.")

class FixerAgentArgs(BaseModel):
    auditor_report: str = Field(description="The detailed report from the Auditor identifying data quality issues.")

class AdvisorAgentArgs(BaseModel):
    auditor_report: str = Field(description="The report from the Auditor.")
    fixer_report: str = Field(description="The report from the Fixer.")

@tool
def save_report(report: str, filename: str):
    """Saves a report to a file in the state directory, appending to a list of entries."""
    filepath = f"state/{filename}"
    entries = []
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        with open(filepath, "r") as f:
            entries = json.load(f)
    entries.append(report)
    with open(filepath, "w") as f:
        json.dump(entries, f, indent=4)
    return f"Successfully saved report to {filename}"

@tool
def load_report(filename: str) -> str:
    """Loads the most recent report from a file in the state directory."""
    filepath = f"state/{filename}"
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return "No report found."
    with open(filepath, "r") as f:
        entries = json.load(f)
    return entries[-1]

def get_sub_agent_tools(all_tools: list, model: ChatOpenAI, logger: logging.Logger, task: str):
    """Initializes and returns a list of all sub-agents as tools."""

    # Filter tools for each agent
    analyst_tools = [t for t in all_tools if t.name in ["query", "graphs_get", "graph_labels"]]
    researcher_tools = [t for t in all_tools if t.name == "google_search"]
    curator_tools = [t for t in all_tools if t.name in ["fetch", "documents_upload_file", "documents_upload_files", "documents_insert_text", "documents_pipeline_status"]]
    auditor_tools = [t for t in all_tools if t.name in ["graphs_get", "query"]]
    fixer_tools = [t for t in all_tools if t.name in ["human_approval", "graph_update_entity", "documents_delete_entity", "graph_update_relation", "documents_delete_relation", "graph_entity_exists"]]
    advisor_tools = [t for t in all_tools if t.name in ["list_allowed_directories", "list_directory", "search_files", "read_text_file", "read_wiki_structure", "read_wiki_contents", "ask_question"]]

    # 1. The Analyst Agent Tool
    analyst_prompt = '''Your goal is to perform a comprehensive analysis of the LightRAG knowledge base (KB) and identify high-value knowledge gaps. You must follow this specific workflow:

1.  **Step 1: Discover Existing Topics.** Use your available tools to get a high-level overview of the knowledge base.
2.  **Step 2: Create a Thematic Summary.** Synthesize the topics into 5-10 high-level themes.
3.  **Step 3: Identify Knowledge Gaps.** Based on your summary, identify temporal or logical gaps.
4.  **Step 4: Formulate Research Topics.** For each gap, formulate a specific, context-rich research topic. For example, if a gap is "outdated information on Topic A," the research topic should be "updated information on Topic A after <date>."
5.  **Step 5: Produce a Report.** Consolidate your findings into a structured list of research topics to be passed to the Researcher.
6.  **Step 6: Return the Report.** Return the report to the Orchestrator.

You must base your analysis exclusively on the output of your tools. Do not use your general knowledge.'''
    analyst_agent = create_sub_agent(model, analyst_tools, analyst_prompt, logger, 'analyst_agent')
    analyst_tool = Tool(
        name="analyst_agent",
        func=lambda input_str: asyncio.run(analyst_agent(input_str)),
        coroutine=analyst_agent,
        description="Use this agent to identify knowledge gaps and stale information in the LightRAG knowledge base (KB). Provide clear instructions as input."
    )

    # 2. The Researcher Agent Tool
    researcher_prompt = '''Your goal is to find new, relevant sources for a given list of research topics. You must follow this specific workflow:

1.  **Step 1: Research Topics.** For each topic you receive, perform up to 4 independent Google searches to find the most relevant URLs.
2.  **Step 2: Produce a Report.** Consolidate your findings into a dictionary where the keys are the research topics and the values are **a flat list of URL strings**.

        **Example of the correct output format:**
        ```json
        {{
          "topic 1": [
            "https://example.com/url1",
            "https://example.com/url2"
          ],
          "topic 2": [
            "https://example.com/url3",
            "https://example.com/url4"
          ]
        }}
        ```
3.  **Step 3: Return the Report.** Return the report to the Orchestrator.

You must base your analysis exclusively on the output of your tools. Do not use your general knowledge.'''
    researcher_agent = create_sub_agent(model, researcher_tools, researcher_prompt, logger, 'researcher_agent')
    researcher_tool = Tool.from_function(
        name="researcher_agent",
        description="Use this agent to search the internet for new, relevant sources for a given list of topics.",
        func=lambda **kwargs: asyncio.run(researcher_agent(kwargs)),
        coroutine=researcher_agent,
        args_schema=ResearcherAgentArgs
    )

    # 3. The Curator Agent Tool
    curator_prompt = '''Your goal is to review and ingest new sources into the LightRAG knowledge base. You will receive a research report from the Orchestrator containing topics and associated URLs. You must follow this specific workflow:

1.  **Step 1: Process URLs.** For each topic in the research report, iterate through the list of URLs.
2.  **Step 2: Fetch and Evaluate.** For each URL, try to fetch the content.
        *   **If the fetch is successful,** evaluate the content for relevance.
        *   **If the fetch fails,** log the error, discard the URL, and continue to the next one.
3.  **Step 3: Ingest Approved Sources.** Ingest all the sources that were successfully fetched and evaluated.
4.  **Step 4: Report Ingestion Results.** Report a summary of what was successfully ingested and a list of any URLs that failed.

You must base your analysis exclusively on the output of your tools. Do not use your general knowledge.'''
    curator_agent = create_sub_agent(model, curator_tools, curator_prompt, logger, 'curator_agent')
    curator_tool = Tool.from_function(
        name="curator_agent",
        description="Use this agent to review and ingest new sources from a research report containing topics and URLs.",
        func=lambda **kwargs: asyncio.run(curator_agent(kwargs)),
        coroutine=curator_agent,
        args_schema=CuratorAgentArgs
    )

    # 4. The Auditor Agent Tool
    auditor_prompt = '''Your goal is to review the LightRAG knowledge base to identify data quality issues. You must follow this specific workflow:

1.  **Step 1: Identify data quality issues.** Use your assigned lightrag_mcp server tools (`graphs_get`, `query`) to scan the graph for duplicate entities, irregular normalization, messy relationships, and label inconsistencies.
2.  **Step 2: Generate Report of findings.** Generate a report of your findings. Your report should be concise and focus on the top 5-10 most critical data quality issues you discover.
3.  **Step 3: Report findings.** Upon task completion, return this detailed report to the Orchestrator.

You must base your analysis exclusively on the output of your tools. Do not use your general knowledge to fill in blanks; if the tools return no information, report that.'''
    auditor_agent = create_sub_agent(model, auditor_tools, auditor_prompt, logger, 'auditor_agent')
    auditor_tool = Tool(
        name="auditor_agent",
        func=lambda input_str: asyncio.run(auditor_agent(input_str)),
        coroutine=auditor_agent,
        description="Use this agent to review the knowledge base and identify data quality issues. Provide a clear instruction as input."
    )

    # 5. The Fixer Agent Tool
    fixer_prompt = '''Your goal is to correct data quality issues based on a report from the Auditor. You must follow this specific workflow:

1.  **Step 1: Analyze the Auditor's Report.** If the report indicates no issues were found, your task is complete. Return a message to the Orchestrator stating that no actions were taken.
2.  **Step 2: Create a Fixing Plan.** If the report identifies issues, create a detailed, step-by-step plan to correct them using your available tools.
3.  **Step 3: Get Human Approval.** Present your plan to a human for approval using the `human_approval` tool.
4.  **Step 4: Execute the Plan.** Once approved, execute the plan.
5.  **Step 5: Report Corrections.** Report a summary of the corrections to the Orchestrator.

You must base your analysis exclusively on the output of your tools. Do not use your general knowledge.'''
    fixer_agent = create_sub_agent(model, fixer_tools, fixer_prompt, logger, 'fixer_agent')
    fixer_tool = Tool.from_function(
        name="fixer_agent",
        description="Use this agent to correct data quality issues based on a report from the Auditor.",
        func=lambda **kwargs: asyncio.run(fixer_agent(kwargs)),
        coroutine=fixer_agent,
        args_schema=FixerAgentArgs
    )

    # 6. The Advisor Agent Tool
    advisor_prompt = '''Your goal is to provide recommendations for systemic improvements. You will be provided with reports from the Auditor and Fixer to identify recurring error patterns. You must follow this specific workflow:

1.  **Step 1: Analyze Reports.** Carefully review the reports from the Auditor and Fixer to identify key themes and recurring issues.
2.  **Step 2: Generate Recommendations.** Based on these patterns, generate specific, actionable recommendations. You can read files from the LighRAG knowledge base instance using the `file_read` tool and get up-to-date documentation/answers from the LightRAG github repository (HKUDS/LightRAG) using the `read_wiki_structure`, `read_wiki_contents`, and `ask_question` tools to inform your suggestions.
    *   **Ingestion Prompts:** Consider how the ingestion prompts contained in the `/workspace/LightRAG/lightrag/prompt.py` file can be revised to better handle node generation, entity naming, avoiding duplicates, establishing useful and relevant relationships, and other relevant aspects.
    *   **Server Configuration:** Review the server configuration settings (e.g., chunk size, chunk overlap, token limits, etc.) in the `/workspace/LightRAG/.env` file to ensure optimal performance and resource allocation for the LightRAG instance, taking into consideration factors such as use of local models (MXFP4-quantized gpt-oss-20b for the LLM, bge-m3-GGUF/bge-m3-Q6_K.gguf for text embedding, and bge-reranker-v2-m3-GGUF/bge-reranker-v2-m3-Q6_K.gguf for reranking) and GPU resources (Nvidia RTX 3090 with 24GB VRAM).
3.  **Step 3: Compile Final Report.** Provide these recommendations in a clear, final report, focusing on the top 3-5 most impactful and actionable suggestions.
4.  **Step 4: Report Recommendations.** Upon task completion, return the final report to the Orchestrator.

You must base your analysis exclusively on the output of your tools. Do not use your general knowledge to fill in blanks; if the tools return no information, report that.'''
    advisor_agent = create_sub_agent(model, advisor_tools, advisor_prompt, logger, 'advisor_agent')
    advisor_tool = Tool.from_function(
        name="advisor_agent",
        description="Use this agent to provide recommendations for systemic improvements based on reports from the Auditor and Fixer.",
        func=lambda **kwargs: asyncio.run(advisor_agent(kwargs)),
        coroutine=advisor_agent,
        args_schema=AdvisorAgentArgs
    )

    if task == "maintenance":
        return [analyst_tool, researcher_tool, curator_tool, auditor_tool, fixer_tool, advisor_tool, save_report, load_report]
    elif task == "analyze":
        return [analyst_tool, save_report]
    elif task == "research":
        return [researcher_tool, load_report, save_report]
    elif task == "curate":
        return [curator_tool, load_report]
    elif task == "audit":
        return [auditor_tool, save_report]
    elif task == "fix":
        return [fixer_tool, load_report, save_report]
    elif task == "advise":
        return [advisor_tool, load_report]
    else:
        return []
