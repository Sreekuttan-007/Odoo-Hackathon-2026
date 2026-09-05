"""The Payroll calculation engine: eligibility, the Salary Rule execution
engine, and the Payrun state machine.

Policy (documented per docs/DOMAIN_TERMS.md):
- Salary Rules ACTUALLY drive Payslip calculations — nothing is hardcoded.
  Basic/Allowances/Gross/Deductions/Net on a Payslip are always the sum of
  that Payslip's PayslipLine amounts grouped by category; GROSS and NET are
  themselves ordinary rules (typically FORMULA) whose author decides how
  they're derived from earlier rules — the engine never invents totals.
- Rules execute strictly by `sequence` ascending. A rule may reference an
  earlier rule's result (`rules["CODE"]`) or a running category total
  (`categories["CATEGORY"]`) — both dicts only ever contain rules that have
  already executed, so forward references are structurally impossible, not
  merely disallowed by convention.
- Money is Decimal end-to-end, quantized to 2 decimal places with
  ROUND_HALF_UP at the point each rule's amount is produced.
- A rule computation failure (unknown dependency, division by zero, bad
  formula syntax) never becomes a silent 0. It's recorded as a BLOCKER
  PayrollWarning on that employee's Payslip and the line is omitted — any
  later rule that depended on it fails too (its code is simply absent from
  `rules`), so the failure is visible everywhere it propagates rather than
  hidden.
- Every computed value (worked_days, contract used, rule amounts) is
  snapshotted onto the Payslip/PayslipLine at compute time. Editing a
  Salary Rule afterward can never retroactively change a Payslip that was
  already computed with the old rule — only a fresh recompute picks up
  the new rule, and recompute is blocked once VALIDATED/PAID.
"""
import json
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import NamedTuple, Optional
from sqlalchemy.orm import Session
from app.models.employee import Employee, EmployeeStatus
from app.models.contract import Contract
from app.models.attendance import Attendance
from app.models.time_off import TimeOffRequest, RequestStatus, TimeOffUnit
from app.models.payroll import (
    Payrun, Payslip, PayslipLine, PayrollWarning,
    SalaryRule, ComputationMethod, PayrunStatus, WarningSeverity,
)
from app.services import contract_rules, attendance_rules, time_off_rules, formula_engine

TWO_PLACES = Decimal("0.01")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def q2(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class InvalidTransitionError(ValueError):
    def __init__(self, current_status: str, action: str):
        super().__init__(f"Cannot {action} a Payrun in {current_status} status.")


class NoEmployeesSelectedError(ValueError):
    def __init__(self):
        super().__init__("At least one employee must be selected.")


class InvalidPeriodError(ValueError):
    def __init__(self):
        super().__init__("period_end must be on or after period_start.")


class IneligibleEmployeesError(ValueError):
    def __init__(self, details: list[dict]):
        self.details = details
        super().__init__("One or more selected employees are not eligible for this payroll period.")


class ValidationBlockedError(ValueError):
    def __init__(self, findings: list):
        # Phase 8: carries the full Preflight blocker findings. The
        # per-payslip id list stays available for the existing API shape.
        self.findings = findings
        self.blocking_payslip_ids = sorted({f.payslip_id for f in findings if f.payslip_id is not None})
        super().__init__("This Payrun has unresolved Preflight blockers and cannot be validated.")


class EligibilityResult(NamedTuple):
    eligible: bool
    code: Optional[str]
    reason: Optional[str]
    contract: Optional[Contract]


def find_overlapping_payslip(
    db: Session, employee_id: int, period_start: date, period_end: date, exclude_payrun_id: Optional[int] = None
) -> Optional[Payslip]:
    query = db.query(Payslip).filter(Payslip.employee_id == employee_id)
    if exclude_payrun_id is not None:
        query = query.filter(Payslip.payrun_id != exclude_payrun_id)
    for existing in query.all():
        if contract_rules.ranges_overlap(period_start, period_end, existing.period_start, existing.period_end):
            return existing
    return None


def check_eligibility(
    db: Session, employee: Employee, period_start: date, period_end: date, exclude_payrun_id: Optional[int] = None
) -> EligibilityResult:
    if employee.status != EmployeeStatus.ACTIVE:
        return EligibilityResult(False, "INACTIVE_EMPLOYEE", "Employee is not active.", None)

    try:
        contract = contract_rules.get_applicable_contract(db, employee.id, period_start, period_end)
    except contract_rules.NoApplicableContractError:
        return EligibilityResult(False, "MISSING_CONTRACT", "Missing applicable contract for this period.", None)
    except contract_rules.ConflictingContractsError:
        return EligibilityResult(False, "CONFLICTING_CONTRACT", "Conflicting contracts for this period.", None)

    if contract.wage_monthly is None or contract.wage_monthly <= 0:
        return EligibilityResult(False, "MISSING_WAGE", "Contract has no valid wage.", None)

    duplicate = find_overlapping_payslip(db, employee.id, period_start, period_end, exclude_payrun_id=exclude_payrun_id)
    if duplicate is not None:
        return EligibilityResult(False, "DUPLICATE_PAYSLIP", f"Duplicate payslip already exists for an overlapping period (Payrun #{duplicate.payrun_id}).", None)

    return EligibilityResult(True, None, None, contract)


def generate_reference(db: Session, period_start: date) -> str:
    year = period_start.year
    prefix = f"PR/{year}/"
    existing_count = db.query(Payrun).filter(Payrun.reference.like(f"{prefix}%")).count()
    sequence = existing_count + 1
    reference = f"{prefix}{sequence:04d}"
    while db.query(Payrun).filter(Payrun.reference == reference).first() is not None:
        sequence += 1
        reference = f"{prefix}{sequence:04d}"
    return reference


def _build_context(db: Session, employee: Employee, contract: Contract, period_start: date, period_end: date) -> dict:
    attendance_records = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee.id,
            Attendance.attendance_date >= period_start,
            Attendance.attendance_date <= period_end,
            Attendance.check_out.isnot(None),
        )
        .all()
    )
    worked_days = Decimal(len(attendance_records))
    worked_minutes = sum(
        (attendance_rules.derive_worked_minutes(r.check_in, r.check_out) or 0) for r in attendance_records
    )
    overtime_minutes = sum(
        (attendance_rules.compute_overtime_minutes(employee, r.attendance_date, attendance_rules.derive_worked_minutes(r.check_in, r.check_out)) or 0)
        for r in attendance_records
    )
    expected_work_days = Decimal(len(time_off_rules.scheduled_working_days(employee, period_start, period_end)))

    # Approved leave: only DAYS-unit types are counted here. Paid/unpaid
    # leave behavior isn't distinguished yet (TimeOffType has no such
    # metadata) — see docs/DOMAIN_TERMS.md. This context value is exposed
    # for formulas to use; the engine never applies it automatically.
    approved_requests = (
        db.query(TimeOffRequest)
        .filter(
            TimeOffRequest.employee_id == employee.id,
            TimeOffRequest.status == RequestStatus.APPROVED,
            TimeOffRequest.start_date <= period_end,
            TimeOffRequest.end_date >= period_start,
        )
        .all()
    )
    approved_leave_days = sum(
        (r.duration_amount for r in approved_requests if r.time_off_type.unit == TimeOffUnit.DAYS),
        Decimal(0),
    )

    return {
        "contract_wage": Decimal(contract.wage_monthly),
        "worked_days": worked_days,
        "expected_work_days": expected_work_days,
        "worked_hours": Decimal(worked_minutes) / Decimal(60),
        "overtime_hours": Decimal(overtime_minutes) / Decimal(60),
        "approved_leave_days": approved_leave_days,
        "rules": {},
        "categories": {},
    }


class RuleAmount(NamedTuple):
    amount: Decimal
    base_desc: str
    # Structured PayTrace snapshot fields (Phase 7) — None where not
    # applicable to this rule's computation_method.
    fixed_amount: Optional[Decimal] = None
    percentage: Optional[Decimal] = None
    base_code: Optional[str] = None
    base_amount: Optional[Decimal] = None
    formula_inputs: Optional[dict] = None


def _compute_rule_amount(rule: SalaryRule, context: dict) -> RuleAmount:
    quantity = Decimal(rule.quantity) if rule.quantity is not None else Decimal(1)

    if rule.computation_method == ComputationMethod.FIXED:
        if rule.fixed_amount is None:
            raise formula_engine.FormulaError("Fixed rule has no fixed_amount configured.")
        amount = Decimal(rule.fixed_amount) * quantity
        base_desc = f"Fixed {rule.fixed_amount}" + (f" x{quantity}" if quantity != 1 else "")
        return RuleAmount(q2(amount), base_desc, fixed_amount=Decimal(rule.fixed_amount))

    if rule.computation_method == ComputationMethod.PERCENTAGE:
        if rule.percentage is None or not rule.percentage_base:
            raise formula_engine.FormulaError("Percentage rule is missing percentage or percentage_base.")
        if rule.percentage_base == "CONTRACT_WAGE":
            base_value = context["contract_wage"]
            base_label = "Contract Wage"
        else:
            if rule.percentage_base not in context["rules"]:
                raise formula_engine.FormulaError(f"Unknown percentage_base rule code: {rule.percentage_base}")
            base_value = context["rules"][rule.percentage_base]
            base_label = rule.percentage_base
        amount = base_value * (Decimal(rule.percentage) / Decimal(100)) * quantity
        base_desc = f"{rule.percentage}% of {base_label} ({base_value})"
        return RuleAmount(
            q2(amount), base_desc,
            percentage=Decimal(rule.percentage), base_code=rule.percentage_base, base_amount=base_value,
        )

    if rule.computation_method == ComputationMethod.FORMULA:
        if not rule.formula_expression:
            raise formula_engine.FormulaError("Formula rule has no formula_expression configured.")
        amount = formula_engine.evaluate_formula(rule.formula_expression, context) * quantity
        inputs = formula_engine.extract_inputs(rule.formula_expression, context)
        return RuleAmount(q2(amount), rule.formula_expression, formula_inputs=inputs)

    raise formula_engine.FormulaError(f"Unsupported computation method: {rule.computation_method}")


def compute_payslip(db: Session, payslip: Payslip) -> None:
    """Recomputes one Payslip in place: clears prior lines/warnings, resolves
    the applicable Contract, builds context, executes the structure's active
    rules in sequence, and sets category totals. Never raises — failures
    become BLOCKER PayrollWarnings attached to this payslip."""
    payslip.lines.clear()
    payslip.warnings.clear()

    eligibility = check_eligibility(db, payslip.employee, payslip.period_start, payslip.period_end, exclude_payrun_id=payslip.payrun_id)
    if not eligibility.eligible or eligibility.contract is None:
        payslip.warnings.append(PayrollWarning(
            severity=WarningSeverity.BLOCKER, code=eligibility.code or "PAYROLL_BLOCKER",
            message=eligibility.reason or "Not eligible.",
        ))
        payslip.contract_id = None
        payslip.worked_days = None
        payslip.expected_work_days = None
        payslip.worked_hours = None
        payslip.basic = payslip.allowances = payslip.gross = payslip.deductions = payslip.net = Decimal(0)
        payslip.warning_count = len(payslip.warnings)
        payslip.computed_at = now_utc()
        return

    contract = eligibility.contract
    payslip.contract_id = contract.id
    context = _build_context(db, payslip.employee, contract, payslip.period_start, payslip.period_end)
    payslip.worked_days = context["worked_days"]
    payslip.expected_work_days = context["expected_work_days"]
    payslip.worked_hours = q2(context["worked_hours"])

    active_rules = sorted(
        [r for r in payslip.salary_structure.rules if r.is_active],
        key=lambda r: r.sequence,
    )

    for rule in active_rules:
        try:
            result = _compute_rule_amount(rule, context)
        except formula_engine.FormulaError as exc:
            payslip.warnings.append(PayrollWarning(
                severity=WarningSeverity.BLOCKER, code="RULE_FAILURE",
                message=f"Rule {rule.code} failed: {exc}",
            ))
            continue

        amount = result.amount
        context["rules"][rule.code] = amount
        context["categories"][rule.category.value] = context["categories"].get(rule.category.value, Decimal(0)) + amount

        payslip.lines.append(PayslipLine(
            salary_rule_id=rule.id,
            rule_name_snapshot=rule.name,
            rule_code_snapshot=rule.code,
            category_snapshot=rule.category,
            sequence_snapshot=rule.sequence,
            computation_method_snapshot=rule.computation_method,
            base_description_snapshot=result.base_desc,
            amount=amount,
            quantity=rule.quantity,
            fixed_amount_snapshot=result.fixed_amount,
            percentage_snapshot=result.percentage,
            base_code_snapshot=result.base_code,
            base_amount_snapshot=result.base_amount,
            formula_inputs_snapshot=(
                json.dumps({k: str(v) for k, v in result.formula_inputs.items()})
                if result.formula_inputs is not None else None
            ),
        ))

    payslip.basic = context["categories"].get("BASIC", Decimal(0))
    payslip.allowances = context["categories"].get("ALLOWANCE", Decimal(0))
    payslip.gross = context["categories"].get("GROSS", Decimal(0))
    payslip.deductions = context["categories"].get("DEDUCTION", Decimal(0))
    payslip.net = context["categories"].get("NET", Decimal(0))
    payslip.warning_count = len(payslip.warnings)
    payslip.computed_at = now_utc()


def compute_payrun(db: Session, payrun: Payrun) -> None:
    if payrun.status not in (PayrunStatus.DRAFT, PayrunStatus.COMPUTED):
        raise InvalidTransitionError(payrun.status.value, "compute")
    for payslip in payrun.payslips:
        compute_payslip(db, payslip)
        payslip.status = PayrunStatus.COMPUTED
    payrun.status = PayrunStatus.COMPUTED
    payrun.computed_at = now_utc()
    db.commit()
    db.refresh(payrun)


def validate_payrun(db: Session, payrun: Payrun, user) -> None:
    if payrun.status != PayrunStatus.COMPUTED:
        raise InvalidTransitionError(payrun.status.value, "validate")

    # Phase 8 stale-Preflight protection (spec sections 36/65): never trust
    # a prior "READY" — recompute every Payslip from current data, then run
    # the deterministic Preflight engine here on the server immediately
    # before finalizing. A blocker introduced after the last UI Preflight
    # still stops validation.
    from app.services import preflight

    for payslip in payrun.payslips:
        compute_payslip(db, payslip)
    db.flush()

    findings = preflight.evaluate_findings(db, payrun)
    blockers = [f for f in findings if f.severity == WarningSeverity.BLOCKER]
    if blockers:
        db.commit()  # persist the refreshed compute state even though validation is refused
        raise ValidationBlockedError(blockers)

    now = now_utc()
    payrun.status = PayrunStatus.VALIDATED
    payrun.validated_at = now
    payrun.validated_by_user_id = user.id
    for payslip in payrun.payslips:
        payslip.status = PayrunStatus.VALIDATED
        payslip.validated_at = now
    db.commit()
    db.refresh(payrun)


def mark_payrun_paid(db: Session, payrun: Payrun, user) -> None:
    if payrun.status != PayrunStatus.VALIDATED:
        raise InvalidTransitionError(payrun.status.value, "mark paid")
    now = now_utc()
    payrun.status = PayrunStatus.PAID
    payrun.paid_at = now
    payrun.paid_by_user_id = user.id
    for payslip in payrun.payslips:
        payslip.status = PayrunStatus.PAID
        payslip.paid_at = now
    db.commit()
    db.refresh(payrun)
