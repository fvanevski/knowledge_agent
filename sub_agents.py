# sub_agents.py
from langchain_openai.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import Tool
from pydantic import BaseModel, Field
from typing import Dict, List

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
    research_report: Dict[str, List[str]] = Field(description="A dictionary where keys are topics (preserving the full context of the knowledge gap) and values are lists of URLs to consider for ingestion.")

class FixerAgentArgs(BaseModel):
    auditor_report: str = Field(description="The detailed report from the Auditor identifying data quality issues.")

class AdvisorAgentArgs(BaseModel):
    auditor_report: str = Field(description="The report from the Auditor.")
    fixer_report: str = Field(description="The report from the Fixer.")

def get_sub_agent_tools(all_tools: list, model: ChatOpenAI):
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

1.  **Step 1: Discover Existing Topics.** Your first action is to get a high-level overview of the knowledge base. Use your `graph_labels` tool to retrieve all existing topic labels. If needed, use the `query` tool with broad queries to understand the main subject matter.
2.  **Step 2: Create a Thematic Summary.** Take the raw list of topics from Step 1 and synthesize it. Group the topics into 5-10 high-level themes or categories to form a clear picture of what the knowledge base is about.
3.  **Step 3: Identify Knowledge Gaps.** Based on your thematic summary, critically reason about what is missing. Consider these types of gaps:
    *   **Temporal Gaps:** Are there topics that are clearly outdated (including, but not limited to or requiring, sources dated prior to 1-2 years ago, information that has been superseded, etc.)?
    *   **Logical/Comparative Gaps:** Are there missing logical or comparative components of a topic (e.g., the KB has 'congressional factors' but not 'judicial factors', or has 'Democrat response' but not 'Republican (aka GOP) response')?
4.  **Step 4: Produce a Report.** Consolidate your findings into a structured list of the most important gaps. Each item in the list should clearly state the missing topic. This report will be passed to a dedicated Researcher, so it must be clear and actionable.
5.  **Step 5: Return the Report.** Upon task completion, return the report to the Orchestrator.

You must base your analysis exclusively on the output of your tools. Do not use your general knowledge to fill in blanks; if the tools return no information, report that.'''
    analyst_agent = create_sub_agent(model, analyst_tools, analyst_prompt)
    analyst_tool = Tool(
        name="analyst_agent",
        func=lambda input_str: analyst_agent.invoke({"input": input_str}),
        coroutine=lambda input_str: analyst_agent.ainvoke({"input": input_str}),
        description="Use this agent to identify knowledge gaps and stale information in the LightRAG knowledge base (KB). Provide clear instructions as input."
    )

    # 2. The Researcher Agent Tool
    researcher_prompt = '''Your goal is to find new, relevant sources to fill knowledge gaps. You will receive a list of topics from the Orchestrator. You must follow this specific workflow:

1.  **Step 1: Establish list of topics.** Review the list of knowledge gaps provided by the Orchestrator. For each gap, formulate a specific research topic that preserves the full context of the gap. For example, if the gap is "outdated information on Topic A," the research topic should be "updated information on Topic A" or "information on Topic A after <date>."
2.  **Step 2: Research topics.** For each topic in the list you established, perform a maximum of 4 independent Google searches using the `google_search` tool.
    *   **Initial general query:** Perform a broad Google search for the topic to get a sense of the landscape of information available. The date restriction contraints can be relaxed somewhat for this initial broad query.
    *   **Focused queries:** Based on the initial results, perform up to 3 more targeted searches to find specific information related to the topic. Use date restriction, subject matter, and source parameters of the `google_search` tool to filter results as appropriate.
    *   **Select top results:** From the combined results, you must identify and select no more than the top 5 most relevant URLs for the topic to return to the Orchestrator.
3.  **Step 3: Produce a report.** Consolidate your findings into a structured report as a dictionary where the keys are the context-rich topics you researched and the values are the lists of URLs you selected for each topic. This report will be passed to a dedicated Curator, so it must be clear and actionable.
4.  **Step 4: Return the Report.** Upon task completion, return the report to the Orchestrator.

You must base your analysis exclusively on the output of your tools. Do not use your general knowledge to fill in blanks; if the tools return no information, report that.'''
    researcher_agent = create_sub_agent(model, researcher_tools, researcher_prompt)
    researcher_tool = Tool.from_function(
        name="researcher_agent",
        description="Use this agent to search the internet for new, relevant sources for a given list of topics.",
        func=lambda topics: researcher_agent.invoke({"input": f"Research the following topics: {topics}"}),
        coroutine=lambda topics: researcher_agent.ainvoke({"input": f"Research the following topics: {topics}"}),
        args_schema=ResearcherAgentArgs
    )

    # 3. The Curator Agent Tool
    curator_prompt = '''Your goal is to review and ingest new sources into the LightRAG knowledge base. You will receive a research report from the Orchestrator containing topics and associated URLs. You must follow this specific workflow:

1.  **Step 1: Establish list of URLs.** Review the research report provided by the Orchestrator. For each topic, generate a list of URLs to fetch using the `fetch` tool, noting for each URL its associated topic.
2.  **Step 2: Fetch and evaluate content.** For each URL, fetch the content (all or partial if sufficient to make a determination) using the `fetch` tool and evaluate its relevance in relation to its associated topic, making a determination of whether or not to ingest. If you encounter an error (e.g., a 403 Forbidden error) while fetching a URL, you should log the error and the URL that caused it, and then continue to the next URL.
3.  **Step 3: Ingest approved sources.** For sources you approve for ingestion, use your assigned tools to ingest them via the lightrag_mcp server. You must monitor the ingestion process using the `documents_pipeline_status` tool until it is complete.
4.  **Step 4: Report ingestion results.** Finally, report a summary of what was successfully ingested to the Orchestrator.

You must base your analysis exclusively on the output of your tools. Do not use your general knowledge to fill in blanks; if the tools return no information, report that.'''
    curator_agent = create_sub_agent(model, curator_tools, curator_prompt)
    curator_tool = Tool.from_function(
        name="curator_agent",
        description="Use this agent to review and ingest new sources from a research report containing topics and URLs.",
        func=lambda research_report: curator_agent.invoke({"input": f"Research Report:\n{research_report}"}),
        coroutine=lambda research_report: curator_agent.ainvoke({"input": f"Research Report:\n{research_report}"}),
        args_schema=CuratorAgentArgs
    )

    # 4. The Auditor Agent Tool
    auditor_prompt = '''Your goal is to review the LightRAG knowledge base to identify data quality issues. You must follow this specific workflow:

1.  **Step 1: Identify data quality issues.** Use your assigned lightrag_mcp server tools (`graphs_get`, `query`) to scan the graph for duplicate entities, irregular normalization, messy relationships, and label inconsistencies.
2.  **Step 2: Generate Report of findings.** Generate a report of your findings. Your report should be concise and focus on the top 5-10 most critical data quality issues you discover.
3.  **Step 3: Report findings.** Upon task completion, return this detailed report to the Orchestrator.

You must base your analysis exclusively on the output of your tools. Do not use your general knowledge to fill in blanks; if the tools return no information, report that.'''
    auditor_agent = create_sub_agent(model, auditor_tools, auditor_prompt)
    auditor_tool = Tool(
        name="auditor_agent",
        func=lambda input_str: auditor_agent.invoke({"input": input_str}),
        coroutine=lambda input_str: auditor_agent.ainvoke({"input": input_str}),
        description="Use this agent to review the knowledge base and identify data quality issues. Provide a clear instruction as input."
    )

    # 5. The Fixer Agent Tool
    fixer_prompt = '''Your goal is to correct data quality issues in the LightRAG knowledge base. You will be given a report of issues from the Auditor. You must follow this specific workflow:

1.  **Step 1: Create Fixing Plan.** First, create a detailed, step-by-step plan for how you will fix the issues using your assigned lightrag_mcp server tools (e.g., `graph_update_entity`, `documents_delete_entity`, `graph_update_relation`, `documents_delete_relation`, `graph_entity_exists`). Your plan should address a manageable number of issues at a time, containing no more than 10 distinct correction steps.
2.  **Step 2: Get Human Approval.** Next, present your fixing plan to a human reviewer for approval. You must use the `human_approval` tool to facilitate this process.
    *   **You MUST use the `human_approval` tool to get permission to execute your plan.** Do NOT make any changes until you have received approval.
3.  **Step 3: Execute Fixing Plan.** Once you have received approval, execute your fixing plan using the assigned lightrag_mcp server tools (e.g., `graph_update_entity`, `documents_delete_entity`, `graph_update_relation`, `documents_delete_relation`, `graph_entity_exists`).
4.  **Step 4: Report Corrections.** Once all approved changes are made, report a summary of the corrections to the Orchestrator.

You must base your analysis exclusively on the output of your tools. Do not use your general knowledge to fill in blanks; if the tools return no information, report that.'''

    fixer_agent = create_sub_agent(model, fixer_tools, fixer_prompt)
    fixer_tool = Tool.from_function(
        name="fixer_agent",
        description="Use this agent to correct data quality issues based on a report from the Auditor.",
        func=lambda auditor_report: fixer_agent.invoke({"input": auditor_report}),
        coroutine=lambda auditor_report: fixer_agent.ainvoke({"input": auditor_report}),
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
    advisor_agent = create_sub_agent(model, advisor_tools, advisor_prompt)
    advisor_tool = Tool.from_function(
        name="advisor_agent",
        description="Use this agent to provide recommendations for systemic improvements based on reports from the Auditor and Fixer.",
        func=lambda auditor_report, fixer_report: advisor_agent.invoke({"input": f"Auditor Report:\n{auditor_report}\n\nFixer Report:\n{fixer_report}"}),
        coroutine=lambda auditor_report, fixer_report: advisor_agent.ainvoke({"input": f"Auditor Report:\n{auditor_report}\n\nFixer Report:\n{fixer_report}"}),
        args_schema=AdvisorAgentArgs
    )

    return [analyst_tool, researcher_tool, curator_tool, auditor_tool, fixer_tool, advisor_tool]
