"""Tests clés produit commerciales."""
from __future__ import annotations

import pytest

from product_keys import generate_key, hash_key, normalize_key, parse_env_product_keys


def test_generate_key_format():
    k = generate_key("ultra")
    assert k.startswith("EMO-ULTRA-")
    assert len(k.split("-")) >= 5


def test_normalize_key():
    assert normalize_key(" emo-ultra-abcd ") == "EMO-ULTRA-ABCD"


def test_hash_deterministic():
    assert hash_key("EMO-TEST") == hash_key("emo-test")


def test_parse_env_product_keys():
    import os
    os.environ["EMO_PRODUCT_KEYS"] = "ultra:EMO-ULTRA-AAAA-BBBB-CCCC,basic:EMO-BASIC-1111-2222-3333"
    items = parse_env_product_keys()
    assert len(items) == 2
    assert items[0]["tier"] == "ultra"
    os.environ.pop("EMO_PRODUCT_KEYS", None)
