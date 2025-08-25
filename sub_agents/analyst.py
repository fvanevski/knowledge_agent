# analyst.py
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool, ToolException
from langchain_core.messages import AIMessage
import json
import os
import re
from state import AgentState
from tools import save_analyst_report

def _extract_and_clean_json_analyst(llm_output: str) -> dict:
    """
    Extracts and cleans a JSON object from the Analyst LLM's output.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    status = f"Extracting and cleaning JSON from analyst LLM output"
    print(status)
    logger.info(status)
    # Use a regex to find the JSON blob
    match = re.search(r"\{.*\}", llm_output, re.DOTALL)
    status = f"Regex match for JSON: {match}"
    print(status)
    logger.info(status)
    if not match:
        status = f"No JSON object found in the output."
        print(status)
        logger.error(status)
        raise ValueError(status)

    json_string = match.group(0)
    status = f"Extracted JSON string: {json_string}"
    print(status)
    logger.info(status)

    # Try to parse the JSON
    status = f"Attempting to parse JSON: {json_string}"
    print(status)
    logger.info(status)
    try:
        parsed_json = json.loads(json_string)
        status = f"Successfully parsed JSON: {parsed_json}"
        print(status)
        logger.info(status)
        return parsed_json
    except json.JSONDecodeError as e:
        status = f"Failed to parse JSON: {e}"
        print(status)
        logger.error(status)
        raise ValueError(status)

async def analyst_agent_node(state: AgentState):
    """This node encapsulates the entire agent execution loop."""
    logger = state['logger']
    
    if not state.get("analyst_report_id"):
        timestamp = state['timestamp']
        report_id = f"ana_{timestamp.replace('-', '').replace(':', '').replace('T', '_').split('.')[0]}"
        state["analyst_report_id"] = report_id
        status = f"Initialized analyst report with ID: {report_id}"
        print(f"[INFO] {status}")
        logger.info(status)

    analyst_prompt = ChatPromptTemplate.from_template(open("prompts/analyst_prompt.txt", "r").read())    
    analyst_tools = [t for t in state['mcp_tools'] if t.name in ["query", "graphs_get", "graph_labels", "google_search", "fetch"]]

    status = f"Attempting to invoke analyst agent executor with tools: {analyst_tools}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        agent_runnable = create_openai_tools_agent(state['model'], analyst_tools, analyst_prompt)
        executor = AgentExecutor(agent=agent_runnable, tools=analyst_tools, verbose=True)
    except Exception as e:
        status = f"Failed to create agent executor: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        return {"status": status}

    status = f"Attempting to run agent executor with input: {state['messages'][0].content}"
    print(f"[INFO] {status}")
    logger.info(status)
    try:
        # The executor handles the entire loop of tool calls and reasoning.
        analyst_result = await executor.ainvoke({
            "input": state['messages'][0].content,
            "analyst_report_id": state.get("analyst_report_id", "")
        })
        final_output = analyst_result.get('output', '')
    except Exception as e:
        status = f"AgentExecutor failed: {e}"
        print(f"[ERROR] {status}")
        logger.error(status, exc_info=True)
        final_output = f"Error in Analyst Agent: {e}"

    # The node returns a single AIMessage with the final report.
    # This message is then passed to the next node in the graph.
    status = f"Successfully generated analyst report: {final_output}"
    print(f"[INFO] {status}")
    logger.info(status)
    return {"messages": state['messages'] + [AIMessage(content=final_output)]}

def save_analyst_report_node(state: AgentState):
    """Saves the final report from the last AI message."""
    logger = state['logger']
    final_message_from_agent = state['messages'][-1]

    status = f"--- Saving Analyst Report ---\n{final_message_from_agent.content}"
    print(f"[INFO] {status}")
    logger.info(status)

    try:
        report_json = _extract_and_clean_json_analyst(final_message_from_agent.content)
        if 'report_id' not in report_json:
            report_json['report_id'] = state.get('analyst_report_id', 'unknown_id')
        save_analyst_report.invoke({"analyst_report": json.dumps(report_json)})
        status = f"Successfully saved analyst report with ID {report_json.get('report_id')}"
        print(f"[INFO] {status}")
        logger.info(status)
    except (ValueError, KeyError) as e:
        status = f"Error processing or saving analyst report: {e}"
        print(f"[ERROR] {status}")
        logger.error(status)
    
    return {"messages": state['messages'] + [AIMessage(content=status)]}
