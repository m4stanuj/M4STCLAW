"""Tests for the semantic fuzzy cache module."""

import time
from m4stclaw.core.cache import (
    normalize_text,
    get_query_hash,
    get_word_similarity,
    should_skip_cache,
    get_cached_response,
    set_cached_response,
    get_cache_stats
)


def test_normalize_text_strips_punctuation():
    """Normalized text should be lowercase with no punctuation."""
    result = normalize_text("Hello, World!")
    assert "hello" in result
    assert "world" in result
    assert "," not in result
    assert "!" not in result


def test_normalize_text_collapses_whitespace():
    """Multiple spaces should collapse to single space."""
    assert normalize_text("  too   many   spaces  ") == "too many spaces"


def test_query_hash_deterministic():
    """Same input should always produce same hash."""
    h1 = get_query_hash("write a python function")
    h2 = get_query_hash("write a python function")
    assert h1 == h2


def test_query_hash_different_inputs():
    """Different inputs should produce different hashes."""
    h1 = get_query_hash("write python code")
    h2 = get_query_hash("deploy node server")
    assert h1 != h2


def test_word_similarity_identical():
    """Identical sentences should have similarity of 1.0."""
    sim = get_word_similarity("how to sort a list in python", "how to sort a list in python")
    assert sim == 1.0


def test_word_similarity_different():
    """Completely different sentences should have low similarity."""
    sim = get_word_similarity("machine learning algorithms", "bake a chocolate cake")
    assert sim < 0.3


def test_word_similarity_partial():
    """Partially overlapping should have moderate similarity."""
    sim = get_word_similarity("sort a list in python", "sort an array in python")
    assert 0.4 < sim < 1.0


def test_should_skip_cache_dynamic_queries():
    """Queries mentioning time-sensitive topics should be skipped."""
    assert should_skip_cache("what is the current time") is True
    assert should_skip_cache("take a screenshot of my screen") is True
    assert should_skip_cache("what is the date today") is True


def test_should_skip_cache_normal_queries():
    """Normal queries should NOT be skipped."""
    assert should_skip_cache("write a python function to sort") is False
    assert should_skip_cache("explain binary search algorithm") is False


def test_cache_set_and_get():
    """Setting a cache entry and retrieving it should return the same value."""
    set_cached_response("explain quicksort algorithm in detail", "Quicksort is a divide-and-conquer algorithm...", ttl_seconds=60)
    result = get_cached_response("explain quicksort algorithm in detail")
    assert result is not None
    assert "Quicksort" in result


def test_cache_stats_accumulate():
    """Cache stats should reflect operations."""
    stats = get_cache_stats()
    assert "hits" in stats
    assert "misses" in stats
    assert "size" in stats
    assert isinstance(stats["hit_rate_pct"], float)
