"""Copy accounts from known pre-Alembic UCM schemas into a new database."""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.db.database import Base
from app.db.models import User  # registers current tables


LEGACY_USERS_COLUMNS = {
    "username", "password_hash", "emails", "last_access_time", "token", "last_ip_addr",
    "public_key", "fcm_token", "passwd_changed", "blocked", "created_at",
}
LEGACY_RESET_COLUMNS = {"username", "challenge_b64", "created_at"}
INTERMEDIATE_HISTORY_COLUMNS = {"id", "username", "password_hash", "created_at"}
INTERMEDIATE_EVENT_COLUMNS = {
    "id", "event_type", "username", "ip_address", "risk_level", "details", "created_at",
}
PRESERVED_COLUMNS = (
    "username", "password_hash", "emails", "last_access_time", "last_ip_addr",
    "public_key", "passwd_changed", "blocked", "created_at",
)


def restore_datetimes(rows: list[dict], *columns: str) -> None:
    """SQLite text queries return timestamps as strings; typed inserts need datetimes."""
    for row in rows:
        for column in columns:
            if isinstance(row[column], str):
                row[column] = datetime.fromisoformat(row[column])


def read_accounts(connection) -> list[dict]:
    rows = [dict(row._mapping) for row in connection.execute(text(
        "SELECT username, password_hash, emails, last_access_time, last_ip_addr, "
        "public_key, passwd_changed, blocked, created_at FROM users"
    ))]
    restore_datetimes(rows, "last_access_time", "passwd_changed", "created_at")
    seen_emails: set[str] = set()
    for row in rows:
        email = row["emails"]
        if not isinstance(email, str) or not email.strip():
            raise ValueError(f"Legacy account {row['username']!r} has no email. Resolve it before import.")
        folded = email.casefold()
        if folded in seen_emails:
            raise ValueError(f"Legacy email {email!r} is duplicated. Resolve it before import.")
        seen_emails.add(folded)
    return rows


def read_source(connection) -> tuple[list[dict], list[dict], list[dict]]:
    inspector = inspect(connection)
    tables = {name for name in inspector.get_table_names() if not name.startswith("sqlite_")}
    original = tables == {"users", "reset_challenges"}
    intermediate = tables == {"users", "reset_challenges", "password_history", "security_events"}
    if not (original or intermediate):
        raise ValueError(f"Expected a known two- or four-table pre-Alembic UCM schema; found {sorted(tables)}.")
    expected_users = LEGACY_USERS_COLUMNS if original else set(PRESERVED_COLUMNS)
    expected_columns = {"users": expected_users, "reset_challenges": LEGACY_RESET_COLUMNS}
    if intermediate:
        expected_columns.update({"password_history": INTERMEDIATE_HISTORY_COLUMNS,
                                 "security_events": INTERMEDIATE_EVENT_COLUMNS})
    for table_name, columns in expected_columns.items():
        if {column["name"] for column in inspector.get_columns(table_name)} != columns:
            raise ValueError(f"The source {table_name} columns do not match a known UCM schema. No data was copied.")
    accounts = read_accounts(connection)
    if not intermediate:
        return accounts, [], []
    histories = [dict(row._mapping) for row in connection.execute(text(
        "SELECT username, password_hash, created_at FROM password_history ORDER BY id"
    ))]
    events = [dict(row._mapping) for row in connection.execute(text(
        "SELECT event_type, username, ip_address, risk_level, details, created_at "
        "FROM security_events ORDER BY id"
    ))]
    restore_datetimes(histories, "created_at")
    restore_datetimes(events, "created_at")
    for event in events:
        if isinstance(event["details"], str):
            event["details"] = json.loads(event["details"])
    return accounts, histories, events


def import_legacy(source_url: str, destination_url: str) -> int:
    if source_url == destination_url:
        raise ValueError("Source and destination must be different databases.")
    source = create_engine(source_url)
    destination = create_engine(destination_url)
    try:
        with source.connect() as source_connection:
            accounts, histories, events = read_source(source_connection)
        with destination.begin() as destination_connection:
            existing = {name for name in inspect(destination_connection).get_table_names()
                        if not name.startswith("sqlite_")}
            if existing:
                raise ValueError(f"Destination must be empty; found {sorted(existing)}.")
            backend_root = Path(__file__).resolve().parents[2]
            config = Config(str(backend_root / "alembic.ini"))
            config.set_main_option("script_location", str(backend_root / "migrations"))
            config.attributes["connection"] = destination_connection
            command.upgrade(config, "head")
            if accounts:
                destination_connection.execute(Base.metadata.tables["users"].insert(), [
                    {column: row[column] for column in PRESERVED_COLUMNS} for row in accounts
                ])
            if histories:
                destination_connection.execute(Base.metadata.tables["password_history"].insert(), histories)
            if events:
                destination_connection.execute(Base.metadata.tables["security_events"].insert(), events)
            migrated = destination_connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
            if migrated != len(accounts):
                raise RuntimeError("Account count changed during import; destination was not committed.")
            if destination_connection.execute(text("SELECT COUNT(*) FROM password_history")).scalar_one() != len(histories):
                raise RuntimeError("Password history count changed during import; destination was not committed.")
            if destination_connection.execute(text("SELECT COUNT(*) FROM security_events")).scalar_one() != len(events):
                raise RuntimeError("Security event count changed during import; destination was not committed.")
        return len(accounts)
    finally:
        source.dispose()
        destination.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy known pre-Alembic UCM data into a fresh migrated database.")
    parser.add_argument("--source-url", default=os.environ.get("UCM_LEGACY_SOURCE_URL"))
    parser.add_argument("--destination-url", default=os.environ.get("UCM_NEW_DATABASE_URL"))
    args = parser.parse_args()
    if not args.source_url or not args.destination_url:
        parser.error("Provide both database URLs as arguments or UCM_LEGACY_SOURCE_URL and UCM_NEW_DATABASE_URL.")
    count = import_legacy(args.source_url, args.destination_url)
    print(f"Imported {count} accounts. Old web tokens, push tokens, and reset challenges were not copied.")


if __name__ == "__main__":
    main()
