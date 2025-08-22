# Knowledge Agent

An autonomous AI agent for intelligently updating, maintaining, and curating a [LightRAG](https://github.com/HKUDS/LightRAG) knowledge base.

## Table of Contents

- [About The Project](#about-the-project)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
- [Architecture](#architecture)
  - [Agent Roles](#agent-roles)
- [Configuration](#configuration)
- [Logging](#logging)

## About The Project

This project provides a sophisticated, autonomous AI agent—the "Knowledge Agent"—that proactively maintains, expands, and curates a local LightRAG knowledge base. It transforms the knowledge base from a static repository into a living, self-improving intelligence system, ensuring the information it contains is always accurate, relevant, and up-to-date.

The Knowledge Agent is designed to solve the challenges of maintaining a static knowledge base:

-   **Staleness:** Information quickly becomes outdated without a process for continuous updates.
-   **Incompleteness:** The knowledge base is limited to manually selected documents, creating information silos and knowledge gaps.
-   **High Maintenance Overhead:** The manual effort required to find new sources, ingest them, and fix data quality issues is significant and does not scale.
-   **Data Quality Degradation:** As more data is added, inconsistencies and duplicates can accumulate, reducing the reliability of RAG outputs and polluting the knowledge graph.

## Getting Started

### Prerequisites

-   Python 3.12+
-   [Rye](https://rye-up.com/) package manager
-   A running [LightRAG](https://github.com/HKUDS/LightRAG) instance
-   Running MCP servers for tools (e.g., Google Search)

### Installation

1.  Clone the repository:
    ```sh
    git clone https://github.com/your_username/knowledge-agent.git
    cd knowledge-agent
    ```
2.  Install the dependencies using Rye:
    ```sh
    rye sync
    ```

## Usage

The Knowledge Agent is executed via the `run.py` script. You can specify different workflows using command-line arguments.

**Full Maintenance Workflow:**

This is the default workflow and runs all the sub-agents in sequence.

```sh
rye run start --maintenance
```

**Specific Workflows:**

You can also run specific parts of the maintenance process:

-   **Analyze**: Identifies knowledge gaps and stale information.
    ```sh
    rye run start --analyze
    ```
-   **Research**: Finds new sources for the topics identified by the Analyst.
    ```sh
    rye run start --research
    ```
-   **Curate**: Ingests new information into the knowledge base.
    ```sh
    rye run start --curate
    ```
-   **Audit**: Reviews the knowledge base for data quality issues.
    ```sh
    rye run start --audit
    ```
-   **Fix**: Corrects the data quality issues found by the Auditor.
    ```sh
    rye run start --fix
    ```
-   **Advise**: Provides recommendations for systemic improvements.
    ```sh
    rye run start --advise
    ```

## Architecture

The Knowledge Agent uses a multi-agent architecture, where a primary **Orchestrator Agent** manages the overall workflow by delegating tasks to a team of specialized sub-agents. The agent framework is built using `LangChain` and `LangGraph`.

-   **Orchestrator (`Knowledge Agent`)**: The project manager. It holds the high-level plan and the overall state. It invokes the appropriate sub-agent for each task and handles the flow of information between them.
-   **Sub-Agents**: A team of specialized agents, each with a specific role in the knowledge management lifecycle.
-   **MCP Servers**: All agents interact with the outside world and the knowledge base exclusively through tools provided by MCP servers.

### Agent Roles

-   **Analyst**: Identifies knowledge gaps and stale information in the knowledge base.
-   **Researcher**: Searches the internet for new, relevant sources based on the Analyst's findings.
-   **Curator**: Reviews the sources found by the Researcher, evaluates them for relevance, and ingests the approved ones into LightRAG.
-   **Auditor**: Scans the knowledge graph for data quality issues like duplicate entities, inconsistent naming, and messy relationships.
-   **Fixer**: Corrects the data quality issues identified by the Auditor, with a human approval step for destructive operations.
-   **Advisor**: Analyzes recurring error patterns and suggests improvements to the LightRAG system's configuration to prevent future issues.

## Configuration

The Knowledge Agent requires a `mcp.json` file in the root directory to configure the connection to the MCP tool servers. This file should contain the server configurations, for example:

```json
{
  "servers": [
    {
      "name": "lightrag_mcp",
      "url": "http://localhost:8001",
      "enabled": true
    },
    {
      "name": "google_search_mcp",
      "url": "http://localhost:8003",
      "enabled": true
    }
  ]
}
```

## Logging

The agent's operations are logged to a file in the `logs/` directory. The logs are in JSON format and include the timestamp, log level, agent name, and the message, providing a detailed record of the agent's activity.
