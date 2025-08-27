# tools.py
from langchain_core.tools import tool, ToolException
from db_utils import add_url_or_get_id, update_document_content
from utils import format_bytes
import requests
import io
import pdfplumber
from playwright.async_api import async_playwright
import trafilatura
from trafilatura.settings import use_config


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

async def fetch_and_generate_markdown(url: str, logger):
    """Fetches raw content from a URL and generates markdown using a hybrid approach."""
    raw_document = b''
    markdown_content = ""
    MIN_CONTENT_LENGTH = 200 # Minimum character length to be considered valid content

    try:
        # Use a HEAD request to check the content type first
        head_response = requests.head(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        head_response.raise_for_status()
        content_type = head_response.headers.get("Content-Type", "")

        if "text/html" in content_type:
            # 1. Try Trafilatura first
            logger.info(f"Attempting to extract content with Trafilatura from: {url}")
            config = use_config()
            config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")
            downloaded_html = trafilatura.fetch_url(url)
            if downloaded_html:
                raw_document = downloaded_html.encode('utf-8')
                markdown_content = trafilatura.extract(
                    downloaded_html,
                    config=config,
                    include_comments=False,
                    include_tables=True,
                )
            
            # 2. Validate output and fallback to Playwright if necessary
            if not markdown_content or len(markdown_content) < MIN_CONTENT_LENGTH:
                logger.warning(f"Trafilatura extraction failed or content too short. Falling back to Playwright for: {url}")
                async with async_playwright() as p:
                    browser = await p.chromium.launch()
                    page = await browser.new_page()
                    await page.goto(url, wait_until="networkidle", timeout=15000)
                    raw_document = (await page.content()).encode('utf-8')
                    # Use a robust JS evaluation to get main content text
                    markdown_content = await page.evaluate('''() => {
                        const main = document.querySelector('main, #main, #content, [role="main"]');
                        return main ? main.innerText : document.body.innerText;
                    }''')
                    await browser.close()
                logger.info(f"Successfully fetched content with Playwright for url: {url}")
            else:
                logger.info(f"Successfully extracted content with Trafilatura for url: {url}")

        elif "application/pdf" in content_type:
            logger.info(f"Downloading PDF content from: {url}")
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            raw_document = response.content
            with pdfplumber.open(io.BytesIO(raw_document)) as pdf:
                markdown_content = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
            logger.info(f"Successfully processed PDF for url: {url}")

        else:
            markdown_content = f"[MARKDOWN_GENERATION_FAILED: Unsupported content type '{content_type}']"

    except Exception as e:
        logger.error(f"An unexpected error occurred while processing {url}: {e}", exc_info=True)
        markdown_content = f"[MARKDOWN_GENERATION_FAILED: {e}]"

    return raw_document, markdown_content

async def process_url(url: str, logger):
    """Downloads, processes, and stores content from a URL."""
    url_id, url_status = add_url_or_get_id(url)
    if url_status == "existing":
        # Optionally, we could check here if the content is missing and re-process if needed
        return url_id, url_status
    
    raw_document, markdown_content = await fetch_and_generate_markdown(url, logger)

    if raw_document or markdown_content:
        logger.info(f"Updating document content for url_id: {url_id}")
        try:
            update_document_content(url_id, raw_document, markdown_content)
            logger.info(f"Successfully updated document content for url_id: {url_id}")
        except Exception as e:
            logger.error(f"Failed to update document content for url_id {url_id}: {e}", exc_info=True)

    return url_id, url_status