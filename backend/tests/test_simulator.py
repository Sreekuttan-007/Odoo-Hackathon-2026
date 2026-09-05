from decimal import Decimal
from tests.conftest import auth_headers, _make_user
from tests.test_payroll_api import _payroll_manager_token, _bootstrap_employee_with_contract
from app.models.user import Role
from app.models.payroll import SalaryStructure, SalaryRule, Payslip, PayrollWarning
from app.models.contract import Contract
from app.models.attendance import Attendance
from app.models.time_off import TimeOffAllocation, TimeOffRequest


def _create_full_structure(client, mgr_token, name="Simulator Test Structure"):
    structure = client.post("/api/payroll/structures", json={"name": name}, headers=auth_headers(mgr_token)).json()
    sid = structure["id"]
    rules = [
        {"name": "Basic Salary", "code": "BASIC", "category": "BASIC", "sequence": 1, "computation_method": "PERCENTAGE", "percentage": 50, "percentage_base": "CONTRACT_WAGE"},
        {"name": "House Rent Allowance", "code": "HRA", "category": "ALLOWANCE", "sequence": 10, "computation_method": "PERCENTAGE", "percentage": 20, "percentage_base": "BASIC"},
        {"name": "Standard Allowance", "code": "ALLOWANCE", "category": "ALLOWANCE", "sequence": 20, "computation_method": "FIXED", "fixed_amount": 2000},
        {"name": "Gross Salary", "code": "GROSS", "category": "GROSS", "sequence": 60, "computation_method": "FORMULA", "formula_expression": 'rules["BASIC"] + rules["HRA"] + rules["ALLOWANCE"]'},
        {"name": "Provident Fund", "code": "PF", "category": "DEDUCTION", "sequence": 80, "computation_method": "PERCENTAGE", "percentage": 10, "percentage_base": "BASIC"},
        {"name": "Net Salary", "code": "NET", "category": "NET", "sequence": 100, "computation_method": "FORMULA", "formula_expression": 'rules["GROSS"] - rules["PF"]'},
    ]
    ids = {}
    for rule in rules:
        res = client.post(f"/api/payroll/rules?salary_structure_id={sid}", json=rule, headers=auth_headers(mgr_token))
        assert res.status_code == 200, res.text
        ids[rule["code"]] = res.json()["id"]
    return sid, ids


def _run(client, token, **kwargs):
    payload = {
        "period_start": "2026-03-01", "period_end": "2026-03-31",
        "rule_overrides": [],
    }
    payload.update(kwargs)
    return client.post("/api/payroll/simulator/run", json=payload, headers=auth_headers(token))


class TestSimulatorBaseline:
    def test_zero_overrides_matches_current_calculation(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid, rule_ids = _create_full_structure(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, mgr_token, wage=50000)

        res = _run(client, mgr_token, salary_structure_id=sid, employee_ids=[emp["id"]])
        assert res.status_code == 200, res.text
        body = res.json()
        result = body["employees"][0]
        assert result["current"] == result["simulated"]
        assert result["delta_net"] == "0.00"
        assert result["status"] == "UNCHANGED"
        assert result["current"]["net"] == "29500.00"  # canonical Phase 5 worked example


class TestSimulatorOverrides:
    def test_percentage_override_recalculates_downstream(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid, rule_ids = _create_full_structure(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, mgr_token, wage=50000)

        res = _run(
            client, mgr_token, salary_structure_id=sid, employee_ids=[emp["id"]],
            rule_overrides=[{"rule_id": rule_ids["HRA"], "percentage": "25.00"}],
        )
        assert res.status_code == 200, res.text
        result = res.json()["employees"][0]
        components = {c["rule_code"]: c for c in result["components"]}

        assert components["HRA"]["current_amount"] == "5000.00"
        assert components["HRA"]["simulated_amount"] == "6250.00"
        assert components["HRA"]["changed"] is True

        # Downstream GROSS/NET recalculated through the real formula, not a
        # hand-added delta.
        assert components["GROSS"]["current_amount"] == "32000.00"
        assert components["GROSS"]["simulated_amount"] == "33250.00"
        assert components["NET"]["current_amount"] == "29500.00"
        assert components["NET"]["simulated_amount"] == "30750.00"
        assert result["delta_net"] == "1250.00"

        # Upstream/unrelated rules (BASIC, PF both depend on BASIC, not HRA)
        # must NOT have changed.
        assert components["BASIC"]["changed"] is False
        assert components["PF"]["changed"] is False

    def test_fixed_rule_override_recalculates_downstream(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid, rule_ids = _create_full_structure(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, mgr_token, wage=50000)

        res = _run(
            client, mgr_token, salary_structure_id=sid, employee_ids=[emp["id"]],
            rule_overrides=[{"rule_id": rule_ids["ALLOWANCE"], "fixed_amount": "3000.00"}],
        )
        result = res.json()["employees"][0]
        components = {c["rule_code"]: c for c in result["components"]}
        assert components["ALLOWANCE"]["simulated_amount"] == "3000.00"
        assert components["GROSS"]["simulated_amount"] == "33000.00"
        assert components["NET"]["simulated_amount"] == "30500.00"

    def test_formula_override(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid, rule_ids = _create_full_structure(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, mgr_token, wage=50000)

        res = _run(
            client, mgr_token, salary_structure_id=sid, employee_ids=[emp["id"]],
            rule_overrides=[{"rule_id": rule_ids["GROSS"], "formula_expression": 'rules["BASIC"] + rules["HRA"]'}],
        )
        assert res.status_code == 200, res.text
        result = res.json()["employees"][0]
        components = {c["rule_code"]: c for c in result["components"]}
        # ALLOWANCE (2000) no longer folded into GROSS under the override.
        assert components["GROSS"]["simulated_amount"] == "30000.00"
        assert components["NET"]["simulated_amount"] == "27500.00"

    def test_multiple_simultaneous_overrides(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid, rule_ids = _create_full_structure(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, mgr_token, wage=50000)

        res = _run(
            client, mgr_token, salary_structure_id=sid, employee_ids=[emp["id"]],
            rule_overrides=[
                {"rule_id": rule_ids["HRA"], "percentage": "25.00"},
                {"rule_id": rule_ids["PF"], "percentage": "12.00"},
            ],
        )
        result = res.json()["employees"][0]
        components = {c["rule_code"]: c for c in result["components"]}
        assert components["HRA"]["simulated_amount"] == "6250.00"
        assert components["PF"]["simulated_amount"] == "3000.00"
        # GROSS 33250, PF 3000 -> NET 30250
        assert components["NET"]["simulated_amount"] == "30250.00"

    def test_invalid_override_rule_not_in_structure_rejected(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid, _ = _create_full_structure(client, mgr_token)
        sid2, other_ids = _create_full_structure(client, mgr_token, name="Other Structure")
        emp = _bootstrap_employee_with_contract(client, mgr_token, wage=50000)

        res = _run(
            client, mgr_token, salary_structure_id=sid, employee_ids=[emp["id"]],
            rule_overrides=[{"rule_id": other_ids["HRA"], "percentage": "25.00"}],
        )
        assert res.status_code == 400
        assert res.json()["detail"]["error"]["code"] == "INVALID_OVERRIDE"


class TestSimulatorScopeAndExclusions:
    def test_missing_contract_excluded_not_fabricated(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid, _ = _create_full_structure(client, mgr_token)
        emp = client.post("/api/employees", json={"first_name": "No", "last_name": "Contract"}, headers=auth_headers(hr_token)).json()

        res = _run(client, mgr_token, salary_structure_id=sid, employee_ids=[emp["id"]])
        assert res.status_code == 200
        body = res.json()
        result = body["employees"][0]
        assert result["excluded"] is True
        assert result["exclusion_code"] == "MISSING_CONTRACT"
        assert result["current"] is None and result["simulated"] is None
        assert body["employees_simulated"] == 0
        assert body["employees_excluded"] == 1

    def test_explicit_period_picks_correct_applicable_contract(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid, rule_ids = _create_full_structure(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, mgr_token, wage=40000)
        existing_contract = client.get(f"/api/contracts?employee_id={emp['id']}", headers=auth_headers(mgr_token)).json()[0]
        dept = existing_contract["department"]["id"]
        pos = existing_contract["job_position"]["id"]
        # Close the first (open-ended) contract so a second, later one
        # with a different wage doesn't overlap it.
        patch_res = client.patch(f"/api/contracts/{existing_contract['id']}", json={"end_date": "2026-05-31"}, headers=auth_headers(mgr_token))
        assert patch_res.status_code == 200, patch_res.text
        create_res = client.post("/api/contracts", json={
            "employee_id": emp["id"], "department_id": dept, "job_position_id": pos,
            "start_date": "2026-06-01", "wage_monthly": 80000,
        }, headers=auth_headers(mgr_token))
        assert create_res.status_code == 200, create_res.text

        res_march = _run(client, mgr_token, salary_structure_id=sid, employee_ids=[emp["id"]], period_start="2026-03-01", period_end="2026-03-31")
        res_june = _run(client, mgr_token, salary_structure_id=sid, employee_ids=[emp["id"]], period_start="2026-06-01", period_end="2026-06-30")
        assert res_march.json()["employees"][0]["current"]["basic"] == "20000.00"  # 50% of 40000
        assert res_june.json()["employees"][0]["current"]["basic"] == "40000.00"  # 50% of 80000

    def test_multi_employee_aggregate_equals_sum_of_employees(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid, rule_ids = _create_full_structure(client, mgr_token)
        emp1 = _bootstrap_employee_with_contract(client, mgr_token, wage=50000, first="One", last="Person")
        emp2 = _bootstrap_employee_with_contract(client, mgr_token, wage=90000, first="Two", last="Person")

        res = _run(
            client, mgr_token, salary_structure_id=sid, employee_ids=[emp1["id"], emp2["id"]],
            rule_overrides=[{"rule_id": rule_ids["HRA"], "percentage": "25.00"}],
        )
        body = res.json()
        assert body["employees_simulated"] == 2
        expected_delta_net = sum(Decimal(e["delta_net"]) for e in body["employees"])
        assert Decimal(body["aggregate"]["delta_net"]) == expected_delta_net
        expected_gross = sum(Decimal(e["simulated"]["gross"]) for e in body["employees"])
        assert Decimal(body["aggregate"]["simulated_total_gross"]) == expected_gross


class TestSimulatorRBAC:
    def test_hr_manager_forbidden(self, client, hr_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid, _ = _create_full_structure(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, mgr_token)
        res = _run(client, hr_token, salary_structure_id=sid, employee_ids=[emp["id"]])
        assert res.status_code == 403

    def test_employee_forbidden(self, client, employee_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid, _ = _create_full_structure(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, mgr_token)
        res = _run(client, employee_token, salary_structure_id=sid, employee_ids=[emp["id"]])
        assert res.status_code == 403

    def test_unauthenticated_rejected(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid, _ = _create_full_structure(client, mgr_token)
        res = client.post("/api/payroll/simulator/run", json={
            "salary_structure_id": sid, "period_start": "2026-03-01", "period_end": "2026-03-31",
            "employee_ids": [1], "rule_overrides": [],
        })
        assert res.status_code == 401


class TestSimulatorNonMutation:
    def test_database_state_unchanged_by_simulation(self, client, db_session):
        """The mandatory invariant test: simulate a nontrivial scenario
        (multiple overrides, multiple employees), then prove every
        payroll-relevant table is byte-identical before and after."""
        mgr_token = _payroll_manager_token(client, db_session)
        sid, rule_ids = _create_full_structure(client, mgr_token)
        emp1 = _bootstrap_employee_with_contract(client, mgr_token, wage=50000, first="Snap", last="ShotOne")
        emp2 = _bootstrap_employee_with_contract(client, mgr_token, wage=70000, first="Snap", last="ShotTwo")

        def snapshot():
            return {
                "rules": [(r.id, r.code, r.computation_method, r.fixed_amount, r.percentage, r.percentage_base, r.formula_expression, r.quantity, r.is_active)
                          for r in db_session.query(SalaryRule).order_by(SalaryRule.id).all()],
                "structures": [(s.id, s.name, s.code, s.is_active) for s in db_session.query(SalaryStructure).order_by(SalaryStructure.id).all()],
                "contracts": [(c.id, c.wage_monthly, c.start_date, c.end_date) for c in db_session.query(Contract).order_by(Contract.id).all()],
                "payslips": [(p.id, p.status, p.net) for p in db_session.query(Payslip).order_by(Payslip.id).all()],
                "warnings": [(w.id, w.code) for w in db_session.query(PayrollWarning).order_by(PayrollWarning.id).all()],
                "attendance": [(a.id,) for a in db_session.query(Attendance).order_by(Attendance.id).all()],
                "allocations": [(a.id,) for a in db_session.query(TimeOffAllocation).order_by(TimeOffAllocation.id).all()],
                "requests": [(r.id,) for r in db_session.query(TimeOffRequest).order_by(TimeOffRequest.id).all()],
            }

        db_session.expire_all()
        before = snapshot()

        res = _run(
            client, mgr_token, salary_structure_id=sid, employee_ids=[emp1["id"], emp2["id"]],
            rule_overrides=[
                {"rule_id": rule_ids["HRA"], "percentage": "35.00"},
                {"rule_id": rule_ids["ALLOWANCE"], "fixed_amount": "9999.00"},
                {"rule_id": rule_ids["PF"], "percentage": "1.00"},
            ],
        )
        assert res.status_code == 200, res.text
        # Sanity: the override actually took effect (proves this wasn't a
        # no-op that would trivially pass the non-mutation check).
        result = res.json()["employees"][0]
        components = {c["rule_code"]: c for c in result["components"]}
        assert components["HRA"]["simulated_amount"] == "8750.00"
        assert components["ALLOWANCE"]["simulated_amount"] == "9999.00"

        db_session.expire_all()
        after = snapshot()
        assert before == after, "Simulation must never mutate persisted payroll/HR data"

        # Also confirm the real SalaryRule rows still report their original
        # values via the API (not just the ORM snapshot).
        rules_after = client.get(f"/api/payroll/rules?salary_structure_id={sid}", headers=auth_headers(mgr_token)).json()
        hra_after = next(r for r in rules_after if r["code"] == "HRA")
        assert hra_after["percentage"] == "20.00"
