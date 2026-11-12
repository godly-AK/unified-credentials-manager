"""Create documented sample accounts in a local demo database only."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_ACCOUNTS = (
    ("ucm_reader_demo", "reader@example.test", "Violet orbit lantern 9274!"),
    ("ucm_monitor_demo", "monitor@example.test", "Cobalt meadow compass 5831!"),
)


def seed_accounts(db):
    """Create missing ordinary accounts; never reset an existing account."""
    from app.db.models import User
    from app.services.auth_service import AuthService

    results = []
    for username, email, password in DEMO_ACCOUNTS:
        if db.get(User, username):
            results.append((username, "already exists; password and role unchanged"))
            continue
        success, details = AuthService.register_user(db, username, password, email, "127.0.0.1")
        if not success:
            raise RuntimeError(f"Could not create {username}: {details.get('error')}")
        results.append((username, "created as an ordinary account"))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=("local", "phone-lab"))
    args = parser.parse_args()
    demo_path = ROOT / ".demo"
    expected = demo_path / ("ucm.sqlite3" if args.target == "local" else "phone-lab/ucm.sqlite3")
    demo_root, database = demo_path.resolve(), expected.resolve()
    if demo_root != demo_path or database != expected or not database.is_file():
        raise SystemExit("The selected local demo database does not exist or is outside the project. Start the selected demo first.")

    # This process has access only to the explicitly selected local SQLite file.
    os.environ["APP_ENV"] = "development"
    os.environ["DATABASE_URL_OVERRIDE"] = "sqlite:///" + database.as_posix()
    sys.path.insert(0, str(ROOT / "backend"))
    from app.db.database import SessionLocal

    with SessionLocal() as db:
        for username, message in seed_accounts(db):
            print(f"{username}: {message}")
    print("Enroll the main phone and assign the monitoring role separately; no admin role was granted.")


if __name__ == "__main__":
    main()
