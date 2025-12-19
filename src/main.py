import asyncio
import logging
import sys
import os

# Ensure src is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from arxiv_client import ArxivClient
from llm_processor import LLMProcessor
from mailer import Mailer

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting ArXiv Daily Digest Workflow...")

    if not settings:
        logger.error("Configuration failed. Exiting.")
        sys.exit(1)

    dry_run = os.getenv("DRY_RUN", "").strip().lower() in {"1", "true", "yes", "y"}

    # 1. Fetch Papers
    client = ArxivClient()
    papers = client.fetch_papers()

    if not papers:
        logger.info("No papers found matching the criteria.")
        # Optional: Send empty email if configured
        if settings.email_config.get("send_empty", False) and not dry_run:
            mailer = Mailer()
            mailer.send_daily_digest([])
        return

    if dry_run:
        logger.info(f"DRY_RUN enabled. Fetched {len(papers)} papers. Skipping LLM and email sending.")
        return

    # 2. Process with LLM
    if settings.llm_config.get("enable", False):
        logger.info("LLM processing enabled. Summarizing papers...")
        processor = LLMProcessor()
        papers = await processor.process_papers(papers)
    else:
        logger.info("LLM processing disabled. Skipping summarization.")

    # 3. Send Email
    logger.info("Preparing to send email...")
    mailer = Mailer()
    mailer.send_daily_digest(papers)
    
    logger.info("Workflow completed successfully.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Workflow interrupted by user.")
    except Exception as e:
        logger.critical(f"Unexpected error in workflow: {e}", exc_info=True)
        sys.exit(1)
