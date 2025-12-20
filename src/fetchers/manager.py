import logging
import re
import concurrent.futures
from typing import List, Dict, Any
from .arxiv import ArxivFetcher
from .semantic_scholar import SemanticScholarFetcher

logger = logging.getLogger(__name__)

class FetchManager:
    def __init__(self):
        self.fetchers = [
            ArxivFetcher(),
            SemanticScholarFetcher()
        ]

    def fetch_all_papers(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch papers from all configured sources and deduplicate.
        """
        all_papers: List[Dict[str, Any]] = []
        source_counts: Dict[str, int] = {}
        
        # Execute fetchers in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.fetchers)) as executor:
            future_to_fetcher = {executor.submit(f.fetch_papers, top_n): f for f in self.fetchers}
            for future in concurrent.futures.as_completed(future_to_fetcher):
                fetcher = future_to_fetcher[future]
                try:
                    papers = future.result()
                    if papers:
                        src = str(papers[0].get("source") or fetcher.__class__.__name__)
                        source_counts[src] = source_counts.get(src, 0) + len(papers)
                    if papers:
                        all_papers.extend(papers)
                except Exception as e:
                    logger.error(f"Fetcher execution failed: {e}")

        if not all_papers:
            if source_counts:
                logger.info(f"Fetched papers by source: {source_counts}, total: 0")
            return []

        # Deduplicate
        unique_papers = self._deduplicate(all_papers)
        logger.info(f"Fetched papers by source: {source_counts}, total: {len(all_papers)}, after dedup: {len(unique_papers)}")
        
        # Sort by published date descending
        unique_papers.sort(key=lambda x: x["published"], reverse=True)
        
        # Return top N overall
        return unique_papers[:top_n]

    def _deduplicate(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate papers based on normalized title.
        Preference: ArXiv > Semantic Scholar
        """
        seen = {}
        
        for p in papers:
            # Normalize title: lowercase, remove punctuation, collapse spaces
            title = p.get("title", "")
            # Remove non-alphanumeric (keep spaces)
            norm_title = re.sub(r'[^\w\s]', '', title.lower())
            # Collapse whitespace
            norm_title = re.sub(r'\s+', ' ', norm_title).strip()
            
            if not norm_title:
                continue
                
            if norm_title in seen:
                existing = seen[norm_title]
                # Conflict resolution
                # If existing is NOT ArXiv and current IS ArXiv, swap.
                if existing.get("source") != "ArXiv" and p.get("source") == "ArXiv":
                    seen[norm_title] = p
                # Otherwise keep existing (if existing is ArXiv, keep it. If both S2, keep first).
            else:
                seen[norm_title] = p
                
        return list(seen.values())
