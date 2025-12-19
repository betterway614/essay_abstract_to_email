import arxiv
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class ArxivClient:
    def __init__(self):
        self.client = arxiv.Client(
            page_size=100,
            delay_seconds=3.0,
            num_retries=3
        )

    def fetch_papers(self) -> List[Dict[str, Any]]:
        """
        Fetch papers from ArXiv based on configuration.
        """
        if not settings:
            logger.error("Configuration not initialized.")
            return []

        subjects = settings.subjects
        keywords = settings.keywords
        match_logic = settings.match_logic

        if not subjects:
            logger.warning("No subjects configured for ArXiv search.")
            return []

        # Construct query: cat:subject1 OR cat:subject2 ...
        # Note: ArXiv API query syntax is limited. 
        # "cat:cs.CV OR cat:cs.LG" is standard.
        query_parts = [f"cat:{subject}" for subject in subjects]
        query = " OR ".join(query_parts)
        
        logger.info(f"Querying ArXiv with: {query}")

        search = arxiv.Search(
            query=query,
            max_results=200, # Fetch enough to cover last 24h
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

        results = []
        try:
            # We need to filter for the last 24 hours.
            # ArXiv updated/published dates are in UTC.
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Using generator to fetch
            for result in self.client.results(search):
                # result.published is datetime with timezone
                if result.published < cutoff_time:
                    # Since results are sorted by submitted date descending, 
                    # once we hit a paper older than 24h, we can stop IF we trust the sort.
                    # However, sometimes submission != publication. 
                    # Let's check a bit more buffer or just filter.
                    # But wait, result.published is when it was published. 
                    # The PRD says "submittedDate". arxiv python lib maps `published` to the published date.
                    # Let's rely on `published` for "latest papers".
                    # Optimization: stop if we are way past 24h (e.g. 48h) to be safe, 
                    # but technically we can stop immediately if strict sort.
                    # Let's just filter strictly.
                    if result.published < cutoff_time - timedelta(hours=1):
                         break
                    continue
                
                # Keyword Filtering
                if self._matches_keywords(result, keywords, match_logic):
                    paper_data = {
                        "title": result.title,
                        "authors": [a.name for a in result.authors],
                        "summary": result.summary,
                        "published": result.published,
                        "pdf_url": result.pdf_url,
                        "entry_id": result.entry_id,
                        "categories": result.categories
                    }
                    results.append(paper_data)
                    
        except Exception as e:
            logger.error(f"Error fetching papers from ArXiv: {e}")
            
        logger.info(f"Found {len(results)} papers matching criteria.")
        return results

    def _matches_keywords(self, paper: arxiv.Result, keywords: List[str], logic: str) -> bool:
        """
        Check if paper matches keyword criteria.
        """
        if not keywords:
            return True # If no keywords defined, return all papers in categories

        text_to_search = (paper.title + " " + paper.summary).lower()
        normalized_keywords = [k.lower() for k in keywords]

        hits = [k in text_to_search for k in normalized_keywords]

        if logic == "AND":
            return all(hits)
        else: # OR
            return any(hits)

if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.INFO)
    client = ArxivClient()
    papers = client.fetch_papers()
    for p in papers:
        print(f"Title: {p['title']}")
        print(f"Date: {p['published']}")
        print("-" * 20)
