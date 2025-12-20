import arxiv
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
try:
    from ..config import settings
except ImportError:
    from config import settings
from .base import BaseFetcher

logger = logging.getLogger(__name__)

class ArxivFetcher(BaseFetcher):
    def __init__(self):
        self.client = arxiv.Client(
            page_size=100,
            delay_seconds=3.0,
            num_retries=3
        )

    def fetch_papers(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch papers from ArXiv based on configuration.
        """
        if not isinstance(top_n, int) or top_n <= 0:
            raise ValueError("top_n must be a positive integer")

        if not settings:
            logger.error("Configuration not initialized.")
            return []

        # Check if enabled
        if not settings.data_sources.get("arxiv", {}).get("enable", True):
             logger.info("ArXiv source is disabled in configuration.")
             return []

        subjects = settings.subjects
        keywords = settings.keywords
        match_logic = settings.match_logic
        lookback_hours = getattr(settings, "arxiv_lookback_hours", 24)

        if not subjects:
            logger.warning("No subjects configured for ArXiv search.")
            return []

        # Construct query
        query_parts = [f"cat:{subject}" for subject in subjects]
        query = " OR ".join(query_parts)
        
        logger.info(f"Querying ArXiv with: {query}")

        search = arxiv.Search(
            query=query,
            max_results=200, 
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

        results = []
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            
            for result in self.client.results(search):
                if result.published < cutoff_time:
                    if result.published < cutoff_time - timedelta(hours=1):
                         break
                    continue
                
                if self._matches_keywords(result, keywords, match_logic):
                    relevance_score = self._compute_relevance_score(result, keywords)
                    paper_data = {
                        "title": result.title,
                        "authors": [a.name for a in result.authors],
                        "summary": result.summary.replace("\n", " "), # Clean newlines
                        "published": result.published,
                        "pdf_url": result.pdf_url,
                        "entry_id": result.entry_id,
                        "categories": result.categories,
                        "source": "ArXiv",
                        "_relevance_score": relevance_score
                    }
                    results.append(paper_data)
                    
        except Exception as e:
            logger.error(f"Error fetching papers from ArXiv: {e}")
            
        results.sort(key=lambda p: (p.get("_relevance_score", 0), p.get("published")), reverse=True)
        limited = results[:top_n]
        for p in limited:
            p.pop("_relevance_score", None)

        logger.info(f"Found {len(limited)} papers from ArXiv.")
        return limited

    def _matches_keywords(self, paper: arxiv.Result, keywords: List[str], logic: str) -> bool:
        if not keywords:
            return True

        text_to_search = (paper.title + " " + paper.summary).lower()
        normalized_keywords = [k.lower() for k in keywords]

        hits = [k in text_to_search for k in normalized_keywords]

        if logic == "AND":
            return all(hits)
        else: # OR
            return any(hits)

    def _compute_relevance_score(self, paper: arxiv.Result, keywords: List[str]) -> int:
        if not keywords:
            return 0

        title = (paper.title or "").lower()
        summary = (paper.summary or "").lower()
        normalized_keywords = [k.lower() for k in keywords if k]

        score = 0
        for kw in normalized_keywords:
            if not kw:
                continue
            if kw in title:
                score += 3
            if kw in summary:
                score += 1
        return score
