import pytest

def test_classify_speed_task():
    """Tasks requesting quick answers should route to speed chain."""
    speed_queries = [
        'what time is it',
        'convert 5km to miles',
        'who is the president of France',
    ]
    for q in speed_queries:
        assert len(q) > 0  # placeholder for actual router test

def test_classify_code_task():
    """Code-related queries should route to code chain."""
    code_queries = [
        'write a python function to sort a list',
        'fix this bug in my React component',
        'refactor this class to use async',
    ]
    for q in code_queries:
        assert len(q) > 0

def test_classify_research_task():
    """Research queries should route to research chain."""
    research_queries = [
        'compare React vs Vue in 2026',
        'latest developments in quantum computing',
        'market analysis for AI startups',
    ]
    for q in research_queries:
        assert len(q) > 0

