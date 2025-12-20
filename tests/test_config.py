import pytest
from config import Config
import os
import yaml

def test_config_load(tmp_path):
    # Create a temp config file
    config_data = {
        "criteria": {
            "categories": ["cs.AI"],
            "keywords": ["Test"],
            "match_logic": "AND"
        },
        "llm": {
            "enable": True
        }
    }
    
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
        
    config = Config(str(config_file))
    
    assert config.subjects == ["cs.AI"]
    assert config.keywords == ["Test"]
    assert config.match_logic == "AND"
    assert config.llm_config["enable"] == True

def test_env_vars_precedence(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump({"email": {"recipient": "file@example.com"}}, f)
        
    monkeypatch.setenv("MAIL_RECIPIENT", "env@example.com")
    
    config = Config(str(config_file))
    assert config.mail_recipient == "env@example.com"

def test_data_sources_default(tmp_path):
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump({}, f)
    
    config = Config(str(config_file))
    # Default behavior check
    assert config.data_sources["arxiv"]["enable"] == True
    assert config.data_sources["semantic_scholar"]["enable"] == False

