from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.db.database import get_db
from app.models.contract import Contract
from app.models.employee import Employee
from app.models.department import Department
from app.models.job_position import JobPosition
from app.models.working_schedule import WorkingSchedule
from app.models.user import User
from app.schemas.contract import ContractResponse, ContractCreate, ContractUpdate
from app.schemas.employee import EmployeeMinimal
from app.schemas.department import DepartmentResponse
from app.schemas.job_position import JobPositionResponse
from app.api.deps import get_current_user, get_current_hr, HR_CAPABLE_ROLES
from app.services import contract_rules
from app.services.schedule_calculator import build_schedule_summary

router = APIRouter()


def _to_response(contract: Contract) -> ContractResponse:
    return ContractResponse(
        id=contract.id,
        reference=contract.reference,
        status=contract_rules.derive_status(contract.start_date, contract.end_date),
        employee=EmployeeMinimal.model_validate(contract.employee),
        department=DepartmentResponse.model_validate(contract.department),
        job_position=JobPositionResponse.model_validate(contract.job_position),
        working_schedule=build_schedule_summary(contract.working_schedule),
        department_id=contract.department_id,
        job_position_id=contract.job_position_id,
        working_schedule_id=contract.working_schedule_id,
        start_date=contract.start_date,
        end_date=contract.end_date,
        wage_monthly=contract.wage_monthly,
        currency=contract.currency,
        salary_structure_note=contract.salary_structure_note,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


def _assert_relations_exist(db: Session, employee_id: Optional[int], department_id: int, job_position_id: int, working_schedule_id: Optional[int]) -> None:
    if employee_id is not None and not db.query(Employee).filter(Employee.id == employee_id).first():
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Employee not found."}})
    if not db.query(Department).filter(Department.id == department_id).first():
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Department not found."}})
    if not db.query(JobPosition).filter(JobPosition.id == job_position_id).first():
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Job position not found."}})
    if working_schedule_id is not None and not db.query(WorkingSchedule).filter(WorkingSchedule.id == working_schedule_id).first():
        raise HTTPException(400, detail={"error": {"code": "NOT_FOUND", "message": "Working schedule not found."}})


@router.get("/contracts", response_model=List[ContractResponse])
def list_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    query = db.query(Contract)
    if current_user.role not in HR_CAPABLE_ROLES:
        query = query.filter(Contract.employee_id == current_user.employee_id)
    if employee_id is not None:
        if current_user.role not in HR_CAPABLE_ROLES and employee_id != current_user.employee_id:
            raise HTTPException(403, detail={"error": {"code": "ACCESS_DENIED", "message": "You don't have access to these contracts."}})
        query = query.filter(Contract.employee_id == employee_id)
    if search:
        query = query.filter(Contract.reference.ilike(f"%{search}%"))

    contracts = query.order_by(Contract.start_date.desc()).all()
    responses = [_to_response(c) for c in contracts]
    if status:
        responses = [r for r in responses if r.status == status.upper()]
    return responses


@router.get("/contracts/applicable", response_model=ContractResponse)
def get_applicable_contract(
    employee_id: int,
    period_start: date,
    period_end: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exposes getApplicableContract() for later Payroll integration and demo
    purposes. Returns the single contract applicable to the given period, or
    a clear MISSING_CONTRACT / CONTRACT_CONFLICT error."""
    if current_user.role not in HR_CAPABLE_ROLES and employee_id != current_user.employee_id:
        raise HTTPException(403, detail={"error": {"code": "ACCESS_DENIED", "message": "You don't have access to this contract."}})
    try:
        contract = contract_rules.get_applicable_contract(db, employee_id, period_start, period_end)
    except contract_rules.NoApplicableContractError:
        raise HTTPException(404, detail={"error": {"code": "MISSING_CONTRACT", "message": "No applicable contract found for this employee for this period."}})
    except contract_rules.ConflictingContractsError as exc:
        raise HTTPException(409, detail={
            "error": {
                "code": "CONTRACT_CONFLICT",
                "message": str(exc),
                "details": {"conflicting_contract_ids": [c.id for c in exc.contracts]},
            }
        })
    return _to_response(contract)


@router.get("/contracts/{contract_id}", response_model=ContractResponse)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Contract).filter(Contract.id == contract_id)
    if current_user.role not in HR_CAPABLE_ROLES:
        query = query.filter(Contract.employee_id == current_user.employee_id)
    contract = query.first()
    if not contract:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Contract not found."}})
    return _to_response(contract)


@router.post("/contracts", response_model=ContractResponse)
def create_contract(
    payload: ContractCreate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    _assert_relations_exist(db, payload.employee_id, payload.department_id, payload.job_position_id, payload.working_schedule_id)

    try:
        contract_rules.assert_no_overlap(db, payload.employee_id, payload.start_date, payload.end_date)
    except contract_rules.ContractOverlapError as exc:
        raise HTTPException(409, detail={
            "error": {
                "code": "CONTRACT_OVERLAP",
                "message": str(exc),
                "details": {"conflicting_contract_id": exc.conflicting_contract.id, "conflicting_contract_reference": exc.conflicting_contract.reference},
            }
        })

    reference = contract_rules.generate_reference(db, payload.start_date)

    contract = Contract(
        reference=reference,
        employee_id=payload.employee_id,
        department_id=payload.department_id,
        job_position_id=payload.job_position_id,
        working_schedule_id=payload.working_schedule_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        wage_monthly=payload.wage_monthly,
        currency=payload.currency,
        salary_structure_note=payload.salary_structure_note,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return _to_response(contract)


@router.patch("/contracts/{contract_id}", response_model=ContractResponse)
def update_contract(
    contract_id: int,
    payload: ContractUpdate,
    db: Session = Depends(get_db),
    current_hr: User = Depends(get_current_hr),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Contract not found."}})

    data = payload.model_dump(exclude_unset=True)

    new_department_id = data.get("department_id", contract.department_id)
    new_job_position_id = data.get("job_position_id", contract.job_position_id)
    new_working_schedule_id = data.get("working_schedule_id", contract.working_schedule_id)
    new_start_date = data.get("start_date", contract.start_date)
    new_end_date = data.get("end_date", contract.end_date)

    if new_end_date is not None and new_end_date < new_start_date:
        raise HTTPException(400, detail={"error": {"code": "INVALID_DATES", "message": "end_date must be on or after start_date."}})

    _assert_relations_exist(db, None, new_department_id, new_job_position_id, new_working_schedule_id)

    try:
        contract_rules.assert_no_overlap(
            db, contract.employee_id, new_start_date, new_end_date, exclude_contract_id=contract.id
        )
    except contract_rules.ContractOverlapError as exc:
        raise HTTPException(409, detail={
            "error": {
                "code": "CONTRACT_OVERLAP",
                "message": str(exc),
                "details": {"conflicting_contract_id": exc.conflicting_contract.id, "conflicting_contract_reference": exc.conflicting_contract.reference},
            }
        })

    for field, value in data.items():
        setattr(contract, field, value)

    db.commit()
    db.refresh(contract)
    return _to_response(contract)
