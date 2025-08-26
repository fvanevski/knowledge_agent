# sub_agents/curator.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from state import AgentState
from db_utils import initialize_curator, update_curator_report, extract_and_clean_json
from terminal_utils import print_colorful_break

async def curator_agent_node(state: AgentState):
    """Orchestrates the curation process."""
    print_colorful_break("CURATOR")
    logger = state['logger']

    report_id = state.get("curator_report_id")
    searches_todo = []
    curator_urls_for_ingestion = []
    curator_url_ingestion_status = []
    final_status = None

    # One-time initialization of the curator state
    if not report_id:
        try:
            init_result = initialize_curator(state['timestamp'])
            report_id = init_result.get("curator_report_id")
            searches_todo = init_result.get("curator_searches_todo")
            status = f"--- Initialized curator state: {init_result} ---"
            logger.info(status)
        except Exception as e:
            status = f"Failed to initialize curator: {e}"
            logger.error(status, exc_info=True)
            return {"status": status}

    # Create the specialized agent for search ranking
    search_ranker_prompt = ChatPromptTemplate.from_template(open("prompts/search_ranker_prompt.txt", "r").read())
    search_ranker_tools = [t for t in state['mcp_tools'] if t.name in ["google_search", "fetch"]]
    status = f"Attempting to invoke search ranker agent executor with tools: {search_ranker_tools}"
    logger.info(status)
    try:
        agent_runnable = create_openai_tools_agent(state['model'], search_ranker_tools, search_ranker_prompt)
        executor = AgentExecutor(agent=agent_runnable, tools=search_ranker_tools, verbose=True)
    except Exception as e:
        status = f"Failed to create search ranker agent executor: {e}"
        logger.error(status, exc_info=True)
        return {"status": status}

    # Main control loop for search ranking
    if isinstance(searches_todo, list) and searches_todo:
        for item in searches_todo:
            current_search = item.get("search", {})
            research_topic = item.get("research_topic", {})
            
            search_id = current_search.get("search_id", "unknown_search")
            search_rationale = current_search.get('rationale', '')
            search_results = current_search.get('results', [])

            status = f"Processing search: {search_id}"
            logger.info(status)
            try:
                search_ranker_result = await executor.ainvoke({
                    "input": {
                        "research_topic": research_topic,
                        "search_results": search_results,
                        "search_rationale": search_rationale
                    }
                })
                raw_search_ranker_result = search_ranker_result.get('output', '')
                status = f"Curator agent for search {search_id} completed. Raw output: {raw_search_ranker_result}"
                logger.info(status)
                
                try:
                    json_output = extract_and_clean_json(raw_search_ranker_result)
                    ranked_urls = json_output.get("ranked_urls", [])
                    approved_urls = [url['url'] for url in ranked_urls if url.get('status') == 'approved']
                    curator_urls_for_ingestion.extend(approved_urls)
                    status = f"Successfully parsed ranked URLs for search {search_id}: {len(approved_urls)} approved."
                    logger.info(status)
                except Exception as e:
                    status = f"Failed to parse ranked URLs for search {search_id}: {e}"
                    logger.error(status, exc_info=True)
                    continue

                status = f"Preparing to update report for search {search_id} with {len(approved_urls)} URLs."
                logger.info(status)
                try:
                    tool_input = {
                        "curator_report_id": report_id,
                        "job": "urls_for_ingestion",
                        "results": approved_urls
                    }
                    update_curator_report(tool_input)
                    status = f"Updated report for search {search_id} with {len(approved_urls)} URLs."
                    logger.info(status)
                except Exception as e:
                    status = f"Failed to update report for search {search_id}: {e}"
                    logger.error(status, exc_info=True)
                    continue

                status = f"Successfully updated report for search {search_id} with {len(approved_urls)} URLs."
                logger.info(status)

            except Exception as e:
                status = f"Curator agent search ranking for search {search_id} failed: {e}"
                logger.error(status, exc_info=True)
                continue

    status = f"Successfully completed ranking of all searches for report: {report_id}"
    logger.info(status)

    # Create the specialized agent for url ingestion
    ingester_prompt = ChatPromptTemplate.from_template(open("prompts/ingester_prompt.txt", "r").read())
    ingester_tools = [t for t in state['mcp_tools'] if t.name in ["fetch", "documents_upload_file", "documents_upload_files", "documents_insert_text", "documents_pipeline_status"]]
    status = f"Attempting to invoke url ingestion agent executor with tools: {ingester_tools}"
    logger.info(status)
    try:
        agent_runnable = create_openai_tools_agent(state['model'], ingester_tools, ingester_prompt)
        executor = AgentExecutor(agent=agent_runnable, tools=ingester_tools, verbose=True)
    except Exception as e:
        status = f"Failed to create url ingestion agent executor: {e}"
        logger.error(status, exc_info=True)
        return {"status": status}

   # Main control for url ingestion
    task = "Ingest the URLs in `{urls_for_ingestion}` and return the ingestion status for each URL."
    status = f"Attempting to run agent executor for url ingestion"
    logger.info(status)
    try:
        # The executor handles the entire loop of tool calls and reasoning.
        ingestion_result = await executor.ainvoke({
            "input": task,
            "urls_for_ingestion": curator_urls_for_ingestion
        })
        raw_ingestion_result = ingestion_result.get('output', '')
        status = f"Curator agent ingestion for report {report_id} completed.\nRaw output: {raw_ingestion_result}"
        logger.info(status)
        
        try:
            json_output = extract_and_clean_json(raw_ingestion_result)
            curator_url_ingestion_status = json_output.get("url_ingestion_status", [])
            status = f"Successfully parsed URL ingestion status: {curator_url_ingestion_status}."
            logger.info(status)
        except Exception as e:
            status = f"Failed to parse URL ingestion status: {e}"
            logger.error(status, exc_info=True)
            return {"status": status}

        status = f"Preparing to update report: {report_id} with ingestion status for {len(curator_url_ingestion_status)} URLs."
        logger.info(status)
        try:
            tool_input = {
                "curator_report_id": report_id,
                "job": "url_ingestion_status",
                "results": curator_url_ingestion_status
            }
            update_curator_report(tool_input)
            status = f"Updated report {report_id} with ingestions status for {len(curator_url_ingestion_status)} URLs."
            logger.info(status)
        except Exception as e:
            status = f"Failed to update report {report_id}: {e}"
            logger.error(status, exc_info=True)
            return {"status": status}

        status = f"Successfully updated report {report_id} with {len(curator_url_ingestion_status)} URLs."
        logger.info(status)

    except Exception as e:
        final_status = f"Curator agent failed to run ingestion of ranked URLs: {e}"
        logger.error(final_status, exc_info=True)
    
    if not final_status:
        final_status = f"Curator successfully ranked and ingested URLs, generating curator report summary written to file `state/curator_report.json`"
        logger.info(status)

    return {
        "status": final_status,
        "curator_report_id": report_id,
        "curator_urls_for_ingestion": curator_urls_for_ingestion,
        "curator_url_ingestion_status": curator_url_ingestion_status
    }