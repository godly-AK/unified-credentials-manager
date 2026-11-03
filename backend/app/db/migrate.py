"""Upgrade a fresh database, or baseline an existing matching UCM schema safely."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.db.database import Base, engine
import app.db.models  # noqa: F401 - populate Base.metadata


INITIAL_REVISION = "02ab954e12a1"


def validate_existing_schema(*, initial: bool = False, previous_head: bool = False,
                             pre_node_quorum: bool = False) -> None:
    inspector = inspect(engine)
    actual_tables = {name for name in inspector.get_table_names()
                     if not name.startswith("sqlite_") and name != "alembic_version"}
    expected_tables = set(Base.metadata.tables)
    if initial:
        expected_tables.remove("security_alert_reviews")
    if initial or previous_head or pre_node_quorum:
        expected_tables.remove("login_node_approvals")
    missing = expected_tables - actual_tables
    extra = actual_tables - expected_tables
    if missing or extra:
        raise RuntimeError(
            f"Existing schema does not match the initial UCM migration. Missing tables: {sorted(missing)}; "
            f"unexpected tables: {sorted(extra)}. Back up the database and migrate the legacy schema explicitly."
        )
    for table_name in expected_tables:
        table = Base.metadata.tables[table_name]
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        expected_columns = set(table.columns.keys())
        if initial and table_name == "users":
            expected_columns.remove("is_admin")
        if (initial or previous_head) and table_name == "login_trust_challenges":
            expected_columns.remove("approval_code")
        if actual_columns != expected_columns:
            raise RuntimeError(
                f"Existing {table_name} columns differ. Missing: {sorted(expected_columns - actual_columns)}; "
                f"unexpected: {sorted(actual_columns - expected_columns)}. No migration was applied."
            )
        actual_primary_key = set(inspector.get_pk_constraint(table_name).get("constrained_columns") or [])
        expected_primary_key = {column.name for column in table.primary_key.columns}
        if actual_primary_key != expected_primary_key:
            raise RuntimeError(f"Existing {table_name} primary key differs; no migration was applied.")
        actual_foreign_keys = {
            (tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]))
            for fk in inspector.get_foreign_keys(table_name)
        }
        expected_foreign_keys = {
            (tuple(element.parent.name for element in foreign_key.elements),
             foreign_key.elements[0].column.table.name,
             tuple(element.column.name for element in foreign_key.elements))
            for foreign_key in table.foreign_key_constraints
        }
        if actual_foreign_keys != expected_foreign_keys:
            raise RuntimeError(f"Existing {table_name} foreign keys differ; no migration was applied.")
        actual_indexes = {(index["name"], bool(index["unique"])) for index in inspector.get_indexes(table_name)}
        expected_indexes = {(index.name, bool(index.unique)) for index in table.indexes}
        if (initial or previous_head) and table_name == "login_trust_challenges":
            expected_indexes.remove(("ix_login_trust_challenges_approval_code", True))
        if not expected_indexes <= actual_indexes:
            raise RuntimeError(
                f"Existing {table_name} indexes are incomplete: {sorted(expected_indexes - actual_indexes)}. "
                "No migration was applied."
            )


def upgrade() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    tables = set(inspect(engine).get_table_names())
    if "alembic_version" not in tables and tables:
        try:
            validate_existing_schema()
        except RuntimeError:
            try:
                validate_existing_schema(pre_node_quorum=True)
            except RuntimeError:
                try:
                    validate_existing_schema(previous_head=True)
                except RuntimeError:
                    validate_existing_schema(initial=True)
                    command.stamp(config, INITIAL_REVISION)
                else:
                    command.stamp(config, "b7e942d0c531")
            else:
                command.stamp(config, "c1d64a8f29b0")
        else:
            command.stamp(config, "head")
        command.upgrade(config, "head")
    else:
        command.upgrade(config, "head")
    validate_existing_schema()


if __name__ == "__main__":
    upgrade()
