from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseFetcher(ABC):
    @abstractmethod
    def fetch_papers(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch papers from the source.
        
        Returns:
            List of dictionaries containing paper details.
            Each dictionary must have:
            - title: str
            - authors: List[str]
            - summary: str
            - published: datetime (UTC)
            - pdf_url: str (or None)
            - source: str (e.g., "ArXiv", "Semantic Scholar")
            - entry_id: str (unique identifier for the source)
            - categories: List[str] (optional)
        """
        pass
