from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from decimal import Decimal
from app.db.database import get_db
from app.models.employee import Employee, EmployeeStatus
from app.models.user import User
from app.models.payroll import (
    SalaryStructure, SalaryRule, Payrun, Payslip, PayrunStatus, WarningSeverity,
)
from app.schemas.employee import EmployeeMinimal
from app.schemas.payroll import (
    SalaryStructureResponse, SalaryStructureCreate, SalaryStructureUpdate, SalaryStructureDetailResponse,
    SalaryStructureMinimal, SalaryRuleResponse, SalaryRuleCreate, SalaryRuleUpdate,
    EligibleEmployee, PayrunCreate, PayrunResponse, ValidationBlockerDetail,
    PayslipResponse, PayslipSummaryResponse, PayslipLineResponse, PayrollWarningResponse,
)
from app.api.deps import get_current_user, get_current_payroll_operator, get_current_payroll_manager, HR_CAPABLE_ROLES
from app.services import payroll_engine, payslip_pdf
from app.services.schedule_calculator import build_schedule_summary

router = APIRouter()


# ---------------------------------------------------------- Structures ----

def _structure_response(structure: SalaryStructure) -> SalaryStructureResponse:
    return SalaryStructureResponse(
        id=structure.id, name=structure.name, code=structure.code, description=structure.description,
        is_active=structure.is_active, rule_count=len(structure.rules),
        created_at=structure.created_at, updated_at=structure.updated_at,
    )


@router.get("/payroll/structures", response_model=List[SalaryStructureResponse])
def list_structures(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    query = db.query(SalaryStructure)
    if search:
        query = query.filter(SalaryStructure.name.ilike(f"%{search}%"))
    if is_active is not None:
        query = query.filter(SalaryStructure.is_active == is_active)
    structures = query.order_by(SalaryStructure.name).all()
    return [_structure_response(s) for s in structures]


@router.post("/payroll/structures", response_model=SalaryStructureResponse)
def create_structure(
    payload: SalaryStructureCreate,
    db: Session = Depends(get_db),
    current_manager: User = Depends(get_current_payroll_manager),
):
    if payload.code and db.query(SalaryStructure).filter(SalaryStructure.code == payload.code).first():
        raise HTTPException(409, detail={"error": {"code": "DUPLICATE_CODE", "message": "A Salary Structure with this code already exists."}})
    structure = SalaryStructure(**payload.model_dump())
    db.add(structure)
    db.commit()
    db.refresh(structure)
    return _structure_response(structure)


@router.get("/payroll/structures/{structure_id}", response_model=SalaryStructureDetailResponse)
def get_structure(structure_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    structure = db.query(SalaryStructure).filter(SalaryStructure.id == structure_id).first()
    if not structure:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Salary Structure not found."}})
    return SalaryStructureDetailResponse(
        **_structure_response(structure).model_dump(),
        rules=[SalaryRuleResponse.model_validate(r) for r in sorted(structure.rules, key=lambda r: r.sequence)],
    )


@router.patch("/payroll/structures/{structure_id}", response_model=SalaryStructureResponse)
def update_structure(
    structure_id: int,
    payload: SalaryStructureUpdate,
    db: Session = Depends(get_db),
    current_manager: User = Depends(get_current_payroll_manager),
):
    structure = db.query(SalaryStructure).filter(SalaryStructure.id == structure_id).first()
    if not structure:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Salary Structure not found."}})
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"] and db.query(SalaryStructure).filter(SalaryStructure.code == data["code"], SalaryStructure.id != structure_id).first():
        raise HTTPException(409, detail={"error": {"code": "DUPLICATE_CODE", "message": "A Salary Structure with this code already exists."}})
    for field, value in data.items():
        setattr(structure, field, value)
    db.commit()
    db.refresh(structure)
    return _structure_response(structure)


# --------------------------------------------------------------- Rules ----

@router.get("/payroll/rules", response_model=List[SalaryRuleResponse])
def list_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    salary_structure_id: Optional[int] = None,
):
    query = db.query(SalaryRule)
    if salary_structure_id is not None:
        query = query.filter(SalaryRule.salary_structure_id == salary_structure_id)
    return query.order_by(SalaryRule.salary_structure_id, SalaryRule.sequence).all()


@router.post("/payroll/rules", response_model=SalaryRuleResponse)
def create_rule(
    salary_structure_id: int,
    payload: SalaryRuleCreate,
    db: Session = Depends(get_db),
    current_manager: User = Depends(get_current_payroll_manager),
):
    structure = db.query(SalaryStructure).filter(SalaryStructure.id == salary_structure_id).first()
    if not structure:
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Salary Structure not found."}})
    if db.query(SalaryRule).filter(SalaryRule.salary_structure_id == salary_structure_id, SalaryRule.code == payload.code).first():
        raise HTTPException(409, detail={"error": {"code": "DUPLICATE_CODE", "message": "A rule with this code already exists in this structure."}})

    rule = SalaryRule(salary_structure_id=salary_structure_id, **payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/payroll/rules/{rule_id}", response_model=SalaryRuleResponse)
def get_rule(rule_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rule = db.query(SalaryRule).filter(SalaryRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Salary Rule not found."}})
    return rule


@router.patch("/payroll/rules/{rule_id}", response_model=SalaryRuleResponse)
def update_rule(
    rule_id: int,
    payload: SalaryRuleUpdate,
    db: Session = Depends(get_db),
    current_manager: User = Depends(get_current_payroll_manager),
):
    rule = db.query(SalaryRule).filter(SalaryRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Salary Rule not found."}})
    data = payload.model_dump(exclude_unset=True)
    new_code = data.get("code", rule.code)
    if new_code != rule.code and db.query(SalaryRule).filter(SalaryRule.salary_structure_id == rule.salary_structure_id, SalaryRule.code == new_code).first():
        raise HTTPException(409, detail={"error": {"code": "DUPLICATE_CODE", "message": "A rule with this code already exists in this structure."}})
    for field, value in data.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


# -------------------------------------------------------------- Payruns ----

def _actor_name(user: Optional[User]) -> Optional[str]:
    if user and user.employee:
        return f"{user.employee.first_name} {user.employee.last_name}"
    return None


def _payrun_response(payrun: Payrun) -> PayrunResponse:
    payslips = payrun.payslips
    return PayrunResponse(
        id=payrun.id,
        reference=payrun.reference,
        salary_structure=SalaryStructureMinimal.model_validate(payrun.salary_structure),
        period_start=payrun.period_start,
        period_end=payrun.period_end,
        status=payrun.status,
        employee_count=len(payslips),
        total_gross=sum((p.gross for p in payslips), Decimal(0)),
        total_net=sum((p.net for p in payslips), Decimal(0)),
        warning_count=sum(p.warning_count for p in payslips),
        created_by_name=_actor_name(payrun.created_by),
        computed_at=payrun.computed_at,
        validated_at=payrun.validated_at,
        validated_by_name=_actor_name(payrun.validated_by),
        paid_at=payrun.paid_at,
        paid_by_name=_actor_name(payrun.paid_by),
        created_at=payrun.created_at,
        updated_at=payrun.updated_at,
    )


@router.get("/payroll/payruns/eligible-employees", response_model=List[EligibleEmployee])
def eligible_employees(
    salary_structure_id: int,
    period_start: date,
    period_end: date,
    db: Session = Depends(get_db),
    current_operator: User = Depends(get_current_payroll_operator),
):
    """Read-only preview for the Payrun creation wizard's Step 2. Does NOT
    create anything — Step 1's "Continue" only ever calls this GET."""
    if period_end < period_start:
        raise HTTPException(400, detail={"error": {"code": "INVALID_PERIOD", "message": "period_end must be on or after period_start."}})
    if not db.query(SalaryStructure).filter(SalaryStructure.id == salary_structure_id).first():
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Salary Structure not found."}})

    employees = db.query(Employee).filter(Employee.status == EmployeeStatus.ACTIVE).order_by(Employee.first_name, Employee.last_name).all()
    results = []
    for employee in employees:
        eligibility = payroll_engine.check_eligibility(db, employee, period_start, period_end)
        schedule_summary = build_schedule_summary(employee.working_schedule)
        results.append(EligibleEmployee(
            employee=EmployeeMinimal.model_validate(employee),
            eligible=eligibility.eligible,
            reason=eligibility.reason,
            working_schedule_summary=f"{schedule_summary.hours_per_week}h/week" if schedule_summary else None,
            wage_monthly=eligibility.contract.wage_monthly if eligibility.contract else None,
        ))
    return results


@router.get("/payroll/payruns", response_model=List[PayrunResponse])
def list_payruns(
    db: Session = Depends(get_db),
    current_operator: User = Depends(get_current_payroll_operator),
    status: Optional[str] = None,
):
    query = db.query(Payrun)
    if status:
        query = query.filter(Payrun.status == status.upper())
    payruns = query.order_by(Payrun.period_start.desc()).all()
    return [_payrun_response(p) for p in payruns]


@router.post("/payroll/payruns", response_model=PayrunResponse)
def create_payrun(
    payload: PayrunCreate,
    db: Session = Depends(get_db),
    current_operator: User = Depends(get_current_payroll_operator),
):
    structure = db.query(SalaryStructure).filter(SalaryStructure.id == payload.salary_structure_id).first()
    if not structure:
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Salary Structure not found."}})
    if not structure.is_active:
        raise HTTPException(400, detail={"error": {"code": "STRUCTURE_INACTIVE", "message": "This Salary Structure is inactive."}})

    employees = db.query(Employee).filter(Employee.id.in_(payload.employee_ids)).all()
    found_ids = {e.id for e in employees}
    missing_ids = set(payload.employee_ids) - found_ids
    if missing_ids:
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": f"Employee(s) not found: {sorted(missing_ids)}"}})

    # Never trust frontend eligibility: re-validate every selection server-side.
    ineligible = []
    for employee in employees:
        eligibility = payroll_engine.check_eligibility(db, employee, payload.period_start, payload.period_end)
        if not eligibility.eligible:
            ineligible.append({"employee_id": employee.id, "name": f"{employee.first_name} {employee.last_name}", "reason": eligibility.reason})
    if ineligible:
        raise HTTPException(409, detail={"error": {"code": "INELIGIBLE_EMPLOYEES", "message": "One or more selected employees are not eligible for this payroll period.", "details": {"ineligible": ineligible}}})

    payrun = Payrun(
        reference=payroll_engine.generate_reference(db, payload.period_start),
        salary_structure_id=structure.id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        status=PayrunStatus.DRAFT,
        created_by_user_id=current_operator.id,
    )
    db.add(payrun)
    db.flush()

    for employee in employees:
        db.add(Payslip(
            payrun_id=payrun.id,
            employee_id=employee.id,
            salary_structure_id=structure.id,
            period_start=payload.period_start,
            period_end=payload.period_end,
            status=PayrunStatus.DRAFT,
        ))
    db.commit()
    db.refresh(payrun)
    return _payrun_response(payrun)


@router.get("/payroll/payruns/{payrun_id}", response_model=PayrunResponse)
def get_payrun(payrun_id: int, db: Session = Depends(get_db), current_operator: User = Depends(get_current_payroll_operator)):
    payrun = db.query(Payrun).filter(Payrun.id == payrun_id).first()
    if not payrun:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Payrun not found."}})
    return _payrun_response(payrun)


@router.post("/payroll/payruns/{payrun_id}/compute", response_model=PayrunResponse)
def compute_payrun(payrun_id: int, db: Session = Depends(get_db), current_operator: User = Depends(get_current_payroll_operator)):
    payrun = db.query(Payrun).filter(Payrun.id == payrun_id).first()
    if not payrun:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Payrun not found."}})
    try:
        payroll_engine.compute_payrun(db, payrun)
    except payroll_engine.InvalidTransitionError as exc:
        raise HTTPException(409, detail={"error": {"code": "INVALID_TRANSITION", "message": str(exc)}})
    return _payrun_response(payrun)


@router.post("/payroll/payruns/{payrun_id}/validate", response_model=PayrunResponse)
def validate_payrun(payrun_id: int, db: Session = Depends(get_db), current_operator: User = Depends(get_current_payroll_operator)):
    payrun = db.query(Payrun).filter(Payrun.id == payrun_id).first()
    if not payrun:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Payrun not found."}})
    try:
        payroll_engine.validate_payrun(db, payrun, current_operator)
    except payroll_engine.InvalidTransitionError as exc:
        raise HTTPException(409, detail={"error": {"code": "INVALID_TRANSITION", "message": str(exc)}})
    except payroll_engine.ValidationBlockedError as exc:
        blockers = []
        for payslip in payrun.payslips:
            if payslip.id in exc.blocking_payslip_ids:
                blockers.append(ValidationBlockerDetail(
                    payslip_id=payslip.id,
                    employee=EmployeeMinimal.model_validate(payslip.employee),
                    messages=[w.message for w in payslip.warnings if w.severity == WarningSeverity.BLOCKER],
                ).model_dump(mode="json"))
        raise HTTPException(409, detail={"error": {"code": "VALIDATION_BLOCKED", "message": str(exc), "details": {"blockers": blockers}}})
    return _payrun_response(payrun)


@router.post("/payroll/payruns/{payrun_id}/mark-paid", response_model=PayrunResponse)
def mark_payrun_paid(payrun_id: int, db: Session = Depends(get_db), current_operator: User = Depends(get_current_payroll_operator)):
    payrun = db.query(Payrun).filter(Payrun.id == payrun_id).first()
    if not payrun:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Payrun not found."}})
    try:
        payroll_engine.mark_payrun_paid(db, payrun, current_operator)
    except payroll_engine.InvalidTransitionError as exc:
        raise HTTPException(409, detail={"error": {"code": "INVALID_TRANSITION", "message": str(exc)}})
    return _payrun_response(payrun)


# ------------------------------------------------------------- Payslips ----

def _payslip_response(payslip: Payslip) -> PayslipResponse:
    return PayslipResponse(
        id=payslip.id,
        payrun_id=payslip.payrun_id,
        payrun_reference=payslip.payrun.reference,
        employee=EmployeeMinimal.model_validate(payslip.employee),
        contract_id=payslip.contract_id,
        salary_structure=SalaryStructureMinimal.model_validate(payslip.salary_structure),
        period_start=payslip.period_start,
        period_end=payslip.period_end,
        status=payslip.status,
        worked_days=payslip.worked_days,
        expected_work_days=payslip.expected_work_days,
        worked_hours=payslip.worked_hours,
        basic=payslip.basic,
        allowances=payslip.allowances,
        gross=payslip.gross,
        deductions=payslip.deductions,
        net=payslip.net,
        warning_count=payslip.warning_count,
        lines=[PayslipLineResponse.model_validate(l) for l in payslip.lines],
        warnings=[PayrollWarningResponse.model_validate(w) for w in payslip.warnings],
        computed_at=payslip.computed_at,
        validated_at=payslip.validated_at,
        paid_at=payslip.paid_at,
        created_at=payslip.created_at,
        updated_at=payslip.updated_at,
    )


def _payslip_summary(payslip: Payslip) -> PayslipSummaryResponse:
    return PayslipSummaryResponse(
        id=payslip.id,
        payrun_id=payslip.payrun_id,
        employee=EmployeeMinimal.model_validate(payslip.employee),
        salary_structure=SalaryStructureMinimal.model_validate(payslip.salary_structure),
        period_start=payslip.period_start,
        period_end=payslip.period_end,
        status=payslip.status,
        basic=payslip.basic,
        gross=payslip.gross,
        net=payslip.net,
        warning_count=payslip.warning_count,
    )


FINALIZED_STATUSES = {PayrunStatus.VALIDATED, PayrunStatus.PAID}


def _assert_payslip_access(current_user: User, payslip: Payslip) -> None:
    if current_user.role in HR_CAPABLE_ROLES:
        return
    if payslip.employee_id != current_user.employee_id:
        raise HTTPException(403, detail={"error": {"code": "ACCESS_DENIED", "message": "You don't have access to this payslip."}})
    if payslip.status not in FINALIZED_STATUSES:
        raise HTTPException(403, detail={"error": {"code": "NOT_AVAILABLE", "message": "Your payslip isn't available yet."}})


@router.get("/payroll/payslips", response_model=List[PayslipSummaryResponse])
def list_payslips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    payrun_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
):
    query = db.query(Payslip)
    if current_user.role not in HR_CAPABLE_ROLES:
        query = query.filter(Payslip.employee_id == current_user.employee_id, Payslip.status.in_(FINALIZED_STATUSES))
    elif employee_id is not None:
        query = query.filter(Payslip.employee_id == employee_id)
    if payrun_id is not None:
        query = query.filter(Payslip.payrun_id == payrun_id)
    if status:
        query = query.filter(Payslip.status == status.upper())
    payslips = query.order_by(Payslip.period_start.desc()).all()
    return [_payslip_summary(p) for p in payslips]


@router.get("/payroll/payslips/{payslip_id}", response_model=PayslipResponse)
def get_payslip(payslip_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    payslip = db.query(Payslip).filter(Payslip.id == payslip_id).first()
    if not payslip:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Payslip not found."}})
    _assert_payslip_access(current_user, payslip)
    return _payslip_response(payslip)


@router.get("/payroll/payslips/{payslip_id}/pdf")
def get_payslip_pdf(payslip_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    payslip = db.query(Payslip).filter(Payslip.id == payslip_id).first()
    if not payslip:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Payslip not found."}})
    _assert_payslip_access(current_user, payslip)
    pdf_bytes = payslip_pdf.generate_payslip_pdf(payslip)
    filename = f"{payslip.employee.employee_code or payslip.employee_id}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{filename}"'})
