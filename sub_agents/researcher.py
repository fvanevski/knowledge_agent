# sub_agents/researcher.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from state import AgentState
from db_utils import initialize_researcher, update_researcher_report, extract_and_clean_json

async def researcher_agent_node(state: AgentState):
    """The main node for the researcher workflow."""
    logger = state['logger']
    report_id = state.get("researcher_report_id")
    gaps_todo = state.get("researcher_gaps_todo", [])
    gaps_complete = state.get("researcher_gaps_complete", [])

    if not report_id:
        try:
            init_result = initialize_researcher_report(state['timestamp'])
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

    with open("prompts/searcher_prompt.txt", "r") as f:
        searcher_prompt_template = f.read()
    
    searcher_prompt = ChatPromptTemplate.from_template(searcher_prompt_template)
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
    try:
        if isinstance(gaps_todo, list) and gaps_todo:
            for current_gap in list(gaps_todo):
                gap_id = current_gap['gap_id']
                research_topic = current_gap['research_topic']

                status = f"Starting research for gap: {gap_id}, research topic: {research_topic}"
                print(f"[INFO] {status}")
                logger.info(status)

                try:
                    # Invoke the specialized agent for just ONE gap
                    searcher_result = await executor.ainvoke({"input": current_gap['research_topic']})
                    status = f"Agent for gap {gap_id} finished. Raw output:\n{searcher_result.get('output')}"
                    print(f"[INFO] {status}")
                    logger.info(status)

                    # The node, not the agent, saves the results
                    try:
                        # Use the new helper function to extract and clean the JSON
                        json_output = extract_and_clean_json(searcher_result.get("output", ""))
                        searches = json_output.get("searches", [])
                        status = f"Successfully parsed searches for gap {gap_id}: {searches}"
                        print(f"[INFO] {status}")
                        logger.info(status)

                    except Exception as e:
                        status = f"Agent for gap {gap_id} returned invalid JSON: {searcher_result.get('output')}. Error: {e}"
                        print(f"[ERROR] {status}")
                        logger.error(status)
                        continue

                    status = f"Preparing to update report for gap {gap_id} with {len(searches)} searches"
                    print(f"[INFO] {status}")
                    logger.info(status)
                    try:
                        update_researcher_report(report_id, gap_id, searches)
                        gaps_complete.append(gap_id)
                        gaps_todo = [g for g in gaps_todo if g.get("gap_id") != gap_id]
                        status = f"Updated researcher report for gap: {gap_id}"
                        print(f"[INFO] {status}")
                        logger.info(status)
                    except Exception as e:
                        status = f"Error processing gap {gap_id}: {e}"
                        print(f"[ERROR] {status}")
                        logger.error(status, exc_info=True)
                        continue

                    status = f"--- Successfully completed research and report writing for gap: {gap_id} ---"
                    print(f"[INFO] {status}")
                    logger.info(status)

                except Exception as e:
                    status = f"An unexpected error occurred while processing gap {gap_id}: {e}"
                    print(f"[ERROR] {status}")
                    logger.error(status, exc_info=True)
                    continue

    except Exception as e:
            final_status = f"AgentExecutor failed: {e}"
            print(f"[ERROR] {final_status}")
            logger.error(final_status, exc_info=True)

    if not final_status:
        final_status = f"Successfully and incrementally completed researcher report with ID {report_id} and wrote report to DB."
        print(f"[INFO] {final_status}")
        logger.info(final_status)

    return {
        "status": status,
        "researcher_report_id": report_id,
        "researcher_gaps_todo": gaps_todo,
        "researcher_gaps_complete": gaps_complete
    }
