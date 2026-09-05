from datetime import date, time
from decimal import Decimal
from tests.conftest import auth_headers, _make_user
from app.models.user import Role
from app.models.working_schedule import WorkingSchedule, WorkingScheduleLine, ScheduleStatus, DayOfWeek


def _payroll_manager_token(client, db_session):
    email = _make_user(db_session, Role.HR_PAYROLL_MANAGER, "payroll-mgr@payloom.local")
    res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    return res.json()["access_token"]


def _payroll_user_token(client, db_session):
    email = _make_user(db_session, Role.HR_PAYROLL_USER, "payroll-user@payloom.local")
    res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    return res.json()["access_token"]


def _give_schedule(db_session, employee_id):
    schedule = WorkingSchedule(name="40 Hours / Week", status=ScheduleStatus.ACTIVE)
    db_session.add(schedule)
    db_session.flush()
    for day in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]:
        db_session.add(WorkingScheduleLine(working_schedule_id=schedule.id, day_of_week=day, start_time=time(9, 0), end_time=time(18, 0), break_minutes=60))
    db_session.commit()
    from app.models.employee import Employee
    employee = db_session.query(Employee).filter(Employee.id == employee_id).first()
    employee.working_schedule_id = schedule.id
    db_session.commit()
    return schedule.id


def _create_structure_with_rules(client, mgr_token):
    structure = client.post("/api/payroll/structures", json={"name": "Regular Salary", "code": "REG"}, headers=auth_headers(mgr_token)).json()
    sid = structure["id"]
    rules = [
        {"name": "Basic Salary", "code": "BASIC", "category": "BASIC", "sequence": 1, "computation_method": "PERCENTAGE", "percentage": 50, "percentage_base": "CONTRACT_WAGE"},
        {"name": "Gross Salary", "code": "GROSS", "category": "GROSS", "sequence": 60, "computation_method": "FORMULA", "formula_expression": 'rules["BASIC"]'},
        {"name": "Net Salary", "code": "NET", "category": "NET", "sequence": 100, "computation_method": "FORMULA", "formula_expression": 'rules["GROSS"]'},
    ]
    for rule in rules:
        res = client.post(f"/api/payroll/rules?salary_structure_id={sid}", json=rule, headers=auth_headers(mgr_token))
        assert res.status_code == 200, res.text
    return sid


def _bootstrap_employee_with_contract(client, hr_token, wage=50000, first="Aarav", last="Mehta"):
    emp = client.post("/api/employees", json={"first_name": first, "last_name": last}, headers=auth_headers(hr_token)).json()
    assert "id" in emp, emp
    dept = client.post("/api/departments", json={"name": f"Engineering-{first}-{last}"}, headers=auth_headers(hr_token)).json()
    pos = client.post("/api/job-positions", json={"title": f"Software Engineer-{first}-{last}"}, headers=auth_headers(hr_token)).json()
    res = client.post("/api/contracts", json={
        "employee_id": emp["id"], "department_id": dept["id"], "job_position_id": pos["id"],
        "start_date": "2026-01-01", "wage_monthly": wage,
    }, headers=auth_headers(hr_token))
    assert res.status_code == 200, res.text
    return emp


class TestWizard:
    def test_continue_step_does_not_create_payrun(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, hr_token)
        _give_schedule(db_session, emp["id"])

        client.get(f"/api/payroll/payruns/eligible-employees?salary_structure_id={sid}&period_start=2026-02-01&period_end=2026-02-28", headers=auth_headers(mgr_token))
        client.get(f"/api/payroll/payruns/eligible-employees?salary_structure_id={sid}&period_start=2026-02-01&period_end=2026-02-28", headers=auth_headers(mgr_token))

        res = client.get("/api/payroll/payruns", headers=auth_headers(mgr_token))
        assert res.status_code == 200
        assert res.json() == []

    def test_eligible_employees_shows_wage(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, hr_token, wage=60000)
        _give_schedule(db_session, emp["id"])

        res = client.get(f"/api/payroll/payruns/eligible-employees?salary_structure_id={sid}&period_start=2026-02-01&period_end=2026-02-28", headers=auth_headers(mgr_token))
        row = next(r for r in res.json() if r["employee"]["id"] == emp["id"])
        assert row["eligible"] is True
        assert row["wage_monthly"] == "60000.00"

    def test_create_payrun_only_includes_selected_employees(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        emp1 = _bootstrap_employee_with_contract(client, hr_token, first="Aarav", last="Mehta")
        emp2 = _bootstrap_employee_with_contract(client, hr_token, first="Sara", last="Khan")
        _give_schedule(db_session, emp1["id"])
        _give_schedule(db_session, emp2["id"])

        res = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-02-01", "period_end": "2026-02-28", "employee_ids": [emp1["id"]],
        }, headers=auth_headers(mgr_token))
        assert res.status_code == 200, res.text
        payrun = res.json()
        assert payrun["employee_count"] == 1
        assert payrun["status"] == "DRAFT"

        payslips = client.get(f"/api/payroll/payslips?payrun_id={payrun['id']}", headers=auth_headers(mgr_token)).json()
        assert len(payslips) == 1
        assert payslips[0]["employee"]["id"] == emp1["id"]

    def test_zero_employees_selected_rejected(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        res = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-02-01", "period_end": "2026-02-28", "employee_ids": [],
        }, headers=auth_headers(mgr_token))
        assert res.status_code == 422

    def test_ineligible_employee_rejected_server_side(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        # employee with NO contract
        emp = client.post("/api/employees", json={"first_name": "No", "last_name": "Contract"}, headers=auth_headers(hr_token)).json()

        res = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-02-01", "period_end": "2026-02-28", "employee_ids": [emp["id"]],
        }, headers=auth_headers(mgr_token))
        assert res.status_code == 409
        assert res.json()["detail"]["error"]["code"] == "INELIGIBLE_EMPLOYEES"

    def test_invalid_period_rejected(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, hr_token)
        res = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-02-28", "period_end": "2026-02-01", "employee_ids": [emp["id"]],
        }, headers=auth_headers(mgr_token))
        assert res.status_code == 422


class TestStateMachine:
    def _create_and_get_payrun(self, client, hr_token, db_session, wage=50000):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, hr_token, wage=wage)
        _give_schedule(db_session, emp["id"])
        payrun = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-02-01", "period_end": "2026-02-28", "employee_ids": [emp["id"]],
        }, headers=auth_headers(mgr_token)).json()
        return mgr_token, payrun

    def test_full_happy_path(self, client, hr_token, db_session):
        mgr_token, payrun = self._create_and_get_payrun(client, hr_token, db_session)
        pid = payrun["id"]

        res = client.post(f"/api/payroll/payruns/{pid}/compute", headers=auth_headers(mgr_token))
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "COMPUTED"
        assert Decimal(res.json()["total_net"]) == Decimal("25000.00")  # BASIC = 50% of 50000; GROSS=NET=BASIC in the test structure

        res = client.post(f"/api/payroll/payruns/{pid}/validate", headers=auth_headers(mgr_token))
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "VALIDATED"

        res = client.post(f"/api/payroll/payruns/{pid}/mark-paid", headers=auth_headers(mgr_token))
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "PAID"

    def test_validate_before_compute_rejected(self, client, hr_token, db_session):
        mgr_token, payrun = self._create_and_get_payrun(client, hr_token, db_session)
        res = client.post(f"/api/payroll/payruns/{payrun['id']}/validate", headers=auth_headers(mgr_token))
        assert res.status_code == 409
        assert res.json()["detail"]["error"]["code"] == "INVALID_TRANSITION"

    def test_mark_paid_before_validate_rejected(self, client, hr_token, db_session):
        mgr_token, payrun = self._create_and_get_payrun(client, hr_token, db_session)
        client.post(f"/api/payroll/payruns/{payrun['id']}/compute", headers=auth_headers(mgr_token))
        res = client.post(f"/api/payroll/payruns/{payrun['id']}/mark-paid", headers=auth_headers(mgr_token))
        assert res.status_code == 409
        assert res.json()["detail"]["error"]["code"] == "INVALID_TRANSITION"

    def test_compute_after_paid_rejected(self, client, hr_token, db_session):
        mgr_token, payrun = self._create_and_get_payrun(client, hr_token, db_session)
        pid = payrun["id"]
        client.post(f"/api/payroll/payruns/{pid}/compute", headers=auth_headers(mgr_token))
        client.post(f"/api/payroll/payruns/{pid}/validate", headers=auth_headers(mgr_token))
        client.post(f"/api/payroll/payruns/{pid}/mark-paid", headers=auth_headers(mgr_token))
        res = client.post(f"/api/payroll/payruns/{pid}/compute", headers=auth_headers(mgr_token))
        assert res.status_code == 409
        assert res.json()["detail"]["error"]["code"] == "INVALID_TRANSITION"

    def test_recompute_allowed_while_computed(self, client, hr_token, db_session):
        mgr_token, payrun = self._create_and_get_payrun(client, hr_token, db_session)
        pid = payrun["id"]
        client.post(f"/api/payroll/payruns/{pid}/compute", headers=auth_headers(mgr_token))
        res = client.post(f"/api/payroll/payruns/{pid}/compute", headers=auth_headers(mgr_token))
        assert res.status_code == 200

    def test_missing_contract_blocks_validation(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, hr_token)
        _give_schedule(db_session, emp["id"])
        payrun = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-02-01", "period_end": "2026-02-28", "employee_ids": [emp["id"]],
        }, headers=auth_headers(mgr_token)).json()

        # Delete the contract's applicability by moving the period outside contract validity
        # (simulate a blocker appearing between creation and validate by using a structure with a broken rule instead)
        client.post(f"/api/payroll/payruns/{payrun['id']}/compute", headers=auth_headers(mgr_token))

        # Break the rule after compute so recompute-on-validate discovers a blocker.
        rules = client.get(f"/api/payroll/rules?salary_structure_id={sid}", headers=auth_headers(mgr_token)).json()
        gross_rule = next(r for r in rules if r["code"] == "GROSS")
        client.patch(f"/api/payroll/rules/{gross_rule['id']}", json={"formula_expression": 'rules["NONEXISTENT"]'}, headers=auth_headers(mgr_token))

        res = client.post(f"/api/payroll/payruns/{payrun['id']}/validate", headers=auth_headers(mgr_token))
        assert res.status_code == 409
        assert res.json()["detail"]["error"]["code"] == "VALIDATION_BLOCKED"


class TestHistoricalIntegrity:
    def test_paid_payslip_unaffected_by_later_rule_edit(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, hr_token, wage=50000)
        _give_schedule(db_session, emp["id"])
        payrun = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-02-01", "period_end": "2026-02-28", "employee_ids": [emp["id"]],
        }, headers=auth_headers(mgr_token)).json()
        pid = payrun["id"]

        client.post(f"/api/payroll/payruns/{pid}/compute", headers=auth_headers(mgr_token))
        client.post(f"/api/payroll/payruns/{pid}/validate", headers=auth_headers(mgr_token))
        client.post(f"/api/payroll/payruns/{pid}/mark-paid", headers=auth_headers(mgr_token))

        payslip_before = client.get(f"/api/payroll/payslips?payrun_id={pid}", headers=auth_headers(mgr_token)).json()[0]
        assert payslip_before["net"] == "25000.00"

        rules = client.get(f"/api/payroll/rules?salary_structure_id={sid}", headers=auth_headers(mgr_token)).json()
        basic_rule = next(r for r in rules if r["code"] == "BASIC")
        client.patch(f"/api/payroll/rules/{basic_rule['id']}", json={"percentage": 90}, headers=auth_headers(mgr_token))

        payslip_after = client.get(f"/api/payroll/payslips/{payslip_before['id']}", headers=auth_headers(mgr_token)).json()
        assert payslip_after["net"] == "25000.00"
        assert payslip_after["lines"][0]["amount"] == "25000.00"


class TestRBACAndPrivacy:
    def test_hr_manager_cannot_create_payrun(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, hr_token)
        res = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-02-01", "period_end": "2026-02-28", "employee_ids": [emp["id"]],
        }, headers=auth_headers(hr_token))
        assert res.status_code == 403

    def test_payroll_user_cannot_edit_salary_rules(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        user_token = _payroll_user_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        res = client.post(f"/api/payroll/rules?salary_structure_id={sid}", json={
            "name": "Extra", "code": "EXTRA", "category": "ALLOWANCE", "sequence": 5, "computation_method": "FIXED", "fixed_amount": 100,
        }, headers=auth_headers(user_token))
        assert res.status_code == 403

    def test_payroll_user_can_create_payrun(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        user_token = _payroll_user_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, hr_token)
        _give_schedule(db_session, emp["id"])
        res = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-02-01", "period_end": "2026-02-28", "employee_ids": [emp["id"]],
        }, headers=auth_headers(user_token))
        assert res.status_code == 200, res.text

    def test_employee_cannot_mark_payrun_paid(self, client, employee_token, db_session):
        res = client.post("/api/payroll/payruns/1/mark-paid", headers=auth_headers(employee_token))
        assert res.status_code == 403

    def test_employee_can_view_own_finalized_payslip_not_others(self, client, employee_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)

        from app.models.user import User
        self_user = db_session.query(User).filter(User.work_email == "employee-test@payloom.local").first()
        _give_schedule(db_session, self_user.employee_id)

        dept = client.post("/api/departments", json={"name": "Engineering"}, headers=auth_headers(mgr_token)).json()
        pos = client.post("/api/job-positions", json={"title": "Software Engineer"}, headers=auth_headers(mgr_token)).json()
        client.post("/api/contracts", json={
            "employee_id": self_user.employee_id, "department_id": dept["id"], "job_position_id": pos["id"],
            "start_date": "2026-01-01", "wage_monthly": 40000,
        }, headers=auth_headers(mgr_token))

        other_emp = _bootstrap_employee_with_contract(client, mgr_token, first="Other", last="Person")
        _give_schedule(db_session, other_emp["id"])

        payrun = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-02-01", "period_end": "2026-02-28",
            "employee_ids": [self_user.employee_id, other_emp["id"]],
        }, headers=auth_headers(mgr_token)).json()
        pid = payrun["id"]

        # DRAFT/COMPUTED payslips aren't "available" to the employee yet.
        payslips = client.get(f"/api/payroll/payslips?payrun_id={pid}", headers=auth_headers(mgr_token)).json()
        self_payslip = next(p for p in payslips if p["employee"]["id"] == self_user.employee_id)
        other_payslip = next(p for p in payslips if p["employee"]["id"] == other_emp["id"])

        res = client.get(f"/api/payroll/payslips/{self_payslip['id']}", headers=auth_headers(employee_token))
        assert res.status_code == 403  # not finalized yet

        client.post(f"/api/payroll/payruns/{pid}/compute", headers=auth_headers(mgr_token))
        client.post(f"/api/payroll/payruns/{pid}/validate", headers=auth_headers(mgr_token))

        res = client.get(f"/api/payroll/payslips/{self_payslip['id']}", headers=auth_headers(employee_token))
        assert res.status_code == 200

        res = client.get(f"/api/payroll/payslips/{other_payslip['id']}", headers=auth_headers(employee_token))
        assert res.status_code == 403

        res = client.get("/api/payroll/payslips", headers=auth_headers(employee_token))
        assert res.status_code == 200
        assert all(p["employee"]["id"] == self_user.employee_id for p in res.json())


class TestPdf:
    def test_pdf_generated_for_finalized_payslip(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_structure_with_rules(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, hr_token, wage=50000)
        _give_schedule(db_session, emp["id"])
        payrun = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-02-01", "period_end": "2026-02-28", "employee_ids": [emp["id"]],
        }, headers=auth_headers(mgr_token)).json()
        pid = payrun["id"]
        client.post(f"/api/payroll/payruns/{pid}/compute", headers=auth_headers(mgr_token))
        client.post(f"/api/payroll/payruns/{pid}/validate", headers=auth_headers(mgr_token))

        payslip = client.get(f"/api/payroll/payslips?payrun_id={pid}", headers=auth_headers(mgr_token)).json()[0]
        res = client.get(f"/api/payroll/payslips/{payslip['id']}/pdf", headers=auth_headers(mgr_token))
        assert res.status_code == 200
        assert res.content[:4] == b"%PDF"
        assert res.headers["content-type"] == "application/pdf"
