import hashlib

import pytest

import app.core.password_policy as policy
from app.core.build_blocklist import build_blocklist
from app.core.password_policy import validate_password
from app.core.security import hash_password, verify_password


def test_argon2id_round_trip():
    encoded = hash_password("a long and unique passphrase")
    assert encoded.startswith("$argon2id$")
    assert verify_password("a long and unique passphrase", encoded).valid
    assert not verify_password("incorrect password", encoded).valid


def test_policy_prefers_length_over_composition_rules():
    result = validate_password("a sufficiently long passphrase")
    assert result.accepted


def test_policy_rejects_short_and_compromised_passwords():
    assert not validate_password("too short").accepted
    assert not validate_password("passwordpassword").accepted


def test_policy_rejects_context_specific_words():
    result = validate_password(
        "student-account-passphrase",
        username="student",
        email="student@example.com",
    )
    assert not result.accepted


def test_offline_breach_corpus_rejects_whole_passwords(tmp_path, monkeypatch):
    source = tmp_path / "source.txt"
    corpus = tmp_path / "corpus.sqlite3"
    source.write_text("# local candidates\norchard meadow lantern 2026\norchard meadow lantern 2026\n", encoding="utf-8")
    assert build_blocklist(source, corpus, "plaintext") == 1
    monkeypatch.setattr(policy, "HASH_BLOCKLIST_PATH", corpus)
    assert not validate_password("orchard meadow lantern 2026").accepted
    assert validate_password("violet telescope river 2026").accepted

    digest = hashlib.sha1("granite meadow lantern 2026".encode()).hexdigest().upper()
    source.write_text(f"{digest}:42\n", encoding="utf-8")
    assert build_blocklist(source, corpus, "sha1-count") == 1
    assert not validate_password("granite meadow lantern 2026").accepted
    assert validate_password("orchard meadow lantern 2026").accepted


def test_bad_corpus_is_rejected_without_replacing_previous_one(tmp_path):
    source = tmp_path / "source.txt"
    corpus = tmp_path / "corpus.sqlite3"
    source.write_text("valid example password 2026\n", encoding="utf-8")
    build_blocklist(source, corpus, "plaintext")
    before = corpus.read_bytes()
    source.write_text("invalid-hash:1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        build_blocklist(source, corpus, "sha1-count")
    assert corpus.read_bytes() == before


def test_offline_breach_corpus_merge_preserves_existing_and_rejects_bad_source(tmp_path, monkeypatch):
    original = tmp_path / "original.txt"
    new = tmp_path / "breached.txt"
    corpus = tmp_path / "corpus.sqlite3"
    original.write_text("orchard meadow lantern 2026\n", encoding="utf-8")
    assert build_blocklist(original, corpus, "plaintext") == 1
    leaked = "thisisalongpassword"
    new.write_text(f"{hashlib.sha1(leaked.encode()).hexdigest().upper()}:826\n", encoding="utf-8")
    assert build_blocklist(new, corpus, "sha1-count", merge=True) == 2
    monkeypatch.setattr(policy, "HASH_BLOCKLIST_PATH", corpus)
    assert not validate_password("orchard meadow lantern 2026").accepted
    assert not validate_password(leaked).accepted
    before = corpus.read_bytes()
    new.write_text("broken\n", encoding="utf-8")
    with pytest.raises(ValueError):
        build_blocklist(new, corpus, "sha1-count", merge=True)
    assert corpus.read_bytes() == before
