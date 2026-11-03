"""Database-operator workplace-node inventory and emergency revocation."""
import argparse
import json

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import User, WorkplaceNode
from app.services.session_service import utc
from app.services.workplace_nodes import revoke_workplace_node


def list_nodes(db: Session, username: str) -> list[WorkplaceNode]:
    if not db.get(User, username):
        raise ValueError("Account not found.")
    return db.query(WorkplaceNode).filter(WorkplaceNode.username == username).order_by(
        WorkplaceNode.slot, WorkplaceNode.created_at.desc()
    ).all()


def operator_revoke_node(db: Session, username: str, node_id: str, reason: str) -> None:
    reason = reason.strip()
    if not 8 <= len(reason) <= 300:
        raise ValueError("Record a revocation reason between 8 and 300 characters.")
    node = db.get(WorkplaceNode, node_id)
    if not node or node.username != username:
        raise ValueError("Active workplace node not found for this account.")
    revoke_workplace_node(db, node, event_type="WORKPLACE_NODE_OPERATOR_REVOKED", reason=reason)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or revoke workplace nodes using operator database access.")
    commands = parser.add_subparsers(dest="command", required=True)
    inventory = commands.add_parser("list", help="List enrolled workplace nodes")
    inventory.add_argument("--username", required=True)
    revoke = commands.add_parser("revoke", help="Revoke a lost or stolen node")
    revoke.add_argument("--username", required=True)
    revoke.add_argument("--node-id", required=True)
    revoke.add_argument("--reason", required=True, help="Reason saved in the security audit event")
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.command == "list":
            rows = list_nodes(db, args.username)
            if not rows:
                print("No workplace nodes found for this account.")
            for row in rows:
                print(json.dumps({
                    "slot": row.slot, "id": row.id, "label": row.label,
                    "created_at": utc(row.created_at).isoformat(),
                    "revoked_at": utc(row.revoked_at).isoformat() if row.revoked_at else None,
                }))
            return
        typed = input(f"Type the node ID {args.node_id!r} to confirm revocation: ").strip()
        if typed != args.node_id:
            raise SystemExit("Confirmation did not match; no node was changed.")
        operator_revoke_node(db, args.username, args.node_id, args.reason)
    print("Node revoked. Office grants, pending approvals, and enrollment codes for this account were cleared.")


if __name__ == "__main__":
    main()
