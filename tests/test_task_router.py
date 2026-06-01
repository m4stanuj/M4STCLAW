import pytest
from m4stclaw.core.router import classify_task

def test_classify_speed_task():
    """Tasks requesting quick answers should route to speed chain."""
    speed_queries = [
        'what time is it',
        'convert 5km to miles',
        'who is the president of France',
        'give me a brief tldr'
    ]
    for q in speed_queries:
        assert classify_task(q) == "speed"

def test_classify_code_task():
    """Code-related queries should route to code chain."""
    code_queries = [
        'write a python function to sort a list',
        'fix this bug in my React component',
        'refactor this class to use async',
        'how to write an SQL query to join tables'
    ]
    for q in code_queries:
        assert classify_task(q) == "code"

def test_classify_research_task():
    """Research queries should route to research chain."""
    research_queries = [
        'deep dive into modern history',
        'latest developments in quantum computing',
        'market trends for AI startups',
        'research new cybersecurity threats'
    ]
    for q in research_queries:
        assert classify_task(q) == "research"
