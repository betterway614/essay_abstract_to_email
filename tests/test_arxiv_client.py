import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from arxiv_client import ArxivClient

@pytest.fixture
def mock_settings():
    with patch('arxiv_client.settings') as mock:
        mock.subjects = ["cs.CV"]
        mock.keywords = ["LLM", "Agent"]
        mock.match_logic = "OR"
        yield mock

def test_matches_keywords(mock_settings):
    client = ArxivClient()
    
    # Mock ArXiv Result
    paper = MagicMock()
    paper.title = "A New LLM Agent"
    paper.summary = "This paper introduces a large language model agent."
    
    # Test OR logic
    assert client._matches_keywords(paper, ["LLM", "Agent"], "OR") == True
    assert client._matches_keywords(paper, ["Vision"], "OR") == False
    
    # Test AND logic
    assert client._matches_keywords(paper, ["LLM", "Agent"], "AND") == True
    
    paper.title = "A New LLM"
    paper.summary = "Just a model."
    assert client._matches_keywords(paper, ["LLM", "Agent"], "AND") == False

@patch('arxiv_client.arxiv.Client')
@patch('arxiv_client.arxiv.Search')
def test_fetch_papers(mock_search, mock_client_cls, mock_settings):
    # Setup Mock Client
    mock_client_instance = mock_client_cls.return_value
    
    # Create mock results
    now = datetime.now(timezone.utc)
    
    # Paper 1: Recent, Matches
    p1 = MagicMock()
    p1.title = "Recent LLM Paper"
    p1.summary = "Summary about LLM"
    p1.published = now - timedelta(hours=2)
    p1.authors = [MagicMock(name="Author A")]
    p1.pdf_url = "http://pdf1"
    p1.entry_id = "1"
    p1.categories = ["cs.CV"]
    
    # Paper 2: Recent, No Match
    p2 = MagicMock()
    p2.title = "Recent Vision Paper"
    p2.summary = "Summary about images"
    p2.published = now - timedelta(hours=3)
    
    # Paper 3: Old
    p3 = MagicMock()
    p3.title = "Old LLM Paper"
    p3.published = now - timedelta(hours=25)
    
    # Mock results iterator
    mock_client_instance.results.return_value = [p1, p2, p3]
    
    client = ArxivClient()
    results = client.fetch_papers()
    
    assert len(results) == 1
    assert results[0]['title'] == "Recent LLM Paper"
