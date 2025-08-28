from __future__ import annotations
import json
from typing import Any

PROMPTS: dict[str, Any] = {}

# --- DEPRECATED DELIMITERS ---
# Kept for reference for any old cached items that might be reprocessed.
# PROMPTS["DEFAULT_TUPLE_DELIMITER"] = "<|>"
# PROMPTS["DEFAULT_RECORD_DELIMITER"] = "##"
# PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"

PROMPTS["DEFAULT_USER_PROMPT"] = "n/a"

# --- JSON Schema for Entity Definitions ---
# Structuring the definitions as a dictionary makes them easy to manage and convert to a JSON string.
PROMPTS["ENTITY_DEFINITIONS"] = {
    "organization/institution": {
        "description": "A named corporate, governmental, or non-profit entity.",
        "examples": ["The Heritage Foundation", "U.S. Supreme Court", "U.S. Department of Agriculture (USDA)"]
    },
    "person": {
        "description": "A specific, named individual.",
        "examples": ["Elon Musk", "Earl Warren"]
    },
    "location/geo": {
        "description": "A specific geographical place.",
        "examples": ["United States", "California", "Texas"]
    },
    "event": {
        "description": "A specific, named occurrence at a point in time.",
        "examples": ["October 7, 2023 Hamas Attack", "2024 G7 Summit"]
    },
    "policy/proposal": {
        "description": "A specific policy, proposal, or named formal plan originating from a person or organization.",
        "examples": ["Tariff Policy", "Police Militarization Plan", "In-State Tuition Policy"]
    },
    "law/regulation": {
        "description": "A named law or regulation.",
        "examples": ["California Indian Child Welfare Act", "Personal Responsibility and Work Opportunity Reconciliation Act of 1996"]
    },
    "tax/fiscal_instrument": {
        "description": "A specific tax, fee, or financial mechanism for revenue or distribution.",
        "examples": ["Sales and Excise Taxes", "Property Taxes", "Payroll Deductions"]
    },
    "narrative": {
        "description": "A specific, socially constructed story (not objective facts) used to shape public perception, justify social policy, and influence behavior by defining a social group, issue, or event.",
        "examples": ["Welfare Queen", "Climate Hoax", "Meritocracy"]
    },
    "misinformation/disinformation": {
        "description": "False or inaccurate information, such as fabricated content, manipulated content, imposter content, false context, and unsupported conspiracy theories.",
        "examples": ["Pizzagate", "Birtherism", "Plandemic", "Altered Pelosi Video"]
    },
    "digital_asset": {
        "description": "A specific digital item or platform.",
        "examples": ["X (formerly Twitter)", "$TRUMP Memecoin"]
    },
    "concept/idea": {
        "description": "An abstract idea, theory, or social construct.",
        "examples": ["Free Speech Absolutism", "Racial Segregation", "Unreimbursed Hospital Costs"]
    },
    "metric/score": {
        "description": "A specific, quantifiable measure or statistic, often including numbers and units.",
        "examples": ["Freedom on the Net Score", "$89.8 billion", "11,862 hate crime incidents"]
    },
    "publication/article": {
        "description": "A named report, book, or article.",
        "examples": ["Mandate for Leadership", "State Report on Undocumented Immigrant Hospital Costs"]
    },
    "political_group": {
        "description": "A group defined by political affiliation or ideology, not a formal organization.",
        "examples": ["White Supremacist Groups"]
    },
    "scenario/situation": {
        "description": "A described situation or context without a formal name.",
        "examples": ["Wealth dynamics between households"]
    },
    "demographic/population": {
        "description": "A group of people defined by shared characteristics.",
        "examples": ["Black Americans", "LGBTQ+ Individuals", "Undocumented Residents"]
    },
    "publisher/outlet": {
        "description": "A named publisher or media outlet.",
        "examples": ["The Washington Post", "The Texas Tribune", "Journal of Law"]
    },
    "time_period/era": {
        "description": "A specific period of time.",
        "examples": ["2025", "2020–2024", "The Civil Rights Era"]
    }
}

# Convert the dictionary to a formatted JSON string to be inserted into the prompt
PROMPTS["ENTITY_DEFINITIONS_JSON"] = json.dumps(PROMPTS["ENTITY_DEFINITIONS"], indent=2)


PROMPTS["entity_extraction"] = """---Goal---
From the text snippet provided, extract key entities and their relationships. The text is a small chunk of a larger document. Identify both direct and implicit relationships (e.g., causal links, memberships, hierarchies) when the connection is clear from the context.

---Output Format---
Your output MUST be a single, valid JSON object and nothing else. Do not include any explanatory text, markdown code fences (like ```json), or any other text before or after the JSON. The JSON object will contain two keys: "entities" and "relationships".

---Entity Definitions---
Extract entities that belong to one of the types defined in the following JSON object. Use these definitions and examples to guide your classification. The `type` you assign in your output must be one of the keys from this JSON object.
```json
{entity_definitions_json}
```

---Relationship Definitions---
For each relationship, select the most appropriate `relationship_type` from this fixed list:
[TARGETS, EVALUATES, PRODUCES, CAUSES, IS_A, IS_PART_OF, IS_LOCATED_IN, INFLUENCES, PUBLISHED_BY, LED_BY, CRITICIZES, SUPPORTS, USES, INVOLVES, ESTIMATES, AFFIRMED_BY, PAYS_INTO, REIMBURSES]

---Instructions & Rules---
1.  **Entities**:
    * `name`: Standardize the name. Use the full, formal name (e.g., "American Civil Liberties Union" instead of "ACLU"). Use Title Case.
    * `type`: Assign one of the specified entity types, using the exact lowercase format from the keys in the Entity Definitions JSON.
    * `description`: Briefly describe the entity using only information from the text. If no description is available, state "Not specified in text."

2.  **Relationships**:
    * `source` / `target`: Use the standardized entity names.
    * `description`: Describe the relationship in one concise sentence based on the text.
    * `type`: Choose exactly one type from the predefined list above.
    * `strength`: Score from 1-10 indicating how explicit the relationship is (1=implied, 10=directly stated).

3.  **CRITICAL RULES**:
    * Your output must be a clean, valid JSON object. Do not include any non-JSON text, comments, or markdown formatting.
    * You are strictly forbidden from using 'UNKNOWN' as an entity type. If an entity does not clearly fit any defined type, you MUST classify it as `concept/idea`.

---Examples---
{examples}

---Real Data---
Text:
{input_text}

---Output---
"""

PROMPTS["entity_extraction_examples"] = [
    """------Example 1------

Text:
```
Project 2025, an initiative led by the Heritage Foundation, proposes sweeping changes to the federal government. A key part of the plan is the reintroduction of "Schedule F," an executive order that would strip job protections from thousands of federal employees, making them easier to fire. Critics, such as the ACLU, argue this policy undermines the principle of a non-partisan civil service. The plan is detailed in their publication, "Mandate for Leadership."
```

Output:
{
  "entities": [
    {
      "name": "Project 2025",
      "type": "policy/proposal",
      "description": "An initiative proposing major changes to the federal government, led by the Heritage Foundation."
    },
    {
      "name": "The Heritage Foundation",
      "type": "organization/institution",
      "description": "The organization leading the Project 2025 initiative."
    },
    {
      "name": "Schedule F",
      "type": "policy/proposal",
      "description": "An executive order designed to remove job protections from federal employees, proposed as part of Project 2025."
    },
    {
      "name": "American Civil Liberties Union",
      "type": "organization/institution",
      "description": "An organization that criticizes the Schedule F policy."
    },
    {
      "name": "Mandate for Leadership",
      "type": "publication/article",
      "description": "The publication where the Project 2025 plan is detailed."
    },
    {
      "name": "Non-Partisan Civil Service",
      "type": "concept/idea",
      "description": "A principle that critics argue is undermined by the Schedule F policy."
    }
  ],
  "relationships": [
    {
      "source": "The Heritage Foundation",
      "target": "Project 2025",
      "description": "The Heritage Foundation leads the Project 2025 initiative.",
      "type": "LED_BY",
      "strength": 10
    },
    {
      "source": "Project 2025",
      "target": "Schedule F",
      "description": "Project 2025 includes the reintroduction of the Schedule F policy.",
      "type": "INVOLVES",
      "strength": 9
    },
    {
      "source": "American Civil Liberties Union",
      "target": "Schedule F",
      "description": "The ACLU argues that the Schedule F policy undermines civil service principles.",
      "type": "CRITICIZES",
      "strength": 8
    },
    {
      "source": "Mandate for Leadership",
      "target": "Project 2025",
      "description": "The details of Project 2025 are found in the 'Mandate for Leadership' publication.",
      "type": "PUBLISHED_BY",
      "strength": 10
    }
  ]
}
""",
    """------Example 2------

Text:
```
Following his acquisition of X (formerly Twitter), Elon Musk reinstated several controversial accounts, citing a commitment to "free speech absolutism." A study by the Center for Strategic and International Studies (CSIS) analyzed the impact of these changes on the platform's "Freedom on the Net Score," which dropped by 5 points in the subsequent year. The study also noted an increase in the prevalence of the $TRUMP memecoin, a digital asset often promoted by the reinstated accounts.
```

Output:
{
  "entities": [
    {
      "name": "Elon Musk",
      "type": "person",
      "description": "Acquired X (formerly Twitter) and reinstated controversial accounts."
    },
    {
      "name": "X",
      "type": "organization/institution",
      "description": "A social media platform, formerly known as Twitter, acquired by Elon Musk."
    },
    {
      "name": "Free Speech Absolutism",
      "type": "concept/idea",
      "description": "The principle cited by Elon Musk for reinstating controversial accounts on X."
    },
    {
      "name": "Center for Strategic and International Studies",
      "type": "organization/institution",
      "description": "An organization that studied the impact of policy changes on X."
    },
    {
      "name": "Freedom on the Net Score",
      "type": "metric/score",
      "description": "A metric that decreased by 5 points for the X platform after the acquisition."
    },
    {
      "name": "$TRUMP Memecoin",
      "type": "digital_asset",
      "description": "A digital asset that saw increased promotion on X after account reinstatements."
    }
  ],
  "relationships": [
    {
      "source": "Elon Musk",
      "target": "X",
      "description": "Elon Musk acquired the platform X.",
      "type": "IS_PART_OF",
      "strength": 10
    },
    {
      "source": "Elon Musk",
      "target": "Free Speech Absolutism",
      "description": "Elon Musk's actions were justified by his stated commitment to free speech absolutism.",
      "type": "SUPPORTS",
      "strength": 9
    },
    {
      "source": "Center for Strategic and International Studies",
      "target": "Freedom on the Net Score",
      "description": "The CSIS study analyzed the platform's Freedom on the Net Score.",
      "type": "EVALUATES",
      "strength": 8
    },
    {
      "source": "X",
      "target": "$TRUMP Memecoin",
      "description": "The $TRUMP memecoin was increasingly promoted on the X platform following the acquisition.",
      "type": "INVOLVES",
      "strength": 7
    }
  ]
}
""",
    """------Example 3------

Text:
```
Estimates from the Institute on Taxation and Economic Policy (ITEP) indicate that undocumented immigrants paid nearly $97 billion in federal, state, and local taxes in 2022. This figure includes over $54 billion in payments to the federal government.
```

Output:
{
  "entities": [
    {
      "name": "Institute on Taxation and Economic Policy",
      "type": "organization/institution",
      "description": "An organization that provides estimates on tax contributions from undocumented immigrants."
    },
    {
      "name": "$97 Billion",
      "type": "metric/score",
      "description": "The estimated total tax contribution from undocumented immigrants in 2022."
    },
    {
      "name": "Undocumented Immigrants",
      "type": "demographic/population",
      "description": "The population group whose tax contributions were estimated."
    }
  ],
  "relationships": [
    {
      "source": "Institute on Taxation and Economic Policy",
      "target": "$97 Billion",
      "description": "The Institute on Taxation and Economic Policy (ITEP) estimated the total tax contribution to be nearly $97 billion.",
      "type": "ESTIMATES",
      "strength": 10
    },
    {
      "source": "Undocumented Immigrants",
      "target": "$97 Billion",
      "description": "Undocumented immigrants were estimated to have paid nearly $97 billion in taxes.",
      "type": "PAYS_INTO",
      "strength": 9
    }
  ]
}
"""
]

PROMPTS["summarize_entity_descriptions"] = """---Role---
You are a Knowledge Graph Specialist responsible for data curation and synthesis.

---Task---
Your task is to synthesize a list of descriptions of a given entity or relation into a single, comprehensive, and cohesive summary.

---Instructions---
1. **Comprehensiveness:** The summary must integrate key information from all provided descriptions. Do not omit important facts.
2. **Context:** The summary must explicitly mention the name of the entity or relation for full context.
3. **Style:** The output must be written from an objective, third-person perspective.
4. **Length:** Maintain depth and completeness while ensuring the summary's length not exceed {summary_length} tokens.
5. **Language:** The entire output must be written in {language}.

---Data---
{description_type} Name: {description_name}
Description List:
{description_list}

---Output---
Output:
"""

PROMPTS["entity_continue_extraction"] = """
It seems some entities or relationships were missed. Please review the previous text and extract ONLY the missing items.

---Remember Rules---
1.  **Output Format**: Your output MUST be a valid JSON object containing "entities" and "relationships" keys. Add only new items to these lists.
2.  **Entity Schema**: `{"name": "...", "type": "...", "description": "..."}`
3.  **Relationship Schema**: `{"source": "...", "target": "...", "description": "...", "type": "...", "strength": ...}`
4.  **CRITICAL**: If nothing was missed, output an empty JSON object: `{"entities": [], "relationships": []}`.

---Output---
Add only new entities and relations below.
"""

PROMPTS["entity_if_loop_extraction"] = """
It appears some entities may have still been missed.

---Output---
Output:
"""

PROMPTS["fail_response"] = (
    "Sorry, I'm not able to provide an answer to that question.[no-context]"
)

PROMPTS["rag_response"] = """---Role---

You are a helpful assistant responding to user query about Knowledge Graph and Document Chunks provided in JSON format below.


---Goal---

Generate a concise response based on Knowledge Base and follow Response Rules, considering both current query and the conversation history if provided. Summarize all information in the provided Knowledge Base, and incorporating general knowledge relevant to the Knowledge Base. Do not include information not provided by Knowledge Base.

---Conversation History---
{history}

---Knowledge Graph and Document Chunks---
{context_data}

---Response Guidelines---
**1. Content & Adherence:**
- Strictly adhere to the provided context from the Knowledge Base. Do not invent, assume, or include any information not present in the source data.
- If the answer cannot be found in the provided context, state that you do not have enough information to answer.
- Ensure the response maintains continuity with the conversation history.

**2. Formatting & Language:**
- Format the response using markdown with appropriate section headings.
- The response language must in the same language as the user's question.
- Target format and length: {response_type}

**3. Citations / References:**
- At the end of the response, under a "References" section, each citation must clearly indicate its origin (KG or DC).
- The maximum number of citations is 5, including both KG and DC.
- Use the following formats for citations:
  - For a Knowledge Graph Entity: `[KG] <entity_name>`
  - For a Knowledge Graph Relationship: `[KG] <entity1_name> - <entity2_name>`
  - For a Document Chunk: `[DC] <file_path_or_document_name>`

---USER CONTEXT---
- Additional user prompt: {user_prompt}

---Response---
Output:"""

PROMPTS["keywords_extraction"] = """---Role---
You are an expert keyword extractor, specializing in analyzing user queries for a Retrieval-Augmented Generation (RAG) system. Your purpose is to identify both high-level and low-level keywords in the user's query that will be used for effective document retrieval.

---Goal---
Given a user query, your task is to extract two distinct types of keywords:
1. **high_level_keywords**: for overarching concepts or themes, capturing user's core intent, the subject area, or the type of question being asked.
2. **low_level_keywords**: for specific entities or details, identifying the specific entities, proper nouns, technical jargon, product names, or concrete items.

---Instructions & Constraints---
1. **Output Format**: Your output MUST be a valid JSON object and nothing else. Do not include any explanatory text, markdown code fences (like ```json), or any other text before or after the JSON. It will be parsed directly by a JSON parser.
2. **Source of Truth**: All keywords must be explicitly derived from the user query, with both high-level and low-level keyword categories required to contain content.
3. **Concise & Meaningful**: Keywords should be concise words or meaningful phrases. Prioritize multi-word phrases when they represent a single concept. For example, from "latest financial report of Apple Inc.", you should extract "latest financial report" and "Apple Inc." rather than "latest", "financial", "report", and "Apple".
4. **Handle Edge Cases**: For queries that are too simple, vague, or nonsensical (e.g., "hello", "ok", "asdfghjkl"), you must return a JSON object with empty lists for both keyword types.

---Examples---
{examples}

---Real Data---
User Query: {query}

---Output---
Output:"""

PROMPTS["keywords_extraction_examples"] = [
    """Example 1:

Query: "How does international trade influence global economic stability?"

Output:
{
  "high_level_keywords": ["International trade", "Global economic stability", "Economic impact"],
  "low_level_keywords": ["Trade agreements", "Tariffs", "Currency exchange", "Imports", "Exports"]
}

""",
    """Example 2:

Query: "What are the environmental consequences of deforestation on biodiversity?"

Output:
{
  "high_level_keywords": ["Environmental consequences", "Deforestation", "Biodiversity loss"],
  "low_level_keywords": ["Species extinction", "Habitat destruction", "Carbon emissions", "Rainforest", "Ecosystem"]
}

""",
    """Example 3:

Query: "What is the role of education in reducing poverty?"

Output:
{
  "high_level_keywords": ["Education", "Poverty reduction", "Socioeconomic development"],
  "low_level_keywords": ["School access", "Literacy rates", "Job training", "Income inequality"]
}

""",
]

PROMPTS["naive_rag_response"] = """---Role---

You are a helpful assistant responding to user query about Document Chunks provided provided in JSON format below.

---Goal---

Generate a concise response based on Document Chunks and follow Response Rules, considering both the conversation history and the current query. Summarize all information in the provided Document Chunks, and incorporating general knowledge relevant to the Document Chunks. Do not include information not provided by Document Chunks.

---Conversation History---
{history}

---Document Chunks(DC)---
{content_data}

---RESPONSE GUIDELINES---
**1. Content & Adherence:**
- Strictly adhere to the provided context from the Knowledge Base. Do not invent, assume, or include any information not present in the source data.
- If the answer cannot be found in the provided context, state that you do not have enough information to answer.
- Ensure the response maintains continuity with the conversation history.

**2. Formatting & Language:**
- Format the response using markdown with appropriate section headings.
- The response language must match the user's question language.
- Target format and length: {response_type}

**3. Citations / References:**
- At the end of the response, under a "References" section, cite a maximum of 5 most relevant sources used.
- Use the following formats for citations: `[DC] <file_path_or_document_name>`

---USER CONTEXT---
- Additional user prompt: {user_prompt}

---Response---
Output:"""
