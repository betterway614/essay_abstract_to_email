# ArXiv Daily Digest System Development Plan

I will develop the system following the PRD requirements and best practices.

## 1. Project Initialization & Structure
- **Directory Structure**:
  - `src/`: Core logic (`main.py`, `arxiv_client.py`, `llm_processor.py`, `mailer.py`, `config.py`).
  - `templates/`: HTML email templates (`email_template.html`).
  - `tests/`: Unit tests.
  - `.github/workflows/`: GitHub Actions workflow configuration.
  - `config.yaml`: User configuration.
  - `requirements.txt`: Python dependencies.

## 2. Dependency Management
- **Libraries**:
  - `arxiv`: Robust wrapper for ArXiv API (handles retries/pagination).
  - `openai`: For LLM integration (compatible with DeepSeek/Moonshot).
  - `jinja2`: For generating HTML emails.
  - `pyyaml`: For parsing `config.yaml`.
  - `pytest` & `pytest-mock`: For testing.
  - `python-dotenv`: For local environment variable management.

## 3. Core Component Implementation

### 3.1 Configuration (`src/config.py`)
- Load `config.yaml` for business logic (subjects, keywords).
- Load environment variables for secrets (`MAIL_USER`, `MAIL_PASS`, `LLM_API_KEY`, etc.).

### 3.2 Data Fetcher (`src/arxiv_client.py`)
- **Query**: Construct complex queries for multiple subjects (e.g., `cat:cs.CV OR cat:cs.LG`).
- **Sorting**: `submittedDate`, descending.
- **Filtering**:
  - **Date**: Strictly filter papers submitted in the last 24 hours (UTC).
  - **Keywords**: Case-insensitive matching in Title and Abstract.

### 3.3 LLM Processor (`src/llm_processor.py`)
- **Interface**: `summarize(paper_data) -> summary_dict`.
- **Prompt**: Structured prompt for "Background", "Method", "Conclusion".
- **Resilience**: Try/Except blocks to handle API failures, falling back to original abstract.
- **Concurrency**: Use `asyncio` to process multiple papers in parallel (limited to 3-5 concurrent requests).

### 3.4 Mailer (`src/mailer.py`)
- **Template**: Jinja2 template with CSS for "AI Summary" vs "Original Abstract".
- **Transport**: SMTP (SSL/TLS) support for major providers.

### 3.5 Workflow (`src/main.py`)
- Orchestrate the pipeline: Config -> Fetch -> Filter -> Summarize -> Email.
- Logging: Console logging for GitHub Actions visibility.

## 4. GitHub Actions Workflow
- Create `.github/workflows/daily_digest.yml`.
- Schedule: Daily (e.g., 09:00 UTC+8).
- Secrets mapping.

## 5. Testing & Documentation
- **Tests**: Unit tests for filtering logic and config loading; Mocks for external APIs.
- **Docs**: `README.md` with setup instructions and `config.yaml` explanation.

## Execution Order
1.  **Scaffold**: Create files and install dependencies.
2.  **Implement Config & ArXiv Client**: Ensure we can get data.
3.  **Implement LLM & Mailer**: Process and deliver data.
4.  **Integration**: `main.py` and GitHub Workflow.
5.  **Test**: Write and run tests.
