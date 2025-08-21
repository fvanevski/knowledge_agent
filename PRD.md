# Product Requirements Document: Knowledge Agent

## 1\. Introduction & Vision

### 1.1. Vision

To create a sophisticated, autonomous AI agent—the "Knowledge Agent"—that proactively maintains, expands, and curates a local LightRAG knowledge base. This agent will transform the knowledge base from a static repository into a living, self-improving intelligence system, ensuring the information it contains is always accurate, relevant, and up-to-date.

### 1.2. Background

The user has a functioning local RAG setup powered by LightRAG, using Neo4j for the knowledge graph and local models for LLM and embedding tasks. Interaction with this system is enabled via a `lightrag_mcp` server. While powerful, the knowledge base is currently static; it only knows what has been manually ingested. This project aims to automate the entire knowledge lifecycle: from discovery and ingestion to curation and system improvement.

## 2\. Problem Statement

A manually curated knowledge base, even a sophisticated one, faces several challenges:

- **Staleness:** Information quickly becomes outdated without a process for continuous updates.

- **Incompleteness:** The knowledge base is limited to manually selected documents, creating information silos and knowledge gaps.

- **High Maintenance Overhead:** The manual effort required to find new sources, ingest them, and fix data quality issues is significant and does not scale.

- **Data Quality Degradation:** As more data is added, inconsistencies and duplicates can accumulate, reducing the reliability of RAG outputs and polluting the knowledge graph.

The Knowledge Agent is being built to solve these problems by automating the end-to-end maintenance and expansion workflow.

## 3\. Goals & Objectives

- **Primary Goal:** To successfully build and deploy an autonomous agent that can execute a multi-step workflow to improve and expand the local LightRAG instance.

- **Objective 1 (Automation):** Automate the process of discovering and ingesting new, relevant documents from the internet, reducing manual effort by over 90%.

- **Objective 2 (Data Quality):** Implement an automated curation workflow that can identify and resolve at least 80% of common data quality issues.

- **Objective 3 (Self-Improvement):** Create a feedback loop where the agent analyzes recurring extraction errors and suggests actionable improvements to the LightRAG system's configuration.

## 4\. System Architecture & Key Components

The Knowledge Agent will be built using a **multi-agent architecture**, where a primary **Orchestrator Agent** manages the overall workflow by delegating tasks to a team of specialized sub-agents.

- **Agent Framework:** The core logic will be built using **LangGraph** via the **`deepagents`** Python package.

- **Tool Providers (MCP Servers):** All agents will interact with the outside world and the knowledge base exclusively through tools provided by MCP servers:

  - **`lightrag_mcp` Server:** Provides tools for interacting with the local LightRAG instance.

  - **`google_search_mcp` Server:** Provides the `google_search` tool for web discovery.

- **Knowledge Base:** The target of all operations is the user's local **LightRAG** instance.

- **LLM & Models:** The agents' reasoning will be powered by the user's locally hosted `openai/gpt-oss-20b` model.

### 4.1. Agent Roles

- **Orchestrator Agent (The Main Agent):**

  - **Role:** The project manager. It holds the high-level plan and the overall state.

  - **Function:** It does not perform tasks itself. Instead, it analyzes the state, decides which task to do next, and invokes the appropriate sub-agent with a specific goal. It receives reports from sub-agents to update its plan and decide the next step.

- **Sub-Agent 1: The Analyst**

  - **Role:** Identifies knowledge gaps and stale information.

  - **Tools:** `query`, `graphs_get`.

  - **Function:** Queries the knowledge base to understand its current topics. It analyzes the graph to find areas that are sparsely connected or entities that haven't been updated recently, then reports these gaps to the Orchestrator.

- **Sub-Agent 2: The Researcher**

  - **Role:** Searches the internet for new, relevant sources.

  - **Tools:** `google_search`.

  - **Function:** Takes a list of knowledge gaps from the Orchestrator, generates targeted search queries, executes them, and returns a list of high-quality URLs for further processing.

- **Sub-Agent 3: The Curator**

  - **Role:** Reviews new sources and decides what to ingest.

  - **Tools:** `fetch` (from a generic MCP server), `documents_upload_file`, `documents_insert_text`, `documents_pipeline_status`.

  - **Function:** Fetches the content from the URLs provided by the Researcher. It uses its LLM to evaluate the content for relevance and utility. For approved sources, it uses the ingestion tools to add them to LightRAG and monitors the process until completion.

- **Sub-Agent 4: The Auditor**

  - **Role:** Reviews the knowledge base to identify data quality issues.

  - **Tools:** `graphs_get`, `query`.

  - **Function:** After new data is ingested, this agent scans the graph for common LightRAG ingestion issues, including:

    - **Duplicate Entities:** Multiple nodes for the same concept (e.g., "U.S.", "United States", "America").

    - **Irregular Normalization:** Inconsistent naming conventions (e.g., "EO 13950" vs. "Executive Order 13950").

    - **Messy Relationships:** Generic relationships (e.g., `:DIRECTED`) where a more specific one could be used, or relationships pointing to a non-canonical entity.

    - **Label Inconsistencies:** Variations in capitalization or naming for the same node type (e.g., `:Person` vs. `:person`).

  - It produces a detailed report of all identified issues for the Orchestrator.

- **Sub-Agent 5: The Fixer**

  - **Role:** Corrects the data quality issues identified by the Auditor.

  - **Tools:** `graph_update_entity`, `documents_delete_entity`, and other graph management tools.

  - **Function:** Takes the Auditor's report and executes a series of tool calls to correct the issues. For example, to merge duplicates, it would update one entity with the combined knowledge, remap all relationships, and then delete the redundant nodes.

- **Sub-Agent 6: The Advisor**

  - **Role:** Provides recommendations for systemic improvements.

  - **Tools:** `read_file` (from a filesystem MCP server to read `prompt.py`).

  - **Function:** Reviews the reports from the Auditor and Fixer to identify recurring error patterns. Based on these patterns, it generates specific, actionable recommendations for modifying the LightRAG `prompt.py` file or adjusting server settings (like chunk size) to prevent similar issues in the future.

## 5\. Core Features (Epics & User Stories)

### Epic 1: Orchestration and Planning

_As the Orchestrator Agent, I need to manage the entire workflow by delegating tasks to specialized sub-agents and tracking their progress._

- **User Story 1.1:** The Orchestrator can create an initial plan using its `write_todos` tool.

- **User Story 1.2:** The Orchestrator can invoke the **Analyst** sub-agent to identify knowledge gaps.

- **User Story 1.3:** Based on the Analyst's report, the Orchestrator can invoke the **Researcher** sub-agent with a list of topics to research.

- **User Story 1.4:** The Orchestrator can pass the Researcher's findings to the **Curator** sub-agent for ingestion.

- **User Story 1.5:** After ingestion, the Orchestrator can invoke the **Auditor** and then the **Fixer** sub-agents to perform data quality checks and corrections.

- **User Story 1.6:** Finally, the Orchestrator can invoke the **Advisor** sub-agent to generate systemic recommendations.

### Epic 2: Knowledge Curation via Sub-Agents

_As the Knowledge Agent system, I need to identify and correct data quality issues using a team of specialized sub-agents._

- **User Story 2.1:** The **Auditor** sub-agent can successfully identify duplicate entities, normalization issues, and messy relationships in the graph.

- **User Story 2.2:** The **Fixer** sub-agent can receive a report from the Auditor and use a sequence of `graph_update_entity` and `documents_delete_entity` calls to effectively merge duplicate nodes.

- **User Story 2.3:** The **Advisor** sub-agent can analyze the Fixer's actions and correctly identify the root cause in the ingestion configuration, suggesting a specific change to the `prompt.py` file.

## 6\. Milestones & Phased Rollout (MVP)

The project will be developed in phases, focusing on implementing the sub-agent architecture iteratively.

- **Phase 1 (MVP): Orchestration with Research & Ingestion):**

  - Implement the main **Orchestrator Agent**.

  - Implement the **Analyst**, **Researcher**, and **Curator** sub-agents.

  - **Goal:** Prove the agent can autonomously identify knowledge gaps, find new sources, and ingest them into LightRAG. The workflow will stop after ingestion.

- **Phase 2 (Semi-Autonomous Curation):**

  - Implement the **Auditor** and **Fixer** sub-agents.

  - The **Fixer** sub-agent will require human approval in the loop before executing destructive changes (merging or deleting entities).

  - **Goal:** Validate the agent's ability to identify and propose correct solutions for data quality issues in a safe environment.

- **Phase 3 (Fully Autonomous Operation):**

  - Remove the human approval step for the **Fixer** sub-agent.

  - Implement the **Advisor** sub-agent to complete the self-improvement feedback loop.

  - **Goal:** Achieve a fully autonomous, "set it and forget it" knowledge management system.

## 7\. Assumptions and Dependencies

- The local LightRAG server is running and accessible.

- The `lightrag_mcp` and `google_search_mcp` servers are correctly configured and can be launched by the `MultiServerMCPClient`.

- The local LLM (`openai/gpt-oss-20b`) is operational and can handle the complexity of the agent's reasoning prompts.

- The sub-agent architecture will effectively manage context and prevent performance degradation in the main Orchestrator agent.
