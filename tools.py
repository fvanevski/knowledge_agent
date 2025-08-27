# tools.py
from langchain_core.tools import tool, ToolException
from db_utils import add_url_or_get_id, update_document_content
from utils import format_bytes
import requests
import io
import pdfplumber
from bs4 import BeautifulSoup
import html2text


@tool
def human_approval(plan: str) -> str:
    """
    Asks for human approval for a given plan.
    The plan is a string that describes the actions to be taken.
    Returns 'approved' or 'denied'.
    """
    import logging
    logger = logging.getLogger('KnowledgeAgent')

    status = f"PROPOSED PLAN:\n{plan}"
    print(f"\n[INFO] {status}")
    logger.info(f"{status}")
    try:
        response = input("Do you approve this plan? (y/n): ").lower()
        if response == 'y':
            status = "Approved."
            print(status)
            logger.info(status)
            return status
        status = "Denied."
        print(status)
        logger.info(status)
        return status
    except Exception as e:
        status = f"Error in human_approval: {e}"
        print(status)
        logger.error(status)
        raise ToolException(status)

def generate_markdown_from_raw(raw_document: bytes, content_type: str) -> str:
    """Generates markdown from a raw document based on its content type."""
    try:
        if "application/pdf" in content_type:
            with pdfplumber.open(io.BytesIO(raw_document)) as pdf:
                return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        elif "text/html" in content_type:
            soup = BeautifulSoup(raw_document, "html.parser")
            # You might want to add more sophisticated logic here to find the main content
            return html2text.html2text(soup.body.get_text())
        elif "text/plain" in content_type:
            return raw_document.decode("utf-8")
        else:
            return "[MARKDOWN_GENERATION_FAILED: Unsupported content type]"
    except Exception as e:
        return f"[MARKDOWN_GENERATION_FAILED: {e}]"

async def fetch_and_generate_markdown(url: str, logger):
    """Fetches raw content from a URL and generates markdown."""
    raw_document = b''
    markdown_content = ""
    try:
        logger.info(f"Downloading raw content from: {url}")
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        raw_document = response.content
        content_type = response.headers.get("Content-Type", "")
        logger.info(f"Successfully downloaded raw content for url: {url}\nFile size: {format_bytes(len(raw_document))}")
        
        markdown_content = generate_markdown_from_raw(raw_document, content_type)
        if "[MARKDOWN_GENERATION_FAILED" in markdown_content:
            logger.warning(f"Failed to generate markdown for url {url}: {markdown_content}")
        else:
            logger.info(f"Successfully generated markdown for url: {url}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download content from {url}: {e}")
        markdown_content = f"[MARKDOWN_GENERATION_FAILED: {e}]"
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing {url}: {e}")
        markdown_content = f"[MARKDOWN_GENERATION_FAILED: {e}]"
        
    return raw_document, markdown_content

async def process_url(url: str, logger):
    """Downloads raw content for each URL in the search results and stores it in the database."""
    url_id, url_status = add_url_or_get_id(url)
    if url_status == "existing":
        return url_id, url_status
    
    raw_document, markdown_content = await fetch_and_generate_markdown(url, logger)

    if raw_document or markdown_content:
        logger.info(f"Updating document content for url_id: {url_id}")
        try:
            update_document_content(url_id, raw_document, markdown_content)
            logger.info(f"Successfully updated document content for url_id: {url_id}")
        except Exception as e:
            status = f"Failed to update document content for url_id {url_id}: {e}"
            logger.error(status)

    return url_id, url_status