"""
Align the transactions.decision CHECK constraint with the new decision labels
emitted by services/decision_service.py (APPROVE / APPROVE_WITH_REVIEW /
DECLINE).

The original constraint only allowed the stale legacy labels
ALLOW / REVIEW / BLOCK and caused every POST /api/v1/transactions to fail
with `transactions_fraud_decision_check`. We keep the legacy labels in the
new constraint so any pre-existing rows remain valid.

Idempotent: drops the existing constraint (if present) before recreating.
Run:
    cd backend
    python -m scripts.apply_decision_constraint_alignment
"""

from sqlalchemy import text

from src.db.session import engine

CONSTRAINT_NAME = "transactions_fraud_decision_check"
ALLOWED = [
    "APPROVE",
    "APPROVE_WITH_REVIEW",
    "DECLINE",
    # legacy values kept so historical rows remain valid
    "ALLOW",
    "REVIEW",
    "BLOCK",
]


def main() -> None:
    values = ", ".join(f"'{v}'" for v in ALLOWED)
    with engine.begin() as conn:
        conn.execute(
            text(f"ALTER TABLE transactions DROP CONSTRAINT IF EXISTS {CONSTRAINT_NAME}")
        )
        conn.execute(
            text(
                f"ALTER TABLE transactions ADD CONSTRAINT {CONSTRAINT_NAME} "
                f"CHECK (decision IS NULL OR decision = ANY (ARRAY[{values}]))"
            )
        )
    print(f"Constraint {CONSTRAINT_NAME} now allows: {ALLOWED}")


if __name__ == "__main__":
    main()
