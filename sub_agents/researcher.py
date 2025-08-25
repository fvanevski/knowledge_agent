# researcher.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
from langchain_core.messages import AIMessage
import json
import os
import re
from state import AgentState
from tools import initialize_researcher, update_researcher_report

def _extract_and_clean_json_researcher(llm_output: str) -> dict:
    """
    Extracts, cleans, and reconstructs a valid JSON object from the LLM's output.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')
    
    status = f"Extracting and cleaning JSON from researcher LLM output"
    print(status)
    logger.info(status)
    try:
        # First, try to parse the whole output as-is
        return json.loads(llm_output)
    except json.JSONDecodeError:
        # If that fails, try to find all search objects and reconstruct the JSON
        status = f"Initial JSON parsing failed, attempting to reconstruct JSON from partial outputs."
        print(status)
        logger.info(status)
        try:
            # This regex will find all dictionaries that look like search objects
            searches = re.findall(r'\{\s*"rationale":.*?"results":.*?\}\s*\}', llm_output, re.DOTALL)
            status = f"Found {len(searches)} search objects in the output."
            print(status)
            logger.info(status)

            if not searches:
                # If no search objects are found, return a valid JSON with an empty list
                status = f"No search objects found in the output, returning empty searches list."
                print(status)
                logger.info(status)
                return {"searches": []}

            # Reconstruct the JSON object
            status = f"Reconstructing JSON from found search objects."
            print(status)
            logger.info(status)
            reconstructed_json_string = f'{{"searches": [{", ".join(searches)}]}}'
            
            status = f"Reconstructed JSON: {reconstructed_json_string}"
            print(status)
            logger.info(status)
            return json.loads(reconstructed_json_string)

        except (json.JSONDecodeError, ValueError) as e:
            status = f"Failed to parse or reconstruct JSON: {e}"
            print(status)
            logger.error(status)
            raise ValueError(status)

async def researcher_agent_node(state: AgentState):
    logger = state['logger']

    # One-time initialization of the researcher state
    if not state.get("researcher_report_id"):
        status = f"--- Researcher state not initialized. Calling initialize_researcher directly. ---"
        print(status)
        logger.info(status)
        try:
            init_result = initialize_researcher(state['timestamp'])
            if isinstance(init_result, dict):
                state["researcher_report_id"] = init_result.get("researcher_report_id")
                state["researcher_gaps_todo"] = init_result.get("researcher_gaps_todo")
                state["researcher_gaps_complete"] = []
                status = f"--- Initialized researcher state: {init_result} ---"
                print(f"[INFO] {status}")
                logger.info(status)
        except Exception as e:
            status = f"Failed to initialize researcher state: {e}"
            print(f"[ERROR] {status}")
            logger.error(status)
            return {"status": status}

    # Create the specialized agent for performing searches
    searcher_prompt = ChatPromptTemplate.from_template(open("prompts/searcher_prompt.txt", "r").read())
    searcher_tools = [tool for tool in state['mcp_tools'] if tool.name == 'google_search']

    status = f"Attempting to invoke searcher agent executor with tools: {searcher_tools}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        agent_runnable = create_openai_tools_agent(state['model'], searcher_tools, searcher_prompt)
        executor = AgentExecutor(agent=agent_runnable, tools=searcher_tools, verbose=True)
    except Exception as e:
        status = f"Failed to create searcher agent executor: {e}"
        print(f"[ERROR] {status}")
        logger.error(status)
        return {"status": status}

    # Main control loop, managed by the node
    gaps_todo = state.get("researcher_gaps_todo", [])
    if isinstance(gaps_todo, list):
        for current_gap in gaps_todo:
            state['researcher_current_gap'] = current_gap
            gap_id = current_gap['gap_id']
            research_topic = current_gap['research_topic']

            status = f"Starting research for gap: {gap_id}, research topic: {research_topic}"
            print(f"[INFO] {status}")
            logger.info(status)

            try:
                # Invoke the specialized agent for just ONE gap
                searcher_result = await executor.ainvoke({"input": research_topic})
                status = f"Agent for gap {gap_id} finished. Raw output:\n{searcher_result.get('output')}"
                print(f"[INFO] {status}")
                logger.info(status)

                # The node, not the agent, saves the results
                try:
                    # Use the new helper function to extract and clean the JSON
                    json_output = _extract_and_clean_json_researcher(searcher_result.get("output", ""))
                    searches = json_output.get("searches", [])
                    status = f"Successfully parsed searches for gap {gap_id}: {searches}"
                    print(f"[INFO] {status}")
                    logger.info(status)

                except (ValueError, json.JSONDecodeError) as e:
                    status = f"Agent for gap {gap_id} returned invalid JSON: {searcher_result.get('output')}. Error: {e}"
                    print(f"[ERROR] {status}")
                    logger.error(status)
                    continue

                status = f"Preparing to update report for gap {gap_id} with {len(searches)} searches"
                print(f"[INFO] {status}")
                logger.info(status)
                try:
                    report_id = state['researcher_report_id']
                    current_gap = state['researcher_current_gap']
                    tool_input = {
                        "report_id": report_id,
                        "current_gap": current_gap,
                        "search_results": searches
                    }
                    result = update_researcher_report.invoke(tool_input)
                    status = f"Updated researcher report for gap {gap_id}: {result}"
                    print(f"[INFO] {status}")
                    logger.info(status)
                except Exception as e:
                    status = f"update_researcher_report failed for gap {gap_id}: {e}"
                    print(f"[ERROR] {status}")
                    logger.error(status, exc_info=True)
                    continue

                status = f"--- Successfully completed research and report writing for gap: {gap_id} ---"
                print(f"[INFO] {status}")
                logger.info(status)
                if "researcher_gaps_complete" not in state or state["researcher_gaps_complete"] is None:
                    state["researcher_gaps_complete"] = []
                state["researcher_gaps_complete"].append(gap_id)

            except Exception as e:
                status = f"An unexpected error occurred while processing gap {gap_id}: {e}"
                print(f"[ERROR] {status}")
                logger.error(status, exc_info=True)
                continue


    final_status = f"Successfully and incrementally completed researcher report with ID {state['researcher_report_id']} and wrote report to researcher_report.json."
    logger.info(final_status)
    return {"messages": state['messages'] + [AIMessage(content=final_status)]}
