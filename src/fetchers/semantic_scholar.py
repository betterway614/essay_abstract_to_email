import requests
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
try:
    from ..config import settings
except ImportError:
    from config import settings
from .base import BaseFetcher

logger = logging.getLogger(__name__)

class SemanticScholarFetcher(BaseFetcher):
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def _get_with_retry(self, params: Dict[str, Any], headers: Dict[str, str], keyword: str) -> requests.Response:
        delay_seconds = 1.0 if headers.get("x-api-key") else 2.0
        time.sleep(delay_seconds)

        response = requests.get(self.BASE_URL, params=params, headers=headers, timeout=10)
        if response.status_code != 429:
            return response

        retry_after = response.headers.get("Retry-After")
        try:
            wait_seconds = float(retry_after) if retry_after is not None else 10.0
        except Exception:
            wait_seconds = 10.0

        logger.warning(f"Rate limit hit for S2 keyword '{keyword}'. Waiting {wait_seconds} seconds and retrying.")
        time.sleep(wait_seconds)
        return requests.get(self.BASE_URL, params=params, headers=headers, timeout=10)

    def fetch_papers(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch papers from Semantic Scholar.
        """
        # Check config
        if not settings.data_sources.get("semantic_scholar", {}).get("enable", False):
             logger.info("Semantic Scholar source is disabled in configuration.")
             return []

        keywords = settings.keywords
        if not keywords:
            logger.warning("No keywords configured for Semantic Scholar.")
            return []

        api_key = settings.semantic_scholar_api_key
        headers = {}
        if api_key:
            headers["x-api-key"] = api_key

        current_year = datetime.now().year
        # Query for this year and last year to catch recent papers around new year
        years = f"{current_year-1}-{current_year}"

        results = []
        seen_ids = set()
        
        # Filter for recent 3 days per PRD
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=3)

        for keyword in keywords:
            params = {
                "query": keyword,
                "year": years,
                "fields": "paperId,title,abstract,url,venue,publicationDate,authors",
                "limit": 20 
            }
            
            try:
                logger.info(f"Searching S2 for: {keyword}")
                response = self._get_with_retry(params=params, headers=headers, keyword=keyword)
                
                if response.status_code == 429:
                    logger.warning(f"Rate limit hit for S2 keyword '{keyword}'. Skipping.")
                    continue
                if response.status_code != 200:
                    logger.error(f"S2 API Error {response.status_code}: {response.text}")
                    continue
                
                data = response.json()
                papers = data.get("data", [])
                
                if not papers:
                    continue

                for p in papers:
                    paper_id = p.get("paperId")
                    if paper_id in seen_ids:
                        continue
                    
                    pub_date_str = p.get("publicationDate") # Format: YYYY-MM-DD
                    if not pub_date_str:
                        continue
                        
                    try:
                        # Parse date
                        pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue 
                        
                    if pub_date < cutoff_date:
                        continue

                    # Clean abstract
                    abstract = p.get("abstract")
                    if not abstract:
                        abstract = "Abstract not available."
                    else:
                        abstract = abstract.replace("\n", " ")

                    # Map to schema
                    entry = {
                        "title": p.get("title"),
                        "authors": [a.get("name") for a in p.get("authors", [])],
                        "summary": abstract,
                        "published": pub_date,
                        "pdf_url": p.get("url"), # S2 link
                        "entry_id": paper_id,
                        "source": "Semantic Scholar",
                        "categories": [] 
                    }
                    
                    results.append(entry)
                    seen_ids.add(paper_id)

            except Exception as e:
                logger.error(f"Error fetching from S2 for keyword '{keyword}': {e}")

        # Sort by date descending
        results.sort(key=lambda x: x["published"], reverse=True)
        
        logger.info(f"Found {len(results)} papers from Semantic Scholar.")
        return results[:top_n]
