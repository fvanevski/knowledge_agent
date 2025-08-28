# Product Requirements Document: Two-Model Knowledge Base Enrichment

Author: Gemini
Version: 1.0
Date: August 28, 2025
Status: Draft

## 1. Introduction & Vision

### 1.1. The Problem

Our current LightRAG knowledge base ingestion pipeline successfully uses a smaller, efficient instruct model to perform initial entity and relationship extraction. This approach is fast, scalable, and minimizes hallucinations. However, the smaller model's limited reasoning capabilities result in a knowledge graph that primarily captures explicit, direct relationships mentioned within single text chunks. This misses a significant number of implicit, indirect, and second-order connections that are crucial for deep, contextual understanding and advanced querying. The result is a graph that is less dense and semantically rich than it could be, limiting the analytical power of the final knowledge base.

### 1.2. The Vision

We envision a hybrid, two-model system that combines the efficiency of a small instruct model for initial ingestion with the advanced reasoning power of a larger language model for periodic enrichment. This approach will create a highly accurate and densely connected knowledge graph. By separating the tasks, we can maintain a fast and cost-effective primary ingestion pipeline while layering on a sophisticated analytical pass to infer complex relationships. This will transform our knowledge base from a collection of extracted facts into a powerful tool for discovery and insight.

## 2. Goals & Objectives

The primary goal of this project is to significantly increase the density and semantic richness of our knowledge graph by identifying and adding implicit relationships missed during initial ingestion.

Objective 1: Increase Relationship Density: Increase the average number of relationships per entity in the graph by at least 30% for processed documents.

Objective 2: Improve Query Performance: Improve the quality and completeness of answers for complex, multi-hop queries that rely on inferred relationships.

Objective 3: Maintain Ingestion Efficiency: Ensure the implementation of the enrichment workflow does not slow down the primary document ingestion pipeline. The enrichment process will run asynchronously.

Objective 4: Ensure Data Quality: Implement a process that allows for review and validation of inferred relationships to maintain the high quality of the knowledge base.

## 3. User Personas

Knowledge Manager/Data Scientist: The primary user of this new workflow. They are responsible for the quality of the knowledge base and will configure, run, and monitor the enrichment jobs. They need tools to manage prompts for the reasoning model and review its output.

Data Analyst/End-User: The primary beneficiary. They will query the knowledge base (either directly or via a RAG application) and expect more comprehensive and insightful answers that leverage the newly inferred relationships.

## 4. Functional Requirements

### 4.1. FR1: Core Relationship Enrichment Service

A new, standalone service will be created that uses a large reasoning model to infer new relationships between existing entities in the knowledge graph.

Input: The service will accept a set of entity names or a subgraph (e.g., all entities extracted from a specific document) as input.

Context Generation: The service will retrieve the descriptions and existing relationships for the input entities from the graph database to form a context block.

LLM Prompting: The service will format this context into a specialized prompt for a large reasoning model. The prompt will instruct the model to identify new, implicit relationships between the provided entities based only on the context.

Output: The service will output a list of new, inferred relationships in the same standard JSON format as the primary ingestion pipeline, including source, target, description, type, and a strength score reflecting the model's confidence.

### 4.2. FR2: Enrichment Workflow Triggering

The enrichment process must be triggerable in a flexible manner.

On-Demand Triggering: Allow a Knowledge Manager to manually trigger the enrichment service for a specific document or set of entities via a CLI or simple UI.

Post-Ingestion Triggering: Automatically trigger the enrichment service as an optional, asynchronous final step after a document has been successfully processed by the primary ingestion pipeline.

Scheduled Triggering: Allow for scheduled, batch enrichment jobs to run periodically (e.g., nightly) on entities that have not yet been enriched.

### 4.3. FR3: Model & Prompt Configuration

The system must allow for easy configuration of the reasoning model and its prompt.

The connection details for the large reasoning model (e.g., API endpoint, credentials) will be configurable via environment variables.

The prompt template used by the enrichment service will be stored in the prompt.py file, separate from the primary ingestion prompt, to allow for independent tuning.

## 5. Non-Functional Requirements

Performance: The primary ingestion pipeline's performance must not be impacted. The enrichment service is a lower-priority, asynchronous task. A single document enrichment pass should complete in a reasonable timeframe (target: < 5 minutes for a 50-page document).

Scalability: The enrichment service should be able to handle batch jobs of thousands of entities without failure. It should leverage asynchronous processing and task queues.

Cost Management: The use of the larger, more expensive reasoning model must be managed. The system should log API usage and costs associated with enrichment jobs.

## 6. Technical Implementation Details

### 6.1. High-Level Architecture

The existing operate.py and lightrag.py modules will manage the primary ingestion. A new module, enrichment.py, will contain the logic for the Relationship Enrichment Service. This service will be callable from the main pipeline and can also be run as a separate script.

### 6.2. Sample Enrichment Prompt Template

A new prompt will be added to prompt.py specifically for the reasoning model.

PROMPTS["relationship_enrichment"] = """---Role---
You are a Knowledge Graph Analyst. Your task is to infer new, non-obvious relationships between a given set of entities based on their descriptions.

---Context---
Here are the entities and their known descriptions from the knowledge base:

```json
{context_entities_json}
```

---Existing Relationships---
The following relationships are already known and should NOT be duplicated:

```json
{existing_relationships_json}
```

---Task---
Analyze the combined context from all entity descriptions. Identify any new, implicit relationships between the entities listed above. For example, if one entity's description mentions an action that affects another entity, that implies a relationship.

---Output Format---
Your output MUST be a valid JSON object containing a single key `new_relationships`. If no new relationships can be inferred, return an empty list.

---Relationship Definitions---
For each new relationship, select the most appropriate relationship_type from this fixed list:
[TARGETS, EVALUATES, PRODUCES, CAUSES, IS_A, IS_PART_OF, IS_LOCATED_IN, INFLUENCES, PUBLISHED_BY, LED_BY, CRITICIZES, SUPPORTS, USES, INVOLVES, ESTIMATES, AFFIRMED_BY, PAYS_INTO, REIMBURSES]

---Output---"""

## 7. Success Metrics

* **Graph Density Score:** Track the ratio of relationships to entities before and after enrichment runs.
* **Qualitative Query Evaluation:** Establish a set of complex "challenge questions" and compare the answers generated by the RAG system using the pre-enrichment vs. post-enrichment graph.
* **Manual Review Acceptance Rate:** Track the percentage of inferred relationships that are accepted as valid by a human reviewer.

## 8. Future Considerations

* **Automated Prompt Tuning:** Explore using feedback from manual reviews to automatically fine-tune the enrichment prompt.
* **Multi-Model Support:** Abstract the model-calling logic to easily swap between different large reasoning models to find the best balance of cost and performance.
* **Recursive Enrichment:** Investigate running the enrichment service multiple times on the same subgraph to discover even deeper, multi-hop relationships.
