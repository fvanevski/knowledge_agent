# sub_agents/researcher.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from state import AgentState
from db_utils import initialize_researcher, update_researcher_report, extract_and_clean_json, get_document_object, update_document_object
from tools import process_url
from terminal_utils import print_colorful_break

async def researcher_agent_node(state: AgentState):
    """The main node for the researcher workflow."""
    print_colorful_break("RESEARCHER")
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
            logger.info(status)
        except Exception as e:
            status = f"Failed to initialize researcher state: {e}"
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
        logger.error(status)
        return {"status": status}

    # Define Refiner Agent
    with open("prompts/refiner_prompt.txt", "r") as f:
        refiner_prompt_template = f.read()
    refiner_prompt = ChatPromptTemplate.from_template(refiner_prompt_template)
    try:
        refiner_agent_runnable = create_openai_tools_agent(state['model'], [], refiner_prompt)
        refiner_executor = AgentExecutor(agent=refiner_agent_runnable, tools=[], verbose=True)
    except Exception as e:
        status = f"Failed to create refiner agent executor: {e}"
        logger.error(status)
        return {"status": status}

    # Define Summarizer Agent
    with open("prompts/summarizer_prompt.txt", "r") as f:
        summarizer_prompt_template = f.read()
    summarizer_prompt = ChatPromptTemplate.from_template(summarizer_prompt_template)
    try:
        summarizer_agent_runnable = create_openai_tools_agent(state['model'], [], summarizer_prompt)
        summarizer_executor = AgentExecutor(agent=summarizer_agent_runnable, tools=[], verbose=True)
    except Exception as e:
        status = f"Failed to create summarizer agent executor: {e}"
        logger.error(status)
        return {"status": status}

    # Get the tools
    google_search_tool = next((tool for tool in state['mcp_tools'] if tool.name == 'google_search'), None)
    if not google_search_tool:
        status = "google_search tool not found."
        logger.error(status)
        return {"status": status}
    

    # Main control loop
    try:
        if isinstance(gaps_todo, list) and gaps_todo:
            for current_gap in list(gaps_todo):
                gap_id = current_gap['gap_id']
                research_topic = current_gap['research_topic']
                all_searches_for_gap = []

                research_topic_title = research_topic.get('title', 'No Title')
                status = f"Starting research for gap: {gap_id}, research topic: {research_topic_title}"
                logger.info(status)

                try:
                    # 1. Planning Step
                    status = f"Invoking planner for gap {gap_id}."
                    logger.info(status)
                    planner_result = await planner_executor.ainvoke({"input": research_topic})
                    planner_output = extract_and_clean_json(planner_result.get("output", ""))
                    planned_searches = planner_output.get("searches", [])
                    status = f"Planner for gap {gap_id} returned {len(planned_searches)} searches."
                    logger.info(status)

                    # 2. Initial Execution Step
                    for planned_search in planned_searches:
                        query = planned_search.get("query")
                        rationale = planned_search.get("rationale")
                        parameters = planned_search.get("parameters", {})
                        search_id = planned_search.get("search_id")
                        if not query:
                            continue
                        
                        if 'query' not in parameters:
                            parameters['query'] = query

                        try:
                            status = f"Executing search for gap {gap_id}, with parameters: {parameters}"
                            logger.info(status)
                            
                            raw_search_results = await google_search_tool.arun(parameters)
                            search_results = extract_and_clean_json(raw_search_results)

                            for i, result in enumerate(search_results):
                                url = result.get('url')
                                if url:
                                    logger.info(f"Attempting document store initialzation for URL: {url}")
                                    try:
                                        url_id, url_status = await process_url(url, logger)                                        
                                    except Exception as e:
                                        status = f"Error processing URL {url}: {e}"
                                        logger.error(status, exc_info=True)
                                        continue                                    
                                    search_results[i]['url_id'] = url_id
                                    if url_status == "new":
                                        status=f"New URL {url} added to the database with ID: {url_id}."
                                    else:
                                        status = f"URL {url} already exists in the database with ID: {url_id}."
                                    logger.info(status)
                                    
                            search_object = {
                                "search_id": search_id,
                                "rationale": rationale,
                                "parameters": parameters,
                                "results": search_results
                            }
                            all_searches_for_gap.append(search_object)
                            
                            status = f"Search for gap {gap_id} finished for query: '{query}'"
                            logger.info(status)
                            
                        except Exception as e:
                            status = f"Search for gap {gap_id}, query '{query}' failed: {e}"
                            logger.error(status)
                            continue

                    # 3. Refinement Step
                    status = f"Invoking refiner for gap {gap_id}."
                    logger.info(status)
                    refiner_input = {"research_topic": research_topic, "search_results": all_searches_for_gap}
                    refiner_result = await refiner_executor.ainvoke({"input": refiner_input})
                    refiner_output = extract_and_clean_json(refiner_result.get("output", ""))
                    
                    status_check = ""
                    if isinstance(refiner_output, dict):
                        status_check = refiner_output.get("status", "").lower()
                    elif isinstance(refiner_output, str):
                        if "insufficient" in refiner_output.lower():
                            status_check = "insufficient"

                    if status_check == "insufficient":
                        refined_searches = []
                        if isinstance(refiner_output, dict):
                            refined_searches = refiner_output.get("searches", [])
                        status = f"Refiner for gap {gap_id} returned {len(refined_searches)} new searches."
                        logger.info(status)

                        # 4. Refined Execution Step
                        for refined_search in refined_searches:
                            query = refined_search.get("query")
                            rationale = refined_search.get("rationale")
                            parameters = refined_search.get("parameters", {})
                            search_id = refined_search.get("search_id")
                            if not query:
                                continue

                            if 'query' not in parameters:
                                parameters['query'] = query
                            
                            try:
                                status = f"Executing refined search for gap {gap_id}, with parameters: {parameters}"
                                logger.info(status)

                                raw_search_results = await google_search_tool.arun(parameters)
                                search_results = extract_and_clean_json(raw_search_results)

                                for i, result in enumerate(search_results):
                                    url = result.get('url')
                                    if url:
                                        logger.info(f"Attempting document store initialzation for URL: {url}")
                                        try:
                                            url_id, url_status = await process_url(url, logger)                                        
                                        except Exception as e:
                                            status = f"Error processing URL {url}: {e}"
                                            logger.error(status, exc_info=True)
                                            continue                                    
                                        search_results[i]['url_id'] = url_id
                                        if url_status == "new":
                                            status=f"New URL {url} added to the database with ID: {url_id}."
                                        else:
                                            status = f"URL {url} already exists in the database with ID: {url_id}."
                                        logger.info(status)

                                search_object = {
                                    "search_id": search_id,
                                    "rationale": rationale,
                                    "parameters": parameters,
                                    "results": search_results
                                }
                                all_searches_for_gap.append(search_object)

                                status = f"Refined search for gap {gap_id} finished for query: '{query}'"
                                logger.info(status)
                            except Exception as e:
                                status = f"Refined search for gap {gap_id}, query '{query}' failed: {e}"
                                logger.error(status)
                                continue
                    else:
                        status = f"Refiner for gap {gap_id} deemed results sufficient."
                        logger.info(status)

                    # 5. Summarization Step
                    status = f"Starting summarization for gap {gap_id}."
                    logger.info(status)
                    for search in all_searches_for_gap:
                        for i, result in enumerate(search.get('results', [])):
                            url = result.get('url')
                            url_id = result.get('url_id')
                            url_summary = get_document_object(url_id, type="summary")
                            if url_summary:
                                logger.info(f"Skipping summarization for url_id: {url_id}, summary already exists.")
                                continue
                            else:
                                markdown_content = get_document_object(url_id, type="markdown_content")
                                if not markdown_content or markdown_content.startswith("[MARKDOWN_GENERATION_FAILED"):
                                    logger.info(f"Skipping summarization for url_id: {url_id}, no valid markdown content available.")
                                    continue

                                logger.info(f"Attempting summary for url_id: {url_id}")                               
                                try:
                                    summarizer_result = await summarizer_executor.ainvoke({"input": markdown_content})
                                    summary_output = extract_and_clean_json(summarizer_result.get("output", ""))
                                    
                                    if isinstance(summary_output, dict):
                                        summary = summary_output.get('summary')
                                    else:
                                        summary = str(summary_output)

                                    update_document_object(url_id, type="summary", object=summary)
                                    status = f"Successfully summarized and updated document for url_id: {url_id}"
                                    logger.info(status)
                                except Exception as e:
                                    status = f"Error summarizing url_id {url_id}: {e}"
                                    logger.error(status, exc_info=True)
                                    continue

                    # 6. Update Step
                    status = f"Preparing to update report for gap {gap_id} with {len(all_searches_for_gap)} searches."
                    logger.info(status)
                    try:
                        update_researcher_report(report_id, gap_id, all_searches_for_gap)
                        gaps_complete.append(gap_id)
                        gaps_todo = [g for g in gaps_todo if g.get("gap_id") != gap_id]
                        status = f"Updated researcher report for gap: {gap_id}"
                        logger.info(status)
                    except Exception as e:
                        status = f"Error updating report for gap {gap_id}: {e}"
                        logger.error(status, exc_info=True)
                        continue

                    status = f"--- Successfully completed research and report writing for gap: {gap_id} ---"
                    logger.info(status)

                except Exception as e:
                    status = f"An unexpected error occurred while processing gap {gap_id}: {e}"
                    logger.error(status, exc_info=True)
                    continue
    
    except Exception as e:
        final_status = f"Main loop failed: {e}"
        logger.error(final_status, exc_info=True)

    if not final_status:
        final_status = f"Successfully and incrementally completed researcher report with ID {report_id} and wrote report to DB."
        logger.info(final_status)

    return {
        "status": final_status,
        "researcher_report_id": report_id,
        "researcher_gaps_todo": gaps_todo,
        "researcher_gaps_complete": gaps_complete
    }
