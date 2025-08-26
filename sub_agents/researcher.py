# sub_agents/researcher.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from state import AgentState
from db_utils import initialize_researcher, update_researcher_report, extract_and_clean_json
import uuid

async def researcher_agent_node(state: AgentState):
    """The main node for the researcher workflow."""
    logger = state['logger']
    report_id = state.get("researcher_report_id")
    gaps_todo = state.get("researcher_gaps_todo", [])
    gaps_complete = state.get("researcher_gaps_complete", [])
    final_status = None

    if not report_id:
        try:
            init_result = initialize_researcher(state['timestamp'])
            report_id = init_result.get("researcher_report_id")
            gaps_todo = init_result.get("researcher_gaps_todo")
            gaps_complete = []
            status = f"--- Initialized researcher state: {init_result} ---"
            print(f"[INFO] {status}")
            logger.info(status)
        except Exception as e:
            status = f"Failed to initialize researcher state: {e}"
            print(f"[ERROR] {status}")
            logger.error(status)
            return {"status": status}

    # Define Planner Agent
    with open("prompts/planner_prompt.txt", "r") as f:
        planner_prompt_template = f.read()
    planner_prompt = ChatPromptTemplate.from_template(planner_prompt_template)
    try:
        planner_agent_runnable = create_openai_tools_agent(state['model'], [], planner_prompt)
        planner_executor = AgentExecutor(agent=planner_agent_runnable, tools=[], verbose=True)
    except Exception as e:
        status = f"Failed to create planner agent executor: {e}"
        print(f"[ERROR] {status}")
        logger.error(status)
        return {"status": status}

    # Get the google_search tool
    google_search_tool = next((tool for tool in state['mcp_tools'] if tool.name == 'google_search'), None)
    if not google_search_tool:
        status = "google_search tool not found."
        print(f"[ERROR] {status}")
        logger.error(status)
        return {"status": status}

    # Main control loop
    try:
        if isinstance(gaps_todo, list) and gaps_todo:
            for current_gap in list(gaps_todo):
                gap_id = current_gap['gap_id']
                research_topic = current_gap['research_topic']
                all_searches_for_gap = []

                status = f"Starting research for gap: {gap_id}, research topic: {research_topic}"
                print(f"[INFO] {status}")
                logger.info(status)

                try:
                    # 1. Planning Step
                    status = f"Invoking planner for gap {gap_id}."
                    print(f"[INFO] {status}")
                    logger.info(status)
                    planner_result = await planner_executor.ainvoke({"input": research_topic})
                    planner_output = extract_and_clean_json(planner_result.get("output", ""))
                    planned_searches = planner_output.get("searches", [])
                    status = f"Planner for gap {gap_id} returned {len(planned_searches)} searches."
                    print(f"[INFO] {status}")
                    logger.info(status)

                    # 2. Execution Step (Sub-loop)
                    for i, planned_search in enumerate(planned_searches):
                        query = planned_search.get("query")
                        rationale = planned_search.get("rationale")
                        parameters = planned_search.get("parameters", {})
                        if not query:
                            continue
                        
                        # Add the query to the parameters if it's not already there
                        if 'query' not in parameters:
                            parameters['query'] = query

                        try:
                            status = f"Executing search for gap {gap_id}, with parameters: {parameters}"
                            print(f"[INFO] {status}")
                            logger.info(status)
                            
                            # Directly call the google_search tool
                            search_results = await google_search_tool.arun(parameters)

                            search_id = f"search_{gap_id}_{i+1}"
                            
                            search_object = {
                                "search_id": search_id,
                                "rationale": rationale,
                                "parameters": parameters,
                                "results": search_results
                            }
                            all_searches_for_gap.append(search_object)
                            
                            status = f"Search for gap {gap_id} finished for query: '{query}'"
                            print(f"[INFO] {status}")
                            logger.info(status)
                        except Exception as e:
                            status = f"Search for gap {gap_id}, query '{query}' failed: {e}"
                            print(f"[ERROR] {status}")
                            logger.error(status)
                            continue # Continue to the next query

                    # 3. Update Step
                    status = f"Preparing to update report for gap {gap_id} with {len(all_searches_for_gap)} searches."
                    print(f"[INFO] {status}")
                    logger.info(status)
                    try:
                        update_researcher_report(report_id, gap_id, all_searches_for_gap)
                        gaps_complete.append(gap_id)
                        gaps_todo = [g for g in gaps_todo if g.get("gap_id") != gap_id]
                        status = f"Updated researcher report for gap: {gap_id}"
                        print(f"[INFO] {status}")
                        logger.info(status)
                    except Exception as e:
                        status = f"Error updating report for gap {gap_id}: {e}"
                        print(f"[ERROR] {status}")
                        logger.error(status, exc_info=True)
                        continue # Continue to the next gap

                    status = f"--- Successfully completed research and report writing for gap: {gap_id} ---"
                    print(f"[INFO] {status}")
                    logger.info(status)

                except Exception as e:
                    status = f"An unexpected error occurred while processing gap {gap_id}: {e}"
                    print(f"[ERROR] {status}")
                    logger.error(status, exc_info=True)
                    continue # Continue to the next gap
    
    except Exception as e:
        final_status = f"Main loop failed: {e}"
        print(f"[ERROR] {final_status}")
        logger.error(final_status, exc_info=True)

    if not final_status:
        final_status = f"Successfully and incrementally completed researcher report with ID {report_id} and wrote report to DB."
        print(f"[INFO] {final_status}")
        logger.info(final_status)

    return {
        "status": final_status,
        "researcher_report_id": report_id,
        "researcher_gaps_todo": gaps_todo,
        "researcher_gaps_complete": gaps_complete
    }