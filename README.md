# Knowledge Agent

An autonomous AI agent for intelligently updating, maintaining, and curating a [LightRAG](https://github.com/HKUDS/LightRAG) knowledge base.

## Table of Contents

- [About The Project](#about-the-project)
- [Architecture](#architecture)
  - [Frameworks and Libraries](#frameworks-and-libraries)
  - [Agent Roles](#agent-roles)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
  - [Workflows](#workflows)
- [Configuration](#configuration)
- [Prompts](#prompts)
- [Logging](#logging)
- [Database](#database)
- [Workflow Details](#workflow-details)

## About The Project

This project provides a sophisticated, autonomous AI agent—the "Knowledge Agent"—that proactively maintains, expands, and curates a local LightRAG knowledge base. It transforms the knowledge base from a static repository into a living, self-improving intelligence system, ensuring the information it contains is always accurate, relevant, and up-to-date.

The Knowledge Agent is designed to solve the challenges of maintaining a static knowledge base:

- **Staleness:** Information quickly becomes outdated without a process for continuous updates.
- **Incompleteness:** The knowledge base is limited to manually selected documents, creating information silos and knowledge gaps.
- **High Maintenance Overhead:** The manual effort required to find new sources, ingest them, and fix data quality issues is significant and does not scale.
- **Data Quality Degradation:** As more data is added, inconsistencies and duplicates can accumulate, reducing the reliability of RAG outputs and polluting the knowledge graph.

The agent now features a **robust document processing pipeline** that can fetch raw web content (including PDFs and HTML), generate clean markdown, and store it in a structured database for further analysis and summarization.

## Architecture

The Knowledge Agent uses a multi-agent architecture, where a primary **Orchestrator Agent** manages the overall workflow by delegating tasks to a team of specialized sub-agents.

```
+---------------------+
| Orchestrator Agent  |
+----------+----------+
           |
           v
+----------+----------+
|      Sub-Agents     |
+----------+----------+
           |
           v
+----------+----------+
|       MCP Servers   |
+---------------------+
```

- **Orchestrator (`Knowledge Agent`)**: The project manager. It holds the high-level plan and the overall state. It invokes the appropriate sub-agent for each task and handles the flow of information between them.
- **Sub-Agents**: A team of specialized agents, each with a specific role in the knowledge management lifecycle.
- **MCP Servers**: All agents interact with the outside world and the knowledge base exclusively through tools provided by MCP servers.

### Frameworks and Libraries

- **[LangChain](https://www.langchain.com/)**: A framework for developing applications powered by language models.
- **[LangGraph](https://langchain-ai.github.io/langgraph/)**: A library for building stateful, multi-agent applications with LLMs.
- **[langchain-mcp-adapters](https://github.com/intelligent-soft-works/langchain-mcp-adapters)**: Used for connecting to and using tools from MCP servers.
- **[ChatOpenAI](https://python.langchain.com/docs/integrations/chat/openai)**: The language model used for the agents.
- **[pydantic](https://pydantic-docs.helpmanual.io/)**: Used for data validation and settings management.
- **[psycopg2-binary](https://pypi.org/project/psycopg2-binary/)**: A PostgreSQL adapter for Python.
- **[python-dotenv](https://pypi.org/project/python-dotenv/)**: A library for managing environment variables.
- **[json-repair](https://pypi.org/project/json-repair/)**: A library for repairing malformed JSON.
- **[requests](https://pypi.org/project/requests/)**: A library for making HTTP requests to download web content.
- **[pdfplumber](https://pypi.org/project/pdfplumber/)**: A library for extracting text from PDF documents.
- **[Trafilatura](https://trafilatura.readthedocs.io/)**: A tool for fast and accurate extraction of main content from HTML.
- **[Playwright](https://playwright.dev/)**: A library for browser automation, used as a fallback for complex websites.
- **[beautifulsoup4](https://pypi.org/project/beautifulsoup4/)**: A library for parsing HTML content.
- **[html2text](https://pypi.org/project/html2text/)**: A library for converting HTML to markdown.
- **[tiktoken](https://github.com/openai/tiktoken)**: A tool for counting tokens to ensure content fits within the LLM's context window.

### Agent Roles

- **Analyst**: Identifies knowledge gaps and stale information in the knowledge base by analyzing its content and structure.
- **Researcher**: Acts as the primary research arm of the agent. It breaks down research tasks and manages the entire content acquisition pipeline:
  - **Planner**: Creates a strategic, diversified search plan using advanced search operators.
  - **Content Processor**: Uses a hybrid strategy to extract clean, reader-mode content. It first tries the fast and accurate `trafilatura` library, and if that fails to return quality content, it falls back to a full browser rendering with `Playwright` to handle complex, JavaScript-heavy sites.
  - **Refiner**: If the initial search plan is unsuccessful, the refiner adjusts the strategy to find the missing information.
  - **Summarizer**: Generates a concise summary from the clean markdown content. Before summarizing, the content is passed through a filter that truncates it to a safe token limit (16k) to ensure efficiency and prevent context window errors.
- **Curator**: Takes the URLs from the Researcher and decides which ones are relevant, then carries out ingestion of approved content into the knowledge base.
- **Auditor**: Scans the knowledge graph for data quality issues like duplicate entities, inconsistent naming, and messy relationships.
- **Fixer**: Corrects the data quality issues identified by the Auditor, with a human approval step for destructive operations.
- **Advisor**: Analyzes recurring error patterns and suggests improvements to the LightRAG system's configuration to prevent future issues.

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- A running [LightRAG](https://github.com/HKUDS/LightRAG) instance
- Running MCP servers for tools (e.g., Google Search)
- PostgreSQL database

### Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/fvanevski/knowledge-agent.git
    cd knowledge-agent
    ```

2. Install the dependencies using uv:

    ```sh
    uv sync
    ```

3. Set up the environment variables by creating a `.env` file in the root directory. You can use the `.env.example` file as a template.

4. Install Playwright's browser binaries:

    ```sh
    uv run python -m playwright install
    ```

## Usage

The Knowledge Agent is executed via the `run.py` script. You can specify different workflows using command-line arguments.

### Workflows

- **Full Maintenance (`--maintenance`)**: This is the default workflow and runs all the sub-agents in sequence to perform a full maintenance cycle on the knowledge base.

    ```sh
    uv run python run.py --maintenance
    ```

- **Analyze (`--analyze`)**: Identifies knowledge gaps and stale information.

    ```sh
    uv run python run.py --analyze
    ```

- **Research (`--research`)**: Finds new sources for the topics identified by the Analyst.

    ```sh
    uv run python run.py --research
    ```

- **Curate (`--curate`)**: Ranks search results and ingests approved new content into the knowledge base.

    ```sh
    uv run python run.py --curate
    ```

- **Audit (`--audit`)**: Reviews the knowledge base for data quality issues.

    ```sh
    uv run python run.py --audit
    ```

- **Fix (`--fix`)**: Corrects the data quality issues found by the Auditor.

    ```sh
    uv run python run.py --fix
    ```

- **Advise (`--advise`)**: Provides recommendations for systemic improvements.

    ```sh
    uv run python run.py --advise
    ```

## Configuration

The Knowledge Agent requires a `mcp.json` file in the root directory to configure the connection to the MCP tool servers. This file should contain the server configurations, for example:

```json
{
    "google_search": {
        "command": "uv",
        "args": ["run", "python", "google_search_mcp.py"],
        "cwd": "/workspace/mcp_servers/google_search_mcp",
        "transport": "stdio"
    },
    "lightrag": {
        "command": "uv",
        "args": ["run", "python", "lightrag_mcp.py"],
        "cwd": "/workspace/mcp_servers/lightrag_mcp",
        "transport": "stdio"
    },
    "file_tools": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace/knowledge_agent", "/workspace/LightRAG"],
        "transport": "stdio"
    },
    "deepwiki": {
        "url": "https://mcp.deepwiki.com/sse",
        "transport": "sse"
    }
}
```

## Prompts

The behavior of each sub-agent is guided by a system prompt located in the `prompts/` directory. These prompts define the agent's persona, goals, and expected output format.

- **`analyst_prompt.txt`**: Guides the Analyst in identifying knowledge gaps.
- **`planner_prompt.txt`**: Guides the Researcher's Planner in creating a search strategy.
- **`refiner_prompt.txt`**: Guides the Researcher's Refiner in adjusting the search strategy.
- **`summarizer_prompt.txt`**: Guides the Researcher's Summarizer in creating a concise summary.
- **`search_ranker_prompt.txt`**: Guides the Curator in ranking search results for ingestion.
- **`ingester_prompt.txt`**: Guides the Curator in ingesting new sources.
- **`auditor_prompt.txt`**: Guides the Auditor in identifying data quality issues.
- **`fixer_prompt.txt`**: Guides the Fixer in correcting data quality issues.
- **`advisor_prompt.txt`**: Guides the Advisor in providing recommendations.

## Logging

The agent's operations are logged to a file in the `logs/` directory. The logs are in JSON format and include the timestamp, log level, agent name, and the message, providing a detailed record of the agent's activity.

## Database

The Knowledge Agent uses a PostgreSQL database to store the reports generated by the sub-agents and to cache processed web content. The `db_utils.py` file contains the functions for creating the tables and interacting with the database.

The database schema consists of tables for each agent's reports and a central `documents` table:

- `analyst_reports`
- `researcher_reports`
- `curator_reports`
- `auditor_reports`
- `fixer_reports`
- `advisor_reports`
- `documents`

The `documents` table stores processed web content and has the following structure:

- `id`: Primary key (integer)
- `url`: The unique URL of the source document (text)
- `raw_document`: The raw binary content of the document (BYTEA)
- `markdown_content`: The processed, clean markdown version of the content (text)
- `summary`: A concise summary of the document (text)
- `created_at`: Timestamp of when the document was first added

## Workflow Details

The `maintenance` workflow is the most comprehensive, executing the full lifecycle of knowledge management. Here is a step-by-step breakdown of the process:

1. **Analysis**: The **Analyst** examines the knowledge base to identify areas that are outdated or incomplete. It generates a report detailing these knowledge gaps.
2. **Research**: The **Researcher** takes the Analyst's report and executes the entire content acquisition pipeline:
    - The **Planner** develops a set of targeted, diversified search queries.
    - The agent executes these searches. For each resulting URL, it uses the **hybrid content processor** (Trafilatura with a Playwright fallback) to extract clean, main content and generate high-quality markdown.
    - All artifacts (raw document, markdown, and summary) are stored in the `documents` table in the database.
    - If the initial searches are insufficient, the **Refiner** adjusts the plan and tries again.
3. **Curation**: The **Curator** ranks the URLs from the Researcher and decides which ones to ingest into the knowledge base, and then proceeds to ingest approved content.
4. **Audit**: The **Auditor** scans the knowledge graph for inconsistencies, duplicates, and other data quality issues, producing a report of its findings.
5. **Fix**: The **Fixer** takes the Auditor's report and attempts to correct the identified issues. For any destructive changes (e.g., deleting an entity), it will require human approval.
6. **Advise**: Finally, the **Advisor** analyzes the reports from all the other agents, identifies recurring problems, and suggests systemic improvements to the LightRAG configuration or the agent's own processes.
