# sub_agents.py
from deepagents.sub_agent import SubAgent
from langchain_openai.chat_models import ChatOpenAI
import os

def get_sub_agents(model: ChatOpenAI):
    """
    Initializes and returns a list of all sub-agents.
    """

    # 1. The Analyst Agent
    analyst_agent = SubAgent(
        name="Analyst",
        description="Identifies knowledge gaps and stale information in the knowledge base.",
        prompt="Your goal is to identify knowledge gaps and stale information in the knowledge base. Your first step is to query the knowledge base using your tools to understand the topics it currently covers. Then, analyze the results to find areas that are sparsely connected, have outdated information, or are missing recent developments. Finally, report the identified gaps as a structured list to the Orchestrator.",
        tools=["query", "graphs_get"],
        model=model,
    )

    # 2. The Researcher Agent
    researcher_agent = SubAgent(
        name="Researcher",
        description="Searches the internet for new, relevant sources.",
        prompt="Your goal is to find new, relevant sources to fill knowledge gaps. You will receive a list of topics from the Orchestrator. For each topic, you are limited to performing a maximum of 3 independent Google searches. From the combined results, you must identify and return no more than the top 5 most relevant URLs to the Orchestrator.",
        tools=["google_search"],
        model=model,
    )

    # 3. The Curator Agent
    curator_agent = SubAgent(
        name="Curator",
        description="Reviews new sources and decides what to ingest.",
        prompt="Your goal is to review and ingest new sources. You will receive a list of URLs from the Orchestrator. For each URL, fetch the content and evaluate its relevance and quality. For sources you approve, use your tools to ingest them into the knowledge base. You must monitor the ingestion process using the `documents_pipeline_status` tool until it is complete. Finally, report a summary of what was successfully ingested to the Orchestrator.",
        tools=["fetch", "documents_upload_file", "documents_upload_files", "documents_insert_text", "documents_pipeline_status"],
        model=model,
    )

    # 4. The Auditor Agent
    auditor_agent = SubAgent(
        name="Auditor",
        description="Reviews the knowledge base to identify data quality issues.",
        prompt="Your goal is to review the knowledge base to identify data quality issues. Scan the graph for duplicate entities, irregular normalization, messy relationships, and label inconsistencies. Your report should be concise and focus on the top 5-10 most critical data quality issues you discover. Produce this detailed report for the Orchestrator.",
        tools=["graphs_get", "query"],
        model=model,
    )

    # 5. The Fixer Agent
    fixer_agent = SubAgent(
        name="Fixer",
        description="Corrects the data quality issues identified by the Auditor.",
        prompt='''Your goal is to correct the data quality issues identified by the Auditor. 

You will be given a report of issues. First, you must create a detailed, step-by-step plan for how you will fix the issues. Your plan should address a manageable number of issues at a time, containing no more than 10 distinct correction steps. 

Then, you MUST use the `human_approval` tool to get permission to execute your plan. 

Do NOT make any changes until you have received approval. Once all approved changes are made, report a summary of the corrections to the Orchestrator.''',
        tools=["human_approval", "graph_update_entity", "documents_delete_entity", "graph_update_relation", "documents_delete_relation", "graph_entity_exists"],
        model=model,
    )

    # 6. The Advisor Agent
    advisor_agent = SubAgent(
        name="Advisor",
        description="Provides recommendations for systemic improvements.",
        prompt="Your goal is to provide recommendations for systemic improvements. Review the reports from the Auditor and Fixer to identify recurring error patterns. Based on these patterns, generate specific, actionable recommendations. Provide these recommendations in a clear, final report to the Orchestrator, focusing on the top 3-5 most impactful and actionable suggestions.",
        tools=["read_file"],
        model=model,
    )

    return [analyst_agent, researcher_agent, curator_agent, auditor_agent, fixer_agent, advisor_agent]
