# ArXiv Daily Digest Workflow 🚀

Automated daily summary of the latest ArXiv papers, delivered to your email.

## Features

- **Automated Fetching**: Crawls ArXiv daily for new papers in your specified categories.
- **Intelligent Summarization**: Uses LLM (OpenAI/DeepSeek) to generate structured Chinese summaries (Background, Method, Conclusion).
- **Keyword Filtering**: Filter papers by keywords in Title or Abstract.
- **Email Delivery**: Sends a beautiful HTML email with "AI Quick Read" and original abstracts.
- **Serverless**: Runs entirely on GitHub Actions (free tier).

## Quick Start

### 1. Fork this Repository
Click the "Fork" button to create your own copy.

### 2. Configure Settings
Edit `config.yaml` to set your preferences:

```yaml
criteria:
  categories: ["cs.CV", "cs.LG"]
  keywords: ["LLM", "Agent"]
  match_logic: "OR"

llm:
  enable: true
  provider: "openai"
  model: "deepseek-chat"
  language: "zh-CN"
```

### 3. Set Secrets
Go to **Settings** -> **Secrets and variables** -> **Actions** in your GitHub repository and add:

| Secret Name | Description |
| --- | --- |
| `MAIL_USER` | Your email address (sender) |
| `MAIL_PASS` | SMTP App Password (not your login password) |
| `MAIL_RECIPIENT` | Recipient email address (can be same as sender) |
| `MAIL_RECIPIENTS` | (Optional) Multiple recipients separated by comma |
| `LLM_API_KEY` | Your OpenAI/DeepSeek API Key |
| `LLM_BASE_URL` | (Optional) Custom API Endpoint (e.g. `https://api.deepseek.com`) |
| `LLM_MODEL` | (Optional) Override model name (e.g. `deepseek-chat`) |

### 4. Enable Workflow
Go to the **Actions** tab and enable the workflow. It will run automatically every day at 09:00 UTC+8.

## Local Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Create a `.env` file in the root:
   ```env
   MAIL_USER=your_email@example.com
   MAIL_PASS=your_app_password
   MAIL_RECIPIENT=target@example.com
   # Or multiple recipients:
   # MAIL_RECIPIENTS=a@example.com,b@example.com
   LLM_API_KEY=sk-...
   LLM_BASE_URL=https://api.deepseek.com
   # LLM_MODEL=deepseek-chat
   ```

3. **Run**:
   ```bash
   # Optional: dry run without calling LLM and sending email
   # DRY_RUN=1 python src/main.py
   python src/main.py
   ```

4. **Run Tests**:
   ```bash
   pytest tests/
   ```

## Requirements

- Python 3.9+
- OpenAI Compatible API Key
- SMTP Email Account (Gmail, Outlook, QQ, etc.)

## License
MIT
