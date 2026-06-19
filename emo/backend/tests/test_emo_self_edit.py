"""Tests for Émo self-edit versioning."""
import pytest
from emo_self_edit import (
    SECTION_DEFAULTS,
    _smoke_test,
    emo_edit_self,
    emo_restore_self,
    emo_reflect,
    get_identity_overrides,
    MIN_SECTION_LEN,
)


class FakeCollection:
    def __init__(self):
        self.docs = {}

    async def find_one(self, query, projection=None):
        if "version_id" in query:
            for d in self.docs.values():
                if d.get("version_id") == query["version_id"]:
                    return d
            return None
        _id = query.get("_id")
        return self.docs.get(_id)

    async def update_one(self, query, update, upsert=False):
        _id = query["_id"]
        doc = self.docs.get(_id, {"_id": _id})
        if "$set" in update:
            doc.update(update["$set"])
        if "$inc" in update:
            for k, v in update["$inc"].items():
                doc[k] = doc.get(k, 0) + v
        if "$setOnInsert" in update and _id not in self.docs:
            doc.update(update["$setOnInsert"])
        self.docs[_id] = doc

    async def insert_one(self, doc):
        key = doc.get("version_id") or doc.get("_id")
        self.docs[key] = doc

    async def delete_one(self, query):
        vid = query.get("version_id")
        if vid and vid in self.docs:
            del self.docs[vid]

    def find(self, query, projection=None):
        return self

    def sort(self, *args, **kwargs):
        return self

    async def to_list(self, limit):
        items = [d for d in self.docs.values() if d.get("version_id")]
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[:limit]


class FakeDB:
    def __init__(self):
        self.emo_identity = FakeCollection()
        self.emo_identity_versions = FakeCollection()


@pytest.mark.asyncio
async def test_edit_self_creates_backup_and_applies():
    db = FakeDB()
    section = "mode_creatif"
    new_content = SECTION_DEFAULTS[section] + "\n# test patch\n" + ("x" * MIN_SECTION_LEN)
    result = await emo_edit_self(db, "user1", section, new_content, reason="test")
    assert result["ok"] is True
    overrides = await get_identity_overrides(db)
    assert section in overrides
    assert "test patch" in overrides[section]


@pytest.mark.asyncio
async def test_edit_self_rejects_invalid_prompt():
    db = FakeDB()
    bad = "x" * MIN_SECTION_LEN
    result = await emo_edit_self(db, "user1", "core_identity", bad, reason="bad")
    assert result["ok"] is False
    assert result.get("restored") is True
    overrides = await get_identity_overrides(db)
    assert "core_identity" not in overrides


@pytest.mark.asyncio
async def test_restore_self():
    db = FakeDB()
    section = "mode_brutal"
    content = SECTION_DEFAULTS[section] + "\n# restored line\n" + ("y" * MIN_SECTION_LEN)
    applied = await emo_edit_self(db, "user1", section, content, reason="apply")
    assert applied["ok"]
    version_id = applied["version_id"]

    await db.emo_identity.update_one({"_id": "active"}, {"$set": {"sections": {}}})

    restored = await emo_restore_self(db, "user1", version_id)
    assert restored["ok"] is True
    overrides = await get_identity_overrides(db)
    assert "restored line" in overrides.get(section, "")


@pytest.mark.asyncio
async def test_emo_reflect():
    db = FakeDB()
    r = await emo_reflect(db, "u1", "Je réfléchis à comment améliorer mon mode créatif.", plan="emo_read_self puis edit", introspect=False)
    assert r["ok"]
    assert len(r["thought"]) > 10


def test_smoke_test_accepts_defaults():
    ok, err = _smoke_test({})
    assert ok is True
    assert err == ""
