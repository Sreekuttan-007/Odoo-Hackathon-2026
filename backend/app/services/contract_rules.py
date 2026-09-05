"""Contract business rules: reference generation, overlap protection and
period-applicability — the logic later Payroll phases depend on.

Policy (documented per docs/DOMAIN_TERMS.md):
- A Contract's validity period is [start_date, end_date] with end_date=None
  meaning open-ended (still running).
- Two Contracts for the SAME employee may never have overlapping validity
  periods. This is enforced on create/update, not just as a UI warning.
- Contract status (RUNNING / UPCOMING / EXPIRED) is DERIVED from dates, never
  persisted, so it can never drift out of sync with the dates.
- getApplicableContract(employee_id, period_start, period_end) expects
  exactly one Contract whose validity period overlaps the given period. Zero
  matches is a "missing contract" condition; more than one is a "conflict".
  Both are reported explicitly rather than silently resolved.
"""
from datetime import date
from typing import Optional, Sequence
from sqlalchemy.orm import Session
from app.models.contract import Contract


class ContractOverlapError(ValueError):
    """Raised when a Contract's validity period overlaps another Contract
    already held by the same employee."""

    def __init__(self, conflicting_contract: Contract):
        self.conflicting_contract = conflicting_contract
        super().__init__(
            f"This contract overlaps an existing contract for this employee "
            f"({conflicting_contract.reference})."
        )


class NoApplicableContractError(Exception):
    """Raised when a payroll period has zero applicable contracts."""

    def __init__(self, employee_id: int):
        self.employee_id = employee_id
        super().__init__(f"No applicable contract found for employee {employee_id} for this period.")


class ConflictingContractsError(Exception):
    """Raised when a payroll period has more than one applicable contract."""

    def __init__(self, employee_id: int, contracts: Sequence[Contract]):
        self.employee_id = employee_id
        self.contracts = list(contracts)
        super().__init__(
            f"Multiple conflicting contracts are applicable for employee {employee_id} for this period."
        )


def ranges_overlap(
    start_a: date, end_a: Optional[date], start_b: date, end_b: Optional[date]
) -> bool:
    """True if [start_a, end_a] and [start_b, end_b] overlap. None end = open-ended."""
    starts_before_b_ends = end_b is None or start_a <= end_b
    starts_after_a_begins = end_a is None or start_b <= end_a
    return starts_before_b_ends and starts_after_a_begins


def find_overlapping_contract(
    db: Session,
    employee_id: int,
    start_date: date,
    end_date: Optional[date],
    exclude_contract_id: Optional[int] = None,
) -> Optional[Contract]:
    query = db.query(Contract).filter(Contract.employee_id == employee_id)
    if exclude_contract_id is not None:
        query = query.filter(Contract.id != exclude_contract_id)

    for existing in query.all():
        if ranges_overlap(start_date, end_date, existing.start_date, existing.end_date):
            return existing
    return None


def assert_no_overlap(
    db: Session,
    employee_id: int,
    start_date: date,
    end_date: Optional[date],
    exclude_contract_id: Optional[int] = None,
) -> None:
    conflict = find_overlapping_contract(db, employee_id, start_date, end_date, exclude_contract_id)
    if conflict is not None:
        raise ContractOverlapError(conflict)


def derive_status(start_date: date, end_date: Optional[date], today: Optional[date] = None) -> str:
    today = today or date.today()
    if start_date > today:
        return "UPCOMING"
    if end_date is not None and end_date < today:
        return "EXPIRED"
    return "RUNNING"


def generate_reference(db: Session, start_date: date) -> str:
    year = start_date.year
    prefix = f"CON/{year}/"
    existing_count = (
        db.query(Contract).filter(Contract.reference.like(f"{prefix}%")).count()
    )
    sequence = existing_count + 1
    reference = f"{prefix}{sequence:04d}"
    # Extremely unlikely with sequence-based generation, but guard against a
    # collision (e.g. from concurrent creation) rather than violating the
    # unique constraint silently.
    while db.query(Contract).filter(Contract.reference == reference).first() is not None:
        sequence += 1
        reference = f"{prefix}{sequence:04d}"
    return reference


def get_applicable_contract(
    db: Session, employee_id: int, period_start: date, period_end: date
) -> Contract:
    candidates = (
        db.query(Contract)
        .filter(Contract.employee_id == employee_id)
        .all()
    )
    applicable = [
        c for c in candidates if ranges_overlap(period_start, period_end, c.start_date, c.end_date)
    ]

    if len(applicable) == 0:
        raise NoApplicableContractError(employee_id)
    if len(applicable) > 1:
        raise ConflictingContractsError(employee_id, applicable)
    return applicable[0]
