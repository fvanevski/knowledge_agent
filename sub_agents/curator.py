# sub_agents/curator.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from state import AgentState
from db_utils import initialize_curator, update_curator_report, extract_and_clean_json

async def curator_agent_node(state: AgentState):
    """Orchestrates the curation process."""
    logger = state['logger']

    report_id = state.get("curator_report_id")
    searches_todo = []
    curator_urls_for_ingestion = []
    curator_url_ingestion_status = []
    # One-time initialization of the curator state
    if not report_id:
        try:
            init_result = initialize_curator(state['timestamp'])
            report_id = init_result.get("curator_report_id")
            searches_todo = init_result.get("curator_searches_todo")
            status = f"--- Initialized curator state: {init_result} ---"
            print(f"[INFO] {status}")
            logger.info(status)
        except Exception as e:
            status = f"Failed to initialize curator: {e}"
            print(f"[ERROR] {status}")
            logger.error(status, exc_info=True)
            return {"status": status}

    # Create the specialized agent for search ranking
    search_ranker_prompt = ChatPromptTemplate.from_template(open("prompts/search_ranker_prompt.txt", "r").read())
    search_ranker_tools = [t for t in state['mcp_tools'] if t.name in ["google_search", "fetch"]]
    status = f"Attempting to invoke search ranker agent executor with tools: {search_ranker_tools}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        agent_runnable = create_openai_tools_agent(state['model'], search_ranker_tools, search_ranker_prompt)
        executor = AgentExecutor(agent=agent_runnable, tools=search_ranker_tools, verbose=True)
    except Exception as e:
        status = f"Failed to create search ranker agent executor: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        return {"status": status}

    # Main control loop for search ranking
    task = "Rank the search results in `{search_results}` based on relevance to the rationale in `{search_rationale}`"
    if isinstance(searches_todo, list) and searches_todo:
        for current_search in searches_todo:
            search_rationale = current_search['rationale']
            search_results = current_search['results']

            status = f"Processing search: {current_search['search_id']}"
            print(f"[INFO] {status}")
            logger.info(status)
            try:
                search_ranker_result = await executor.ainvoke({
                    "input": task,
                    "search_rationale": search_rationale,
                    "search_results": search_results
                })
                raw_search_ranker_result = search_ranker_result.get('output', '')
                status = f"Curator agent for search {current_search['search_id']} completed. Raw output: {raw_search_ranker_result}"
                print(f"[INFO] {status}")
                logger.info(status)
                
                try:
                    json_output = extract_and_clean_json(raw_search_ranker_result)
                    ranked_urls = json_output.get("urls_for_ingestion", [])
                    curator_urls_for_ingestion.extend(ranked_urls)
                    status = f"Successfully parsed ranked URLs for search {current_search['search_id']}: {ranked_urls}."
                    print(f"[INFO] {status}")
                    logger.info(status)
                except Exception as e:
                    status = f"Failed to parse ranked URLs for search {current_search['search_id']}: {e}"
                    print(f"[ERROR] {status}")
                    logger.error(status, exc_info=True)
                    continue

                status = f"Preparing to update report for search {current_search['search_id']} with {len(ranked_urls)} URLs."
                print(f"[INFO] {status}")
                logger.info(status)
                try:
                    tool_input = {
                        "curator_report_id": report_id,
                        "job": "urls_for_ingestion",
                        "results": ranked_urls
                    }
                    update_curator_report(tool_input)
                    status = f"Updated report for search {current_search['search_id']} with {len(ranked_urls)} URLs."
                    print(f"[INFO] {status}")
                    logger.info(status)
                except Exception as e:
                    status = f"Failed to update report for search {current_search['search_id']}: {e}"
                    print(f"[ERROR] {status}")
                    logger.error(status, exc_info=True)
                    continue

                status = f"Successfully updated report for search {current_search['search_id']} with {len(ranked_urls)} URLs."
                print(f"[INFO] {status}")
                logger.info(status)

            except Exception as e:
                status = f"Curater agent search ranking for search {current_search['search_id']} failed: {e}"
                print(f"[ERROR] {status}")
                logger.error(status, exc_info=True)
                continue

    status = f"Successfully completed ranking of all searches for report: {report_id}"
    print(f"[INFO] {status}")
    logger.info(status)

    # Create the specialized agent for url ingestion
    ingester_prompt = ChatPromptTemplate.from_template(open("prompts/ingester_prompt.txt", "r").read())
    ingester_tools = [t for t in state['mcp_tools'] if t.name in ["fetch", "documents_upload_file", "documents_upload_files", "documents_insert_text", "documents_pipeline_status"]]
    status = f"Attempting to invoke url ingestion agent executor with tools: {ingester_tools}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        agent_runnable = create_openai_tools_agent(state['model'], ingester_tools, ingester_prompt)
        executor = AgentExecutor(agent=agent_runnable, tools=ingester_tools, verbose=True)
    except Exception as e:
        status = f"Failed to create url ingestion agent executor: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        return {"status": status}

   # Main control for url ingestion
    task = "Ingest the URLs in `{urls_for_ingestion}` and return the ingestion status for each URL."
    status = f"Attempting to run agent executor for url ingestion"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        # The executor handles the entire loop of tool calls and reasoning.
        ingestion_result = await executor.ainvoke({
            "input": task,
            "urls_for_ingestion": curator_urls_for_ingestion
        })
        raw_ingestion_result = ingestion_result.get('output', '')
        status = f"Curator agent ingestion for report {report_id} completed.\nRaw output: {raw_ingestion_result}"
        print(f"[INFO] {status}")
        logger.info(status)
        
        try:
            json_output = extract_and_clean_json(raw_ingestion_result)
            curator_url_ingestion_status = json_output.get("url_ingestion_status", [])
            status = f"Successfully parsed URL ingestion status: {curator_url_ingestion_status}."
            print(f"[INFO] {status}")
            logger.info(status)
        except Exception as e:
            status = f"Failed to parse URL ingestion status: {e}"
            print(f"[ERROR] {status}")
            logger.error(status, exc_info=True)
            return {"status": status}

        status = f"Preparing to update report: {report_id} with ingestion status for {len(curator_url_ingestion_status)} URLs."
        print(f"[INFO] {status}")
        logger.info(status)
        try:
            tool_input = {
                "curator_report_id": report_id,
                "job": "url_ingestion_status",
                "results": curator_url_ingestion_status
            }
            update_curator_report(tool_input)
            status = f"Updated report {report_id} with ingestions status for {len(curator_url_ingestion_status)} URLs."
            print(f"[INFO] {status}")
            logger.info(status)
        except Exception as e:
            status = f"Failed to update report {report_id}: {e}"
            print(f"[ERROR] {status}")
            logger.error(status, exc_info=True)
            return {"status": status}

        status = f"Successfully updated report {report_id} with {len(curator_url_ingestion_status)} URLs."
        print(f"[INFO] {status}")
        logger.info(status)

    except Exception as e:
        final_status = f"Curator agent failed to run ingestion of ranked URLs: {e}"
        print(f"[ERROR] {final_status}")
        logger.error(final_status, exc_info=True)
    
    if not final_status:
        final_status = f"Curator successfully ranked and ingested URLs, generating curator report summary written to file `state/curator_report.json`"
        print(f"[INFO] {status}")
        logger.info(status)

    return {
        "status": status,
        "curator_report_id": report_id,
        "curator_urls_for_ingestion": curator_urls_for_ingestion,
        "curator_url_ingestion_status": curator_url_ingestion_status
    }
