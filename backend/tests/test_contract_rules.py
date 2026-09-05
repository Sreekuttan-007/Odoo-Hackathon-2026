from datetime import date
from decimal import Decimal
import pytest
from app.models.department import Department
from app.models.job_position import JobPosition
from app.models.employee import Employee
from app.models.contract import Contract
from app.services import contract_rules


def _setup_employee(db_session):
    dept = Department(name="Engineering")
    pos = JobPosition(title="Software Engineer")
    db_session.add_all([dept, pos])
    db_session.flush()
    emp = Employee(first_name="Test", last_name="Employee", work_email="test.employee@payloom.local")
    db_session.add(emp)
    db_session.flush()
    return emp, dept, pos


def _make_contract(db_session, emp, dept, pos, start, end, wage=Decimal("50000.00")):
    reference = contract_rules.generate_reference(db_session, start)
    contract = Contract(
        reference=reference, employee_id=emp.id, department_id=dept.id, job_position_id=pos.id,
        start_date=start, end_date=end, wage_monthly=wage, currency="INR",
    )
    db_session.add(contract)
    db_session.commit()
    return contract


def test_employee_can_have_historical_contracts(db_session):
    emp, dept, pos = _setup_employee(db_session)
    c1 = _make_contract(db_session, emp, dept, pos, date(2025, 1, 1), date(2025, 6, 30))
    c2 = _make_contract(db_session, emp, dept, pos, date(2025, 7, 1), None)
    contracts = db_session.query(Contract).filter(Contract.employee_id == emp.id).all()
    assert {c.id for c in contracts} == {c1.id, c2.id}


def test_valid_non_overlapping_contract_creation_allowed(db_session):
    emp, dept, pos = _setup_employee(db_session)
    _make_contract(db_session, emp, dept, pos, date(2025, 1, 1), date(2025, 6, 30))
    # Should not raise.
    contract_rules.assert_no_overlap(db_session, emp.id, date(2025, 7, 1), None)


def test_overlapping_applicable_contracts_rejected(db_session):
    emp, dept, pos = _setup_employee(db_session)
    _make_contract(db_session, emp, dept, pos, date(2025, 1, 1), date(2025, 12, 31))
    with pytest.raises(contract_rules.ContractOverlapError):
        contract_rules.assert_no_overlap(db_session, emp.id, date(2025, 7, 1), None)


def test_open_ended_contract_overlaps_any_future_contract(db_session):
    emp, dept, pos = _setup_employee(db_session)
    _make_contract(db_session, emp, dept, pos, date(2025, 1, 1), None)
    with pytest.raises(contract_rules.ContractOverlapError):
        contract_rules.assert_no_overlap(db_session, emp.id, date(2026, 1, 1), date(2026, 12, 31))


def test_update_excludes_self_from_overlap_check(db_session):
    emp, dept, pos = _setup_employee(db_session)
    contract = _make_contract(db_session, emp, dept, pos, date(2025, 1, 1), date(2025, 12, 31))
    # Should not raise: this only overlaps itself.
    contract_rules.assert_no_overlap(
        db_session, emp.id, date(2025, 2, 1), date(2025, 12, 31), exclude_contract_id=contract.id
    )


def test_derive_status_running_upcoming_expired():
    today = date(2026, 6, 15)
    assert contract_rules.derive_status(date(2026, 1, 1), None, today) == "RUNNING"
    assert contract_rules.derive_status(date(2026, 7, 1), None, today) == "UPCOMING"
    assert contract_rules.derive_status(date(2025, 1, 1), date(2025, 12, 31), today) == "EXPIRED"


def test_period_with_one_applicable_contract_returns_it(db_session):
    emp, dept, pos = _setup_employee(db_session)
    contract = _make_contract(db_session, emp, dept, pos, date(2026, 1, 1), None)
    result = contract_rules.get_applicable_contract(db_session, emp.id, date(2026, 3, 1), date(2026, 3, 31))
    assert result.id == contract.id


def test_period_with_no_contract_reports_missing(db_session):
    emp, dept, pos = _setup_employee(db_session)
    with pytest.raises(contract_rules.NoApplicableContractError):
        contract_rules.get_applicable_contract(db_session, emp.id, date(2026, 3, 1), date(2026, 3, 31))


def test_conflict_never_silently_resolved(db_session):
    # Bypass assert_no_overlap to simulate legacy/bad data with two contracts
    # applicable to the same period, and confirm the service reports a
    # conflict instead of silently picking one.
    emp, dept, pos = _setup_employee(db_session)
    _make_contract(db_session, emp, dept, pos, date(2026, 1, 1), date(2026, 6, 30))
    contract = Contract(
        reference="CON/2026/9999", employee_id=emp.id, department_id=dept.id, job_position_id=pos.id,
        start_date=date(2026, 4, 1), end_date=None, wage_monthly=Decimal("60000.00"), currency="INR",
    )
    db_session.add(contract)
    db_session.commit()

    with pytest.raises(contract_rules.ConflictingContractsError):
        contract_rules.get_applicable_contract(db_session, emp.id, date(2026, 5, 1), date(2026, 5, 31))


def test_wage_preserves_decimal_accuracy(db_session):
    emp, dept, pos = _setup_employee(db_session)
    contract = _make_contract(db_session, emp, dept, pos, date(2026, 1, 1), None, wage=Decimal("85000.33"))
    db_session.refresh(contract)
    assert contract.wage_monthly == Decimal("85000.33")


def test_reference_generation_is_sequential_per_year(db_session):
    emp, dept, pos = _setup_employee(db_session)
    c1 = _make_contract(db_session, emp, dept, pos, date(2025, 1, 1), date(2025, 6, 30))
    assert c1.reference == "CON/2025/0001"
