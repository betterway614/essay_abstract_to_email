import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from src.fetchers.arxiv import ArxivFetcher
from src.fetchers.semantic_scholar import SemanticScholarFetcher
from src.fetchers.manager import FetchManager

# --- Fixtures ---
@pytest.fixture
def mock_settings():
    with patch('src.fetchers.arxiv.settings') as mock:
        mock.subjects = ["cs.CV"]
        mock.keywords = ["LLM", "Agent"]
        mock.match_logic = "OR"
        mock.arxiv_lookback_hours = 168
        mock.data_sources = {"arxiv": {"enable": True}, "semantic_scholar": {"enable": True}}
        mock.semantic_scholar_api_key = "test_key"
        yield mock

@pytest.fixture
def mock_s2_settings():
    with patch('src.fetchers.semantic_scholar.settings') as mock:
        mock.keywords = ["LLM"]
        mock.data_sources = {"semantic_scholar": {"enable": True}}
        mock.semantic_scholar_api_key = "test_key"
        yield mock

# --- ArxivFetcher Tests ---
@patch('src.fetchers.arxiv.arxiv.Client')
@patch('src.fetchers.arxiv.arxiv.Search')
def test_arxiv_fetcher(mock_search, mock_client_cls, mock_settings):
    mock_client_instance = mock_client_cls.return_value
    now = datetime.now(timezone.utc)
    
    p1 = MagicMock()
    p1.title = "Arxiv Paper LLM"
    p1.summary = "Summary"
    p1.published = now - timedelta(hours=2)
    p1.authors = [MagicMock(name="Author A")]
    p1.pdf_url = "http://pdf1"
    p1.entry_id = "1"
    p1.categories = ["cs.CV"]
    
    p2 = MagicMock()
    p2.title = "Old Paper LLM"
    p2.summary = "Summary"
    p2.published = now - timedelta(days=8)
    mock_client_instance.results.return_value = [p1, p2]
    
    fetcher = ArxivFetcher()
    results = fetcher.fetch_papers()
    
    assert len(results) == 1
    assert results[0]['source'] == "ArXiv"
    assert results[0]['title'] == "Arxiv Paper LLM"

# --- SemanticScholarFetcher Tests ---
@patch('src.fetchers.semantic_scholar.requests.get')
def test_s2_fetcher(mock_get, mock_s2_settings):
    now = datetime.now(timezone.utc)
    
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "paperId": "s2_1",
                "title": "S2 Paper",
                "abstract": "Abstract",
                "url": "http://s2",
                "venue": "Venue",
                "publicationDate": now.strftime("%Y-%m-%d"),
                "authors": [{"name": "Author B"}]
            }
        ]
    }
    mock_get.return_value = mock_response
    
    fetcher = SemanticScholarFetcher()
    results = fetcher.fetch_papers()
    
    assert len(results) == 1
    assert results[0]['source'] == "Semantic Scholar"
    assert results[0]['title'] == "S2 Paper"

# --- FetchManager Tests ---
@patch('src.fetchers.manager.ArxivFetcher')
@patch('src.fetchers.manager.SemanticScholarFetcher')
def test_manager_deduplication(MockArxiv, MockS2):
    # Setup mocks
    arxiv_fetcher = MockArxiv.return_value
    s2_fetcher = MockS2.return_value
    
    now = datetime.now(timezone.utc)
    
    # Paper A in Arxiv
    paper_arxiv = {
        "title": "Alpha Paper",
        "published": now,
        "source": "ArXiv",
        "pdf_url": "arxiv_url"
    }
    
    # Paper A in S2 (duplicate)
    paper_s2_dup = {
        "title": "Alpha Paper", # Same title
        "published": now,
        "source": "Semantic Scholar",
        "pdf_url": "s2_url"
    }
    
    # Paper B in S2 (unique)
    paper_s2_unique = {
        "title": "Beta Paper",
        "published": now - timedelta(hours=1),
        "source": "Semantic Scholar",
        "pdf_url": "s2_url_b"
    }
    
    arxiv_fetcher.fetch_papers.return_value = [paper_arxiv]
    s2_fetcher.fetch_papers.return_value = [paper_s2_dup, paper_s2_unique]
    
    manager = FetchManager()
    results = manager.fetch_all_papers()
    
    # Should have 2 papers: Alpha (Arxiv) and Beta (S2)
    assert len(results) == 2
    
    titles = [p['title'] for p in results]
    assert "Alpha Paper" in titles
    assert "Beta Paper" in titles
    
    # Check deduplication preference
    alpha = next(p for p in results if p['title'] == "Alpha Paper")
    assert alpha['source'] == "ArXiv" # Prefer ArXiv
