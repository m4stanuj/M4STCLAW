"""Tests for the configuration and key rotation module."""

import os
from m4stclaw.core.config import (
    get_keys_for_provider,
    get_next_key,
    set_cooldown,
    get_cooldowns_status
)


def test_placeholder_key_for_unknown_provider():
    """Providers with no configured keys should return placeholder."""
    keys = get_keys_for_provider("nonexistent_provider_xyz")
    assert keys == ["PLACEHOLDER_NO_KEY"]


def test_get_next_key_placeholder():
    """Getting next key from placeholder list should return placeholder."""
    key, idx = get_next_key("fake_provider", ["PLACEHOLDER_NO_KEY"])
    assert key == "PLACEHOLDER_NO_KEY"
    assert idx == 0


def test_get_next_key_rotation():
    """Key rotation should cycle through available keys."""
    test_keys = ["key_a", "key_b", "key_c"]
    seen_keys = set()
    for _ in range(6):
        key, idx = get_next_key("test_rotation_provider", test_keys)
        seen_keys.add(key)
    # Should have rotated through all 3 keys
    assert seen_keys == {"key_a", "key_b", "key_c"}


def test_set_and_get_cooldown():
    """Setting a cooldown should be reflected in status."""
    set_cooldown("test_cd_provider", 0, 5.0)
    status = get_cooldowns_status()
    assert "test_cd_provider:0" in status
    assert status["test_cd_provider:0"] > 0


def test_cooldown_skips_cooled_key():
    """Cooled-down keys should be skipped during rotation."""
    test_keys = ["cool_a", "cool_b"]
    # Cool down first key
    set_cooldown("test_skip_provider", 0, 30.0)
    key, idx = get_next_key("test_skip_provider", test_keys)
    # Should prefer the non-cooled key
    assert key == "cool_b" or idx == 1
