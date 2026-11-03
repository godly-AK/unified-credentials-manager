"""Build a local breach-hash lookup from plaintext or HIBP SHA-1:count lines."""
import argparse
import hashlib
import os
import sqlite3
import tempfile
import unicodedata
from contextlib import closing
from pathlib import Path

from app.core.password_policy import HASH_BLOCKLIST_PATH


def parse_digest(value: str, source_format: str, line_number: int) -> bytes | None:
    value = value.rstrip("\r\n")
    if not value or value.startswith("#"):
        return None
    if source_format == "plaintext":
        return hashlib.sha1(unicodedata.normalize("NFC", value).encode("utf-8")).digest()
    hash_text, separator, count = value.partition(":")
    if separator != ":" or len(hash_text) != 40 or not count.isdigit() or int(count) < 1:
        raise ValueError(f"Invalid SHA-1:count entry on line {line_number}.")
    try:
        return bytes.fromhex(hash_text)
    except ValueError as error:
        raise ValueError(f"Invalid SHA-1 hash on line {line_number}.") from error


def build_blocklist(source: Path, destination: Path, source_format: str, *, merge: bool = False) -> int:
    if source_format not in {"plaintext", "sha1-count"}:
        raise ValueError("Source format must be plaintext or sha1-count.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(prefix="ucm-blocklist-", suffix=".sqlite3",
                                                        dir=destination.parent)
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        with closing(sqlite3.connect(temporary)) as db, db:
            if merge:
                if not destination.is_file():
                    raise ValueError("An existing blocklist is required for --merge.")
                with closing(sqlite3.connect(f"file:{destination.as_posix()}?mode=ro", uri=True)) as old:
                    if old.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise RuntimeError("Existing blocklist integrity check failed.")
                    if not old.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='blocked_sha1'").fetchone():
                        raise ValueError("Existing blocklist has no blocked_sha1 table.")
                    old.backup(db)
            else:
                db.execute("CREATE TABLE blocked_sha1 (digest BLOB PRIMARY KEY) WITHOUT ROWID")
            batch: list[tuple[bytes]] = []
            with source.open("r", encoding="utf-8-sig", errors="strict") as input_file:
                for line_number, line in enumerate(input_file, start=1):
                    digest = parse_digest(line, source_format, line_number)
                    if digest is None:
                        continue
                    batch.append((digest,))
                    if len(batch) >= 5000:
                        db.executemany("INSERT OR IGNORE INTO blocked_sha1 VALUES (?)", batch)
                        batch.clear()
                if batch:
                    db.executemany("INSERT OR IGNORE INTO blocked_sha1 VALUES (?)", batch)
            total = db.execute("SELECT COUNT(*) FROM blocked_sha1").fetchone()[0]
            if total == 0:
                raise ValueError("The source contains no usable password hashes.")
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Blocklist database integrity check failed.")
        os.replace(temporary, destination)
        return total
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an offline UCM compromised-password lookup.")
    parser.add_argument("source", type=Path, help="Local source file; no network requests are made")
    parser.add_argument("--format", choices=["plaintext", "sha1-count"], required=True)
    parser.add_argument("--output", type=Path, default=HASH_BLOCKLIST_PATH)
    parser.add_argument("--merge", action="store_true", help="Preserve the existing indexed hashes and add this source")
    args = parser.parse_args()
    count = build_blocklist(args.source, args.output, args.format, merge=args.merge)
    print(f"Indexed {count} distinct password hashes at {args.output}")


if __name__ == "__main__":
    main()
