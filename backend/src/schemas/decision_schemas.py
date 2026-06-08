# src/schemas/decision_schemas.py

from enum import StrEnum


class Decision(StrEnum):
    APPROVE = "APPROVE"
    APPROVE_WITH_REVIEW = "APPROVE_WITH_REVIEW"
    DECLINE = "DECLINE"