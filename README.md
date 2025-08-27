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

- **[LangChain](https://www.langchain.com/)**: Used for building the core agent logic and integrating with language models.
- **[LangGraph](https://langchain-ai.github.io/langgraph/)**: Used to create the stateful, multi-agent graph that orchestrates the sub-agents.
- **[langchain-mcp-adapters](https://pypi.org/project/langchain-mcp-adapters/)**: Used for connecting to and using tools from MCP servers.
- **[ChatOpenAI](https://python.langchain.com/docs/integrations/chat/openai)**: Used as the language model for the agents.
- **[pydantic](https://pydantic-docs.helpmanual.io/)**: Used for data validation and settings management.
- **[psycopg2-binary](https://pypi.org/project/psycopg2-binary/)**: Used for connecting to the PostgreSQL database.
- **[python-dotenv](https://pypi.org/project/python-dotenv/)**: Used for managing environment variables.
- **[json-repair](https://pypi.org/project/json-repair/)**: Used for repairing malformed JSON.
- **[requests](https://pypi.org/project/requests/)**: Used for making HTTP requests to download web content.
- **[pdfplumber](https://pypi.org/project/pdfplumber/)**: Used for extracting text from PDF documents.
- **[beautifulsoup4](https://pypi.org/project/beautifulsoup4/)**: Used for parsing HTML content.
- **[html2text](https://pypi.org/project/html2text/)**: Used for converting HTML to markdown.

### Agent Roles

- **Analyst**: Identifies knowledge gaps and stale information in the knowledge base by analyzing its content and structure.
- **Researcher**: Acts as the primary research arm of the agent. It breaks down research tasks and manages the entire content acquisition pipeline:
    - **Planner**: Creates a strategic search plan using advanced search operators to target information effectively.
    - **Content Processor**: Fetches raw documents (PDF, HTML, etc.), processes them into clean markdown, and stores both the raw and processed versions in the database.
    - **Refiner**: If the initial search plan is unsuccessful, the refiner adjusts the strategy to find the missing information.
    - **Summarizer**: Generates a concise summary from the clean markdown content.
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
    git clone https://github.com/your_username/knowledge-agent.git
    cd knowledge-agent
    ```

2. Install the dependencies using uv:

    ```sh
    uv sync
    ```

3. Set up the environment variables by creating a `.env` file in the root directory. You can use the `.env.example` file as a template.

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

1.  **Analysis**: The **Analyst** examines the knowledge base to identify areas that are outdated or incomplete. It generates a report detailing these knowledge gaps.
2.  **Research**: The **Researcher** takes the Analyst's report and executes the entire content acquisition pipeline:
    - The **Planner** develops a set of targeted search queries using advanced search operators.
    - The agent executes these searches and for each resulting URL, it downloads the raw content, processes it into clean markdown, and generates a summary.
    - All artifacts (raw document, markdown, and summary) are stored in the `documents` table in the database.
    - If the initial searches are insufficient, the **Refiner** adjusts the plan and tries again.
3.  **Audit**: The **Auditor** scans the knowledge graph for inconsistencies, duplicates, and other data quality issues, producing a report of its findings.
4.  **Fix**: The **Fixer** takes the Auditor's report and attempts to correct the identified issues. For any destructive changes (e.g., deleting an entity), it will require human approval.
5.  **Advise**: Finally, the **Advisor** analyzes the reports from all the other agents, identifies recurring problems, and suggests systemic improvements to the LightRAG configuration or the agent's own processes.