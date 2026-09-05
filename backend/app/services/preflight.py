"""Payroll Preflight (Phase 8): a deterministic payroll readiness & risk engine.

Preflight inspects an already-computed Payrun and surfaces real payroll
problems BEFORE validation / payment. It is NOT a second warning system —
it reuses the existing severity vocabulary (BLOCKER / WARNING / INFO from
`WarningSeverity`), the canonical contract-applicability service
(`contract_rules.get_applicable_contract` semantics), the canonical
overlapping-payslip rule (`contract_rules.ranges_overlap`), and the
BLOCKER `PayrollWarning`s the compute engine already produces.

Design contract (see PHASE 8 spec):
- Preflight is a DERIVED readiness assessment of a COMPUTED Payrun. It
  persists nothing and does NOT introduce a new Payrun status. The
  canonical state machine (DRAFT -> COMPUTED -> VALIDATED -> PAID) is
  untouched.
- Every finding is reproducible from database facts + an explicit rule.
  No AI is involved anywhere in this module. An optional AI layer may
  later SUMMARISE findings, but never classify them.
- `readiness` is purely a function of the finding counts:
    any BLOCKER          -> ACTION_REQUIRED
    else any WARNING      -> REVIEW_RECOMMENDED
    else                 -> READY
- The validation gate calls `evaluate_findings()` directly (after a fresh
  recompute) so a stale "READY" from the UI can never let a blocker
  through — see payroll_engine.validate_payrun.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.contract import Contract
from app.models.time_off import TimeOffRequest, RequestStatus
from app.models.payroll import (
    Payrun, Payslip, PayrunStatus, RuleCategory, WarningSeverity,
)
from app.services import contract_rules, attendance_rules

logger = logging.getLogger("payloom.preflight")

TWO_PLACES = Decimal("0.01")


def _q2(value: Decimal) -> Decimal:
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Centralised thresholds (spec sections 21 / 24): no magic numbers buried
# inside individual checks. Tune here; every check reads from this object.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class PreflightThresholds:
    # Salary variance is flagged only when BOTH cross their bar, so a tiny
    # salary swinging by a large % (or a large salary nudged by a few
    # rupees) doesn't produce noise.
    net_variance_percent: Decimal = Decimal("25")
    net_variance_min_absolute: Decimal = Decimal("5000")
    # A single Attendance session longer than this is almost certainly a
    # missed check-out rather than real worked time.
    max_single_session_hours: Decimal = Decimal("16")
    # Worked substantially more calendar days than the Working Schedule
    # expected in the period (e.g. unplanned weekend work).
    worked_days_ratio: Decimal = Decimal("1.5")


THRESHOLDS = PreflightThresholds()


# ---------------------------------------------------------------- categories
CATEGORY_CONTRACT = "CONTRACT"
CATEGORY_EMPLOYEE = "EMPLOYEE_DATA"
CATEGORY_ATTENDANCE = "ATTENDANCE"
CATEGORY_TIME_OFF = "TIME_OFF"
CATEGORY_CONFIG = "PAYROLL_CONFIGURATION"
CATEGORY_INTEGRITY = "PAYSLIP_INTEGRITY"
CATEGORY_VARIANCE = "PAYROLL_VARIANCE"
CATEGORY_DUPLICATES = "DUPLICATES"

_SEVERITY_ORDER = {WarningSeverity.BLOCKER: 0, WarningSeverity.WARNING: 1, WarningSeverity.INFO: 2}

_READINESS_NOT_RUN = "NOT_RUN"
_READINESS_ACTION_REQUIRED = "ACTION_REQUIRED"
_READINESS_REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"
_READINESS_READY = "READY"


@dataclass
class PreflightFinding:
    code: str
    severity: WarningSeverity
    category: str
    message: str
    employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    payslip_id: Optional[int] = None
    evidence: dict = field(default_factory=dict)
    resolution: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "payslip_id": self.payslip_id,
            "evidence": self.evidence,
            "resolution": self.resolution,
        }


# --------------------------------------------------------------- the context
@dataclass
class PreflightContext:
    """Built ONCE per Preflight run (spec section 66/67) so individual
    checks never issue their own per-employee queries."""
    db: Session
    payrun: Payrun
    payslips: list[Payslip]
    period_start: date
    period_end: date
    # employee_id -> ("OK", Contract) | ("MISSING", None) | ("CONFLICT", [Contract, ...])
    contract_resolution: dict[int, tuple[str, object]]
    attendance_by_employee: dict[int, list[Attendance]]
    approved_time_off_by_employee: dict[int, list[TimeOffRequest]]
    previous_payslip_by_employee: dict[int, Optional[Payslip]]
    other_payslips_by_employee: dict[int, list[Payslip]]

    def employee_name(self, payslip: Payslip) -> str:
        e = payslip.employee
        return f"{e.first_name} {e.last_name}" if e else f"Employee #{payslip.employee_id}"


def _resolve_contract(contracts: list[Contract], ps: date, pe: date) -> tuple[str, object]:
    applicable = [c for c in contracts if contract_rules.ranges_overlap(ps, pe, c.start_date, c.end_date)]
    if not applicable:
        return ("MISSING", None)
    if len(applicable) > 1:
        return ("CONFLICT", applicable)
    return ("OK", applicable[0])


def load_context(db: Session, payrun: Payrun) -> PreflightContext:
    payslips = list(payrun.payslips)
    employee_ids = [p.employee_id for p in payslips]
    ps, pe = payrun.period_start, payrun.period_end

    contracts_by_employee: dict[int, list[Contract]] = {eid: [] for eid in employee_ids}
    if employee_ids:
        for c in db.query(Contract).filter(Contract.employee_id.in_(employee_ids)).all():
            contracts_by_employee.setdefault(c.employee_id, []).append(c)
    contract_resolution = {
        eid: _resolve_contract(contracts_by_employee.get(eid, []), ps, pe) for eid in employee_ids
    }

    attendance_by_employee: dict[int, list[Attendance]] = {eid: [] for eid in employee_ids}
    if employee_ids:
        rows = (
            db.query(Attendance)
            .filter(
                Attendance.employee_id.in_(employee_ids),
                Attendance.attendance_date >= ps,
                Attendance.attendance_date <= pe,
            )
            .all()
        )
        for r in rows:
            attendance_by_employee.setdefault(r.employee_id, []).append(r)

    time_off_by_employee: dict[int, list[TimeOffRequest]] = {eid: [] for eid in employee_ids}
    if employee_ids:
        rows = (
            db.query(TimeOffRequest)
            .filter(
                TimeOffRequest.employee_id.in_(employee_ids),
                TimeOffRequest.status == RequestStatus.APPROVED,
                TimeOffRequest.start_date <= pe,
                TimeOffRequest.end_date >= ps,
            )
            .all()
        )
        for r in rows:
            time_off_by_employee.setdefault(r.employee_id, []).append(r)

    previous_payslip_by_employee: dict[int, Optional[Payslip]] = {eid: None for eid in employee_ids}
    other_payslips_by_employee: dict[int, list[Payslip]] = {eid: [] for eid in employee_ids}
    if employee_ids:
        others = (
            db.query(Payslip)
            .filter(
                Payslip.employee_id.in_(employee_ids),
                Payslip.payrun_id != payrun.id,
            )
            .all()
        )
        prev_candidates: dict[int, list[Payslip]] = {}
        for other in others:
            other_payslips_by_employee.setdefault(other.employee_id, []).append(other)
            # Variance baseline: a strictly-earlier, already-computed Payslip.
            if other.period_start < ps and other.computed_at is not None:
                prev_candidates.setdefault(other.employee_id, []).append(other)
        for eid, candidates in prev_candidates.items():
            candidates.sort(key=lambda p: p.period_start, reverse=True)
            previous_payslip_by_employee[eid] = candidates[0]

    return PreflightContext(
        db=db,
        payrun=payrun,
        payslips=payslips,
        period_start=ps,
        period_end=pe,
        contract_resolution=contract_resolution,
        attendance_by_employee=attendance_by_employee,
        approved_time_off_by_employee=time_off_by_employee,
        previous_payslip_by_employee=previous_payslip_by_employee,
        other_payslips_by_employee=other_payslips_by_employee,
    )


# --------------------------------------------------------------- check helpers
def _payslip_has_blocker(payslip: Payslip) -> bool:
    return any(w.severity == WarningSeverity.BLOCKER for w in payslip.warnings)


def _period_str(ps: date, pe: date) -> str:
    return f"{ps.isoformat()} to {pe.isoformat()}"


def _finding(ctx: PreflightContext, payslip: Payslip, **kwargs) -> PreflightFinding:
    return PreflightFinding(
        employee_id=payslip.employee_id,
        employee_name=ctx.employee_name(payslip),
        payslip_id=payslip.id,
        **kwargs,
    )


# --------------------------------------------------------------------- checks
def _check_missing_contract(ctx: PreflightContext) -> list[PreflightFinding]:
    out = []
    for p in ctx.payslips:
        state, _ = ctx.contract_resolution.get(p.employee_id, ("MISSING", None))
        if state == "MISSING":
            out.append(_finding(
                ctx, p,
                code="MISSING_APPLICABLE_CONTRACT",
                severity=WarningSeverity.BLOCKER,
                category=CATEGORY_CONTRACT,
                message=f"{ctx.employee_name(p)} has no contract applicable to {_period_str(ctx.period_start, ctx.period_end)}.",
                evidence={"period_start": ctx.period_start.isoformat(), "period_end": ctx.period_end.isoformat()},
                resolution="Create or correct this employee's contract so it covers the payroll period, then recompute the Payrun.",
            ))
    return out


def _check_contract_conflict(ctx: PreflightContext) -> list[PreflightFinding]:
    out = []
    for p in ctx.payslips:
        state, payload = ctx.contract_resolution.get(p.employee_id, ("MISSING", None))
        if state == "CONFLICT":
            contracts = payload
            out.append(_finding(
                ctx, p,
                code="CONTRACT_CONFLICT",
                severity=WarningSeverity.BLOCKER,
                category=CATEGORY_CONTRACT,
                message=f"{len(contracts)} contracts overlap the payroll period for {ctx.employee_name(p)}; exactly one must apply.",
                evidence={
                    "contracts": [
                        {
                            "reference": c.reference,
                            "start_date": c.start_date.isoformat(),
                            "end_date": c.end_date.isoformat() if c.end_date else None,
                        }
                        for c in contracts
                    ],
                },
                resolution="Adjust the contract validity dates so only one contract covers this period.",
            ))
    return out


def _check_duplicate_payslip(ctx: PreflightContext) -> list[PreflightFinding]:
    out = []
    for p in ctx.payslips:
        dupes = [
            other for other in ctx.other_payslips_by_employee.get(p.employee_id, [])
            if contract_rules.ranges_overlap(p.period_start, p.period_end, other.period_start, other.period_end)
        ]
        if not dupes:
            continue
        out.append(_finding(
            ctx, p,
            code="DUPLICATE_PAYSLIP",
            severity=WarningSeverity.BLOCKER,
            category=CATEGORY_DUPLICATES,
            message=f"{ctx.employee_name(p)} is already on another Payrun for an overlapping period.",
            evidence={
                "duplicates": [
                    {
                        "payslip_id": d.id,
                        "payrun_id": d.payrun_id,
                        "payrun_reference": d.payrun.reference if d.payrun else None,
                        "status": d.status.value,
                        "period_start": d.period_start.isoformat(),
                        "period_end": d.period_end.isoformat(),
                    }
                    for d in dupes
                ],
            },
            resolution="Remove this employee from one of the overlapping Payruns, or correct the payroll period.",
        ))
    return out


def _check_salary_structure(ctx: PreflightContext) -> list[PreflightFinding]:
    out = []
    for p in ctx.payslips:
        structure = p.salary_structure
        if structure is None:
            out.append(_finding(
                ctx, p,
                code="MISSING_SALARY_STRUCTURE",
                severity=WarningSeverity.BLOCKER,
                category=CATEGORY_CONFIG,
                message=f"{ctx.employee_name(p)}'s Payslip has no Salary Structure attached.",
                evidence={},
                resolution="Recreate the Payrun with a valid Salary Structure.",
            ))
            continue
        active_rules = [r for r in structure.rules if r.is_active]
        if not active_rules:
            out.append(_finding(
                ctx, p,
                code="SALARY_STRUCTURE_HAS_NO_RULES",
                severity=WarningSeverity.BLOCKER,
                category=CATEGORY_CONFIG,
                message=f"Salary Structure '{structure.name}' has no active Salary Rules.",
                evidence={"salary_structure_id": structure.id, "salary_structure_name": structure.name},
                resolution="Add active Salary Rules to this structure, then recompute the Payrun.",
            ))
            continue
        if not any(r.category == RuleCategory.NET for r in active_rules):
            out.append(_finding(
                ctx, p,
                code="SALARY_STRUCTURE_HAS_NO_NET_RULE",
                severity=WarningSeverity.BLOCKER,
                category=CATEGORY_CONFIG,
                message=f"Salary Structure '{structure.name}' has no Net Pay rule — the Payslip has no terminal result.",
                evidence={"salary_structure_id": structure.id, "salary_structure_name": structure.name},
                resolution="Add a NET-category Salary Rule that derives Net Pay, then recompute the Payrun.",
            ))
    return out


# Engine codes handled by their own dedicated checks above — don't also
# surface the raw compute-time warning for them (would double-report).
_BRIDGE_SUPPRESS = {"MISSING_CONTRACT", "CONFLICTING_CONTRACT", "DUPLICATE_PAYSLIP"}

# Better home for the compute engine's own warning codes when bridged.
_BRIDGE_CATEGORY = {
    "RULE_FAILURE": CATEGORY_INTEGRITY,
    "MISSING_WAGE": CATEGORY_CONTRACT,
    "INACTIVE_EMPLOYEE": CATEGORY_EMPLOYEE,
    "PAYROLL_BLOCKER": CATEGORY_INTEGRITY,
}


def _check_computation_integrity(ctx: PreflightContext) -> list[PreflightFinding]:
    """Bridge the BLOCKER/WARNING `PayrollWarning`s the compute engine
    already produced (RULE_FAILURE, missing wage, ...) into Preflight
    findings so they live in one coherent readiness view."""
    out = []
    for p in ctx.payslips:
        for w in p.warnings:
            if w.code in _BRIDGE_SUPPRESS:
                continue
            out.append(_finding(
                ctx, p,
                code=w.code,
                severity=w.severity,
                category=_BRIDGE_CATEGORY.get(w.code, CATEGORY_INTEGRITY),
                message=w.message,
                evidence={"origin": "compute_engine"},
                resolution=(
                    "Fix the Salary Rule or contract data this calculation depends on, then recompute the Payrun."
                    if w.severity == WarningSeverity.BLOCKER else None
                ),
            ))
    return out


def _check_payslip_totals(ctx: PreflightContext) -> list[PreflightFinding]:
    """Persisted Basic/Allowances/Gross/Deductions/Net must equal the sum
    of the Payslip's own calculation lines by category. Decimal-exact —
    never a float comparison (spec section 18)."""
    out = []
    fields = [
        ("basic", RuleCategory.BASIC),
        ("allowances", RuleCategory.ALLOWANCE),
        ("gross", RuleCategory.GROSS),
        ("deductions", RuleCategory.DEDUCTION),
        ("net", RuleCategory.NET),
    ]
    for p in ctx.payslips:
        if p.computed_at is None or not p.lines:
            continue
        mismatches = {}
        for field_name, category in fields:
            calculated = _q2(sum((l.amount for l in p.lines if l.category_snapshot == category), Decimal(0)))
            persisted = _q2(getattr(p, field_name) or Decimal(0))
            if calculated != persisted:
                mismatches[field_name] = {"calculated": str(calculated), "persisted": str(persisted)}
        if mismatches:
            out.append(_finding(
                ctx, p,
                code="PAYSLIP_TOTAL_MISMATCH",
                severity=WarningSeverity.BLOCKER,
                category=CATEGORY_INTEGRITY,
                message=f"{ctx.employee_name(p)}'s persisted Payslip totals disagree with its calculation lines.",
                evidence={"mismatches": mismatches},
                resolution="Recompute the Payrun to rebuild the Payslip from its calculation lines.",
            ))
    return out


def _check_negative_net(ctx: PreflightContext) -> list[PreflightFinding]:
    out = []
    for p in ctx.payslips:
        if p.computed_at is None or not p.lines or _payslip_has_blocker(p):
            continue
        if (p.net or Decimal(0)) < 0:
            out.append(_finding(
                ctx, p,
                code="NEGATIVE_NET_PAY",
                severity=WarningSeverity.BLOCKER,
                category=CATEGORY_INTEGRITY,
                message=f"{ctx.employee_name(p)}'s Net Pay is negative ({_q2(p.net)}).",
                evidence={"net": str(_q2(p.net)), "gross": str(_q2(p.gross or Decimal(0))), "deductions": str(_q2(p.deductions or Decimal(0)))},
                resolution="Review the Salary Rules — total deductions exceed total pay for this employee.",
            ))
    return out


def _check_extreme_deductions(ctx: PreflightContext) -> list[PreflightFinding]:
    out = []
    for p in ctx.payslips:
        if p.computed_at is None or not p.lines or _payslip_has_blocker(p):
            continue
        gross = p.gross or Decimal(0)
        deductions = p.deductions or Decimal(0)
        if gross > 0 and deductions > gross:
            out.append(_finding(
                ctx, p,
                code="DEDUCTIONS_EXCEED_GROSS",
                severity=WarningSeverity.WARNING,
                category=CATEGORY_VARIANCE,
                message=f"{ctx.employee_name(p)}'s deductions ({_q2(deductions)}) exceed gross pay ({_q2(gross)}).",
                evidence={"gross": str(_q2(gross)), "deductions": str(_q2(deductions)), "net": str(_q2(p.net or Decimal(0)))},
                resolution="Confirm the deduction Salary Rules are configured correctly for this employee.",
            ))
    return out


def _check_incomplete_attendance(ctx: PreflightContext) -> list[PreflightFinding]:
    today = attendance_rules.today_in_company_tz()
    out = []
    for p in ctx.payslips:
        records = ctx.attendance_by_employee.get(p.employee_id, [])
        incomplete = [r for r in records if r.check_out is None]
        if not incomplete:
            continue
        out.append(_finding(
            ctx, p,
            code="INCOMPLETE_ATTENDANCE",
            severity=WarningSeverity.WARNING,
            category=CATEGORY_ATTENDANCE,
            message=f"{ctx.employee_name(p)} has {len(incomplete)} Attendance record(s) with no check-out inside this payroll period.",
            evidence={
                "records": [
                    {
                        "date": r.attendance_date.isoformat(),
                        "status": attendance_rules.derive_status(r.check_in, r.check_out, r.attendance_date),
                    }
                    for r in sorted(incomplete, key=lambda x: x.attendance_date)
                ],
                "as_of": today.isoformat(),
            },
            resolution="Add the missing check-out via an Attendance correction, or confirm the records are expected, then re-run Preflight.",
        ))
    return out


def _check_attendance_anomaly(ctx: PreflightContext) -> list[PreflightFinding]:
    out = []
    max_minutes = THRESHOLDS.max_single_session_hours * Decimal(60)
    for p in ctx.payslips:
        records = ctx.attendance_by_employee.get(p.employee_id, [])
        long_sessions = []
        for r in records:
            minutes = attendance_rules.derive_worked_minutes(r.check_in, r.check_out)
            if minutes is not None and Decimal(minutes) > max_minutes:
                long_sessions.append({"date": r.attendance_date.isoformat(), "hours": str(_q2(Decimal(minutes) / Decimal(60)))})
        if long_sessions:
            out.append(_finding(
                ctx, p,
                code="LONG_ATTENDANCE_SESSION",
                severity=WarningSeverity.WARNING,
                category=CATEGORY_ATTENDANCE,
                message=f"{ctx.employee_name(p)} has an Attendance session longer than {THRESHOLDS.max_single_session_hours}h — likely a missed check-out.",
                evidence={"sessions": long_sessions, "threshold_hours": str(THRESHOLDS.max_single_session_hours)},
                resolution="Verify the check-in / check-out times for the flagged day(s).",
            ))

        worked_days = p.worked_days
        expected_days = p.expected_work_days
        if worked_days is not None and expected_days and expected_days > 0:
            if Decimal(worked_days) > Decimal(expected_days) * THRESHOLDS.worked_days_ratio:
                out.append(_finding(
                    ctx, p,
                    code="ATTENDANCE_ABOVE_SCHEDULE",
                    severity=WarningSeverity.WARNING,
                    category=CATEGORY_ATTENDANCE,
                    message=f"{ctx.employee_name(p)} worked {worked_days} days against {expected_days} scheduled in this period.",
                    evidence={"worked_days": str(worked_days), "expected_work_days": str(expected_days)},
                    resolution="Confirm the extra worked days are expected (e.g. approved weekend work).",
                ))
    return out


def _check_time_off_context(ctx: PreflightContext) -> list[PreflightFinding]:
    out = []
    for p in ctx.payslips:
        requests = ctx.approved_time_off_by_employee.get(p.employee_id, [])
        if not requests:
            continue
        out.append(_finding(
            ctx, p,
            code="APPROVED_TIME_OFF_IN_PERIOD",
            severity=WarningSeverity.INFO,
            category=CATEGORY_TIME_OFF,
            message=f"{ctx.employee_name(p)} had approved time off overlapping this payroll period.",
            evidence={
                "requests": [
                    {
                        "type": r.time_off_type.name if r.time_off_type else None,
                        "unit": r.time_off_type.unit.value if r.time_off_type else None,
                        "amount": str(r.duration_amount),
                        "start_date": r.start_date.isoformat(),
                        "end_date": r.end_date.isoformat(),
                    }
                    for r in requests
                ],
                "note": "Contextual only — this payroll engine does not reduce pay for leave unless a Salary Rule formula explicitly uses approved_leave_days.",
            },
            resolution=None,
        ))
    return out


def _check_salary_variance(ctx: PreflightContext) -> list[PreflightFinding]:
    out = []
    for p in ctx.payslips:
        if p.computed_at is None or not p.lines or _payslip_has_blocker(p):
            continue
        previous = ctx.previous_payslip_by_employee.get(p.employee_id)
        if previous is None:
            out.append(_finding(
                ctx, p,
                code="NO_PREVIOUS_PAYSLIP",
                severity=WarningSeverity.INFO,
                category=CATEGORY_VARIANCE,
                message=f"No previous Payslip exists for {ctx.employee_name(p)} — salary variance cannot be compared.",
                evidence={},
                resolution=None,
            ))
            continue

        previous_net = _q2(previous.net or Decimal(0))
        current_net = _q2(p.net or Decimal(0))
        delta = _q2(current_net - previous_net)
        pct: Optional[Decimal] = None
        if previous_net != 0:
            pct = _q2(abs(delta) / abs(previous_net) * Decimal(100))

        crosses_absolute = abs(delta) >= THRESHOLDS.net_variance_min_absolute
        crosses_percent = previous_net == 0 or (pct is not None and pct >= THRESHOLDS.net_variance_percent)
        if crosses_absolute and crosses_percent:
            direction = "increased" if delta > 0 else "decreased"
            pct_label = f"{pct}%" if pct is not None else "n/a (previous Net was 0)"
            out.append(_finding(
                ctx, p,
                code="LARGE_NET_VARIANCE",
                severity=WarningSeverity.WARNING,
                category=CATEGORY_VARIANCE,
                message=f"{ctx.employee_name(p)}'s Net Pay {direction} by {abs(delta)} ({pct_label}) versus the previous Payslip. Review recommended.",
                evidence={
                    "previous_net": str(previous_net),
                    "current_net": str(current_net),
                    "absolute_delta": str(delta),
                    "percentage_delta": str(pct) if pct is not None else None,
                    "previous_payslip_id": previous.id,
                    "previous_payrun_reference": previous.payrun.reference if previous.payrun else None,
                    "previous_period": _period_str(previous.period_start, previous.period_end),
                },
                resolution="Open PayTrace for this Payslip to confirm the change is expected.",
            ))
    return out


def _check_contract_boundary(ctx: PreflightContext) -> list[PreflightFinding]:
    out = []
    for p in ctx.payslips:
        state, payload = ctx.contract_resolution.get(p.employee_id, ("MISSING", None))
        if state != "OK":
            continue
        contract = payload
        if contract.start_date > ctx.period_start:
            out.append(_finding(
                ctx, p,
                code="CONTRACT_STARTS_MID_PERIOD",
                severity=WarningSeverity.INFO,
                category=CATEGORY_CONTRACT,
                message=f"{ctx.employee_name(p)}'s contract {contract.reference} begins on {contract.start_date.isoformat()}, after the payroll period start.",
                evidence={
                    "contract_reference": contract.reference,
                    "contract_start": contract.start_date.isoformat(),
                    "period_start": ctx.period_start.isoformat(),
                    "note": "This engine does not prorate — the full structure was applied.",
                },
                resolution=None,
            ))
        if contract.end_date is not None and contract.end_date < ctx.period_end:
            out.append(_finding(
                ctx, p,
                code="CONTRACT_ENDS_MID_PERIOD",
                severity=WarningSeverity.INFO,
                category=CATEGORY_CONTRACT,
                message=f"{ctx.employee_name(p)}'s contract {contract.reference} ends on {contract.end_date.isoformat()}, before the payroll period end.",
                evidence={
                    "contract_reference": contract.reference,
                    "contract_end": contract.end_date.isoformat(),
                    "period_end": ctx.period_end.isoformat(),
                    "note": "This engine does not prorate — the full structure was applied.",
                },
                resolution=None,
            ))
    return out


@dataclass(frozen=True)
class PreflightCheck:
    code: str
    name: str
    category: str
    evaluate: Callable[[PreflightContext], list[PreflightFinding]]


PREFLIGHT_CHECKS: list[PreflightCheck] = [
    PreflightCheck("MISSING_APPLICABLE_CONTRACT", "Applicable contract", CATEGORY_CONTRACT, _check_missing_contract),
    PreflightCheck("CONTRACT_CONFLICT", "Contract conflict", CATEGORY_CONTRACT, _check_contract_conflict),
    PreflightCheck("DUPLICATE_PAYSLIP", "Duplicate payslip", CATEGORY_DUPLICATES, _check_duplicate_payslip),
    PreflightCheck("SALARY_STRUCTURE", "Salary structure availability", CATEGORY_CONFIG, _check_salary_structure),
    PreflightCheck("COMPUTATION_INTEGRITY", "Salary rule execution integrity", CATEGORY_INTEGRITY, _check_computation_integrity),
    PreflightCheck("PAYSLIP_TOTALS", "Payslip total integrity", CATEGORY_INTEGRITY, _check_payslip_totals),
    PreflightCheck("NEGATIVE_NET", "Negative or impossible Net", CATEGORY_INTEGRITY, _check_negative_net),
    PreflightCheck("EXTREME_DEDUCTIONS", "Extreme deduction relationship", CATEGORY_VARIANCE, _check_extreme_deductions),
    PreflightCheck("INCOMPLETE_ATTENDANCE", "Attendance incompleteness", CATEGORY_ATTENDANCE, _check_incomplete_attendance),
    PreflightCheck("ATTENDANCE_ANOMALY", "Attendance anomaly", CATEGORY_ATTENDANCE, _check_attendance_anomaly),
    PreflightCheck("TIME_OFF_CONTEXT", "Time off context", CATEGORY_TIME_OFF, _check_time_off_context),
    PreflightCheck("SALARY_VARIANCE", "Salary variance", CATEGORY_VARIANCE, _check_salary_variance),
    PreflightCheck("CONTRACT_BOUNDARY", "Payroll period / contract boundary", CATEGORY_CONTRACT, _check_contract_boundary),
]


def _sort_key(f: PreflightFinding) -> tuple:
    return (_SEVERITY_ORDER.get(f.severity, 9), f.category, f.employee_name or "", f.code)


def evaluate_findings(db: Session, payrun: Payrun) -> list[PreflightFinding]:
    """Run every check against a freshly-loaded context and return the
    normalized, sorted findings. A check that raises unexpectedly becomes
    a BLOCKER `PREFLIGHT_CHECK_ERROR` — Preflight fails safe rather than
    silently declaring payroll READY (spec section 68)."""
    ctx = load_context(db, payrun)
    findings: list[PreflightFinding] = []
    for check in PREFLIGHT_CHECKS:
        try:
            findings.extend(check.evaluate(ctx) or [])
        except Exception:  # noqa: BLE001 — deliberately broad, logged, fails safe
            logger.exception("Preflight check %s failed for payrun %s", check.code, payrun.id)
            findings.append(PreflightFinding(
                code="PREFLIGHT_CHECK_ERROR",
                severity=WarningSeverity.BLOCKER,
                category=check.category,
                message=f"Preflight could not complete the '{check.name}' check, so payroll integrity is unverified.",
                evidence={"check": check.code},
                resolution="Re-run Preflight. If this persists, a payroll administrator should investigate before validating.",
            ))
    findings.sort(key=_sort_key)
    return findings


def _summarize(findings: list[PreflightFinding]) -> dict:
    return {
        "blockers": sum(1 for f in findings if f.severity == WarningSeverity.BLOCKER),
        "warnings": sum(1 for f in findings if f.severity == WarningSeverity.WARNING),
        "info": sum(1 for f in findings if f.severity == WarningSeverity.INFO),
    }


def _readiness(summary: dict) -> str:
    if summary["blockers"] > 0:
        return _READINESS_ACTION_REQUIRED
    if summary["warnings"] > 0:
        return _READINESS_REVIEW_RECOMMENDED
    return _READINESS_READY


def run_preflight(db: Session, payrun: Payrun) -> dict:
    """The public read model for the Preflight endpoint. Persists nothing."""
    base = {
        "payrun_id": payrun.id,
        "reference": payrun.reference,
        "status": payrun.status.value,
        "period": {"start": payrun.period_start.isoformat(), "end": payrun.period_end.isoformat()},
        "employee_count": len(payrun.payslips),
        "generated_at": _now_iso(),
    }

    if payrun.status == PayrunStatus.DRAFT:
        return {
            **base,
            "readiness": _READINESS_NOT_RUN,
            "summary": {"blockers": 0, "warnings": 0, "info": 0},
            "findings": [],
            "message": "Compute this Payrun before running Preflight.",
        }

    findings = evaluate_findings(db, payrun)
    summary = _summarize(findings)
    return {
        **base,
        "readiness": _readiness(summary),
        "summary": summary,
        "findings": [f.to_dict() for f in findings],
        "message": None,
    }
