"""Émo backend integration tests."""
import os
import time
import json
import uuid
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://emo-personal.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

UNIQUE = uuid.uuid4().hex[:8]
EMAIL = f"test_{UNIQUE}@example.com"
PASSWORD = "emo-test-2026"
NAME = f"Tester {UNIQUE}"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth_session(session):
    r = session.post(f"{API}/auth/signup", json={"email": EMAIL, "password": PASSWORD, "name": NAME})
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["email"] == EMAIL
    # Extract token from Set-Cookie (cookie is HttpOnly/secure/samesite=none — requests session has it)
    return session


# ---------------- AUTH ---------------- #

def test_health(session):
    r = session.get(f"{API}/")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_signup_duplicate(auth_session):
    r = auth_session.post(f"{API}/auth/signup", json={"email": EMAIL, "password": PASSWORD, "name": NAME})
    assert r.status_code == 409


def test_me(auth_session):
    r = auth_session.get(f"{API}/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == EMAIL
    assert data["name"] == NAME
    assert data["auth_provider"] == "password"


def test_login_wrong_password(session):
    r = session.post(f"{API}/auth/login", json={"email": EMAIL, "password": "wrongpw"})
    assert r.status_code == 401


def test_login_success_and_bearer_auth():
    # Use new session, capture session_token cookie
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200, r.text
    token = s.cookies.get("session_token")
    assert token, "session_token cookie not set"
    # Verify Bearer auth works on a fresh session (no cookies)
    s2 = requests.Session()
    r2 = s2.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["email"] == EMAIL


def test_me_unauthenticated(session):
    s = requests.Session()
    r = s.get(f"{API}/auth/me")
    assert r.status_code == 401


# ---------------- CONVERSATIONS ---------------- #

@pytest.fixture(scope="module")
def conversation_id(auth_session):
    r = auth_session.post(f"{API}/conversations", json={"title": "TEST_conv", "mode": "normal"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["title"] == "TEST_conv"
    assert data["mode"] == "normal"
    assert "conversation_id" in data
    assert "_id" not in data
    return data["conversation_id"]


def test_list_conversations(auth_session, conversation_id):
    r = auth_session.get(f"{API}/conversations")
    assert r.status_code == 200
    ids = [c["conversation_id"] for c in r.json()]
    assert conversation_id in ids


def test_rename_conversation(auth_session, conversation_id):
    r = auth_session.patch(f"{API}/conversations/{conversation_id}", json={"title": "TEST_renamed"})
    assert r.status_code == 200
    r2 = auth_session.get(f"{API}/conversations")
    titles = {c["conversation_id"]: c["title"] for c in r2.json()}
    assert titles[conversation_id] == "TEST_renamed"


def test_messages_empty(auth_session, conversation_id):
    r = auth_session.get(f"{API}/conversations/{conversation_id}/messages")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_rename_not_found(auth_session):
    r = auth_session.patch(f"{API}/conversations/conv_nonexistent", json={"title": "x"})
    assert r.status_code == 404


# ---------------- CHAT STREAM ---------------- #

def _stream_chat(auth_session, conv_id, content, mode="normal"):
    r = auth_session.post(
        f"{API}/chat/stream",
        json={"conversation_id": conv_id, "content": content, "mode": mode},
        stream=True,
        timeout=90,
    )
    assert r.status_code == 200, r.text
    deltas = []
    done = None
    err = None
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data: "):
            payload = json.loads(line[6:])
            if payload["type"] == "delta":
                deltas.append(payload["content"])
            elif payload["type"] == "done":
                done = payload
            elif payload["type"] == "error":
                err = payload
    return deltas, done, err


def test_chat_stream_normal_and_autotitle(auth_session):
    # Fresh conversation to test auto-title
    rc = auth_session.post(f"{API}/conversations", json={})
    cid = rc.json()["conversation_id"]
    deltas, done, err = _stream_chat(auth_session, cid, "Dis bonjour en une phrase.", "normal")
    assert err is None, f"stream error: {err}"
    assert len(deltas) > 0, "no deltas received"
    full = "".join(deltas)
    assert done is not None, "no done event"
    assert done.get("mood"), "mood missing in done event"
    # Persona: must not claim to be Claude
    assert "claude" not in full.lower(), f"Persona leak: {full}"
    # Auto-title set from first user message
    convs = auth_session.get(f"{API}/conversations").json()
    titles = {c["conversation_id"]: c["title"] for c in convs}
    assert titles[cid] != "Nouvelle conversation", f"auto-title not set: {titles[cid]}"

    # Messages persisted
    msgs = auth_session.get(f"{API}/conversations/{cid}/messages").json()
    assert len(msgs) >= 2
    roles = [m["role"] for m in msgs]
    assert "user" in roles and "emo" in roles
    emo_msg = next(m for m in msgs if m["role"] == "emo")
    assert "[MOOD:" not in emo_msg["content"], "MOOD tag not stripped from stored content"
    assert emo_msg.get("mood") in (
        "neutre", "amusee", "concentree", "sarcastique", "enthousiaste", "agacee", "curieuse", "pensive"
    )


def test_chat_stream_tech_mode_persona(auth_session):
    rc = auth_session.post(f"{API}/conversations", json={"mode": "tech"})
    cid = rc.json()["conversation_id"]
    deltas, done, err = _stream_chat(auth_session, cid, "Qui es-tu ?", "tech")
    assert err is None
    full = "".join(deltas).lower()
    # Emo may say "pas Claude" (denying Claude identity) — that's fine.
    # The real failure mode is claiming to BE Claude.
    forbidden = ["je suis claude", "i am claude", "i'm claude", "modèle anthropic", "model anthropic"]
    for phrase in forbidden:
        assert phrase not in full, f"Emo claimed Claude identity: {full}"
    assert "émo" in full or "emo" in full, f"Emo identity missing: {full}"


# ---------------- DELETE ---------------- #

def test_delete_conversation(auth_session, conversation_id):
    r = auth_session.delete(f"{API}/conversations/{conversation_id}")
    assert r.status_code == 200
    # Verify gone
    r2 = auth_session.get(f"{API}/conversations/{conversation_id}/messages")
    assert r2.status_code == 404


def test_logout(auth_session):
    r = auth_session.post(f"{API}/auth/logout")
    assert r.status_code == 200
    r2 = auth_session.get(f"{API}/auth/me")
    assert r2.status_code == 401
