Of course. Here is a detailed and comprehensive Product Requirements Document (PRD) for the "Evolver" workflow.

### **Product Requirements Document: Knowledge Agent "Evolver" Workflow**

**Author:** Gemini
**Version:** 1.0
**Date:** August 26, 2025

#### **1. Introduction**

The Knowledge Agent project has successfully established a robust, multi-agent system for the maintenance and curation of a LightRAG knowledge base. The current "maintenance" workflow is a structured, sequential process that leverages a team of specialized agents to perform tasks ranging from analysis to research to data quality control.

While effective, the current system is static; its performance is dependent on the initial design of the agents and their prompts. To address this, we propose the development of a new, parallel workflow called the "Evolver." The Evolver will introduce a mechanism for the Knowledge Agent to autonomously improve its own performance over time, creating a self-optimizing system that learns and adapts without direct human intervention. This is inspired by the principles of natural selection, where iterative changes are tested against a fitness function, and successful adaptations are propagated.

#### **2. Goals and Objectives**

* **Primary Goal:** To create a self-improving Knowledge Agent that can autonomously optimize its "maintenance" workflow for better performance and higher-quality results.
* **Key Objectives:**
  * Develop a new "Evolver" meta-agent that can orchestrate the process of experimentation and adaptation.
  * Create a streamlined "evaluation" workflow that can be run repeatedly and efficiently to test the performance of the maintenance agents.
  * Implement a robust scoring system to objectively measure the quality of the evaluation workflow's results.
  * Design and build "Tweaker" sub-agents that can modify the characteristics of the maintenance agents (e.g., prompts, code).
  * Establish a human-in-the-loop review process to validate the improvements made by the Evolver and to integrate them into the main system.

#### **3. User Personas**

* **AI Developer/Researcher (Primary):** The user who is building and maintaining the Knowledge Agent. They are technically proficient and are interested in creating a more autonomous and intelligent system. They will be responsible for reviewing the Evolver's suggestions and for making the final decision on whether to integrate them.

#### **4. Features and Functionality**

##### **4.1. The "Evolver" Meta-Agent**

The Evolver will be a new top-level agent that orchestrates the entire evolution workflow. It will be responsible for:

* Initiating and managing the iterative evolution process.
* Directing the "Tweaker" sub-agents to modify the characteristics of the maintenance agents.
* Triggering the "evaluation" workflow to test the new characteristics.
* Receiving and interpreting the results of the evaluation.
* Making the decision to either "lock in" or "revert" the changes based on the evaluation score.

##### **4.2. The "Evaluation" Workflow**

This will be a streamlined version of the existing "maintenance" workflow, designed for speed and efficiency. It will include the following steps:

1. **Analyst:** Identifies a single, well-defined knowledge gap.
2. **Researcher:** Performs a limited number of searches to find sources related to the knowledge gap.
3. **Curator:** Ranks the sources found by the Researcher.

##### **4.3. The Scoring and Evaluation Engine**

A new module will be developed to score the results of the evaluation workflow. The score will be a composite of multiple metrics, including:

* **Source Relevance:** A measure of how relevant the curated sources are to the initial knowledge gap. This could be determined by a separate "Evaluator" agent that compares the sources to the key questions in the research topic.
* **Source Diversity:** A measure of the variety of the sources (e.g., different domains, file types).
* **Efficiency:** The time and computational resources used to complete the evaluation workflow.

##### **4.4. The "Tweaker" Sub-Agents**

These will be specialized agents responsible for making targeted modifications to the maintenance agents. Initially, we will develop a single "Prompt Tweaker" agent with a constrained set of capabilities:

* **Prompt Tweaker:** This agent will be given the ability to read the prompt file for a specific maintenance agent (e.g., `planner_prompt.txt`) and to propose a specific, targeted change (e.g., rephrasing a sentence, adding a new instruction).

##### **4.5. The Human Review and Integration Process**

The Evolver will log all of its experiments and their results to a new table in the database. When the Evolver has found a set of tweaks that significantly improves the evaluation score, it will flag these changes for human review. The developer can then review the changes and, if they approve, merge them into the main branch of the project.

#### **5. Technical Requirements and Architecture**

* **New LangGraph Workflow:** A new "evolve" workflow will be added to the `knowledge_agent.py` file. This will be a parallel workflow to the existing "maintenance" workflow.
* **New Sub-Agents:** The "Evolver," "Evaluator," and "Prompt Tweaker" agents will be developed as new modules in the `sub_agents` directory.
* **Database Schema:** A new `evolution_runs` table will be added to the database to store the results of each experiment. This table will include columns for the run ID, the tweaks that were made, the evaluation score, and the final status (kept or reverted).
* **Version Control:** The system will need a mechanism for managing different versions of the agent characteristics (e.g., prompts). This could be done by creating a new branch in the Git repository for each evolution experiment.

#### **6. Future-Looking Branches and Areas for Exploration**

* **Advanced Optimization Algorithms:** The initial implementation will use a simple "hill climbing" algorithm. Future versions could explore more advanced techniques, such as:
  * **Simulated Annealing:** This would allow the system to occasionally accept a "bad" tweak in order to escape local optima.
  * **Genetic Algorithms:** A more fully-featured genetic algorithm could be implemented, with a population of agents that "evolve" over multiple generations.
* **Expanded "Tweak" Space:** The initial "Prompt Tweaker" will be quite constrained. Future versions could include:
  * **Code Tweaker:** An agent that can modify the Python code of the maintenance agents. This would be a high-risk, high-reward capability that would require very careful implementation.
  * **Graph Tweaker:** An agent that can modify the structure of the LangGraph itself, for example, by adding or removing nodes or edges.
* **Automated Integration:** In a more advanced version, the system could be given the ability to automatically merge its own improvements into the main branch, creating a truly self-evolving codebase.

#### **7. Success Metrics**

* **Rate of Improvement:** The primary metric will be the rate at which the evaluation score improves over time.
* **Quality of Evolved Agents:** The subjective quality of the evolved agents, as assessed by the human reviewer.
* **Automation Efficiency:** The amount of human effort saved by the automated evolution process.
