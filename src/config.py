import os
import yaml
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._config = self._load_config()
        self._validate_env_vars()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found at: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            try:
                return yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ValueError(f"Error parsing YAML configuration: {e}")

    def _validate_env_vars(self):
        """Validate that required environment variables are set."""
        required_vars = [
            "MAIL_USER",
            "MAIL_PASS",
            "LLM_API_KEY"
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            logging.warning(f"Missing environment variables: {', '.join(missing)}. Some features may not work.")

    @property
    def criteria(self) -> Dict[str, Any]:
        return self._config.get("criteria", {})

    @property
    def subjects(self) -> List[str]:
        return self.criteria.get("categories", [])

    @property
    def keywords(self) -> List[str]:
        return self.criteria.get("keywords", [])

    @property
    def match_logic(self) -> str:
        return self.criteria.get("match_logic", "OR").upper()

    @property
    def llm_config(self) -> Dict[str, Any]:
        return self._config.get("llm", {})

    @property
    def email_config(self) -> Dict[str, Any]:
        return self._config.get("email", {})

    # Environment variable getters
    @property
    def mail_user(self) -> str:
        return os.getenv("MAIL_USER", "").strip()

    @property
    def mail_pass(self) -> str:
        return os.getenv("MAIL_PASS", "").strip()

    @property
    def mail_recipient(self) -> str:
        # Allow override via env var
        return os.getenv("MAIL_RECIPIENT", self.email_config.get("recipient", "")).strip()

    @property
    def mail_recipients(self) -> List[str]:
        raw = os.getenv("MAIL_RECIPIENTS", "").strip()
        if raw:
            return [s.strip() for s in raw.replace(";", ",").split(",") if s.strip()]

        raw = os.getenv("MAIL_RECIPIENT", "").strip()
        if raw:
            return [s.strip() for s in raw.replace(";", ",").split(",") if s.strip()]

        recipients = self.email_config.get("recipients")
        if isinstance(recipients, list):
            return [str(s).strip() for s in recipients if str(s).strip()]

        recipient = self.email_config.get("recipient", "")
        if isinstance(recipient, str) and recipient.strip():
            return [recipient.strip()]

        return []

    @property
    def llm_api_key(self) -> str:
        return os.getenv("LLM_API_KEY", "").strip()

    @property
    def llm_base_url(self) -> Optional[str]:
        return os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip()

# Global config instance
try:
    # Look for config.yaml in the root directory relative to this file
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(root_dir, "config.yaml")
    settings = Config(config_path)
except Exception as e:
    logging.error(f"Failed to initialize configuration: {e}")
    settings = None
