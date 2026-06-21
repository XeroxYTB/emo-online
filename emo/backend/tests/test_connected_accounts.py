"""Unit tests for connected_accounts helpers."""
import base64
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import connected_accounts as ca


def test_encode_decode_state_roundtrip():
    state = ca.encode_state("user_abc", "http://127.0.0.1:3000/auth/connections/callback")
    user_id, return_url = ca.decode_state(state)
    assert user_id == "user_abc"
    assert return_url.endswith("/auth/connections/callback")


def test_public_account_row_not_configured():
    os.environ.pop("GITHUB_CLIENT_ID", None)
    os.environ.pop("GITHUB_CLIENT_SECRET", None)
    row = ca.public_account_row("github", None)
    assert row["configured"] is False
    assert row["connected"] is False
    assert "Configure keys on server" in row["message"]


def test_public_account_row_connected_masks_token():
    doc = {
        "provider": "github",
        "access_token": "secret-token",
        "scopes": ["read:user"],
        "connected_at": "2026-01-01T00:00:00+00:00",
        "profile": {"login": "octocat", "display": "octocat"},
    }
    os.environ["GITHUB_CLIENT_ID"] = "id"
    os.environ["GITHUB_CLIENT_SECRET"] = "secret"
    row = ca.public_account_row("github", doc)
    assert row["connected"] is True
    assert row["profile"]["login"] == "octocat"
    assert "access_token" not in row


def test_is_provider_configured_github():
    os.environ["GITHUB_CLIENT_ID"] = "cid"
    os.environ["GITHUB_CLIENT_SECRET"] = "sec"
    assert ca.is_provider_configured("github") is True
    os.environ.pop("GITHUB_CLIENT_SECRET", None)
    assert ca.is_provider_configured("github") is False


def test_build_authorize_url_github():
    os.environ["GITHUB_CLIENT_ID"] = "gh_client"
    os.environ["GITHUB_CLIENT_SECRET"] = "gh_secret"
    os.environ["EMO_PUBLIC_BACKEND_URL"] = "https://api.example.com"
    url = ca.build_authorize_url("github", "user_1", "https://app.example.com/auth/connections/callback")
    assert url.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=gh_client" in url
    assert "scope=" in url
