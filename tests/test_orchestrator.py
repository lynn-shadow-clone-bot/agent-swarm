import sys
import os
import pytest

# Add the scripts directory to the path so we can import orchestrator
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))

from orchestrator import load_agent_template

def test_load_agent_template_valid():
    """Test that a valid agent type returns the correct template."""
    template = load_agent_template("tester")
    assert template["agent_id"] == "tester"
    assert "system_prompt" in template

def test_load_agent_template_unknown():
    """Test that an unknown agent type returns the default 'code-writer' template."""
    template = load_agent_template("unknown_agent_type")
    assert template["agent_id"] == "code-writer"
    assert "system_prompt" in template

def test_load_agent_template_default():
    """Test that the default 'code-writer' template is returned correctly when requested explicitly."""
    template = load_agent_template("code-writer")
    assert template["agent_id"] == "code-writer"
