from decimal import Decimal
from tests.conftest import auth_headers, _make_user
from tests.test_payroll_api import (
    _payroll_manager_token, _give_schedule, _bootstrap_employee_with_contract,
)
from app.models.user import Role, User
from app.models.payroll import Payslip, PayslipLine, RuleCategory, ComputationMethod
from app.services import paytrace, payroll_narrator
from app.core.config import settings


def _create_full_structure(client, mgr_token):
    structure = client.post("/api/payroll/structures", json={"name": "PayTrace Test Structure"}, headers=auth_headers(mgr_token)).json()
    sid = structure["id"]
    rules = [
        {"name": "Basic Salary", "code": "BASIC", "category": "BASIC", "sequence": 1, "computation_method": "PERCENTAGE", "percentage": 50, "percentage_base": "CONTRACT_WAGE"},
        {"name": "House Rent Allowance", "code": "HRA", "category": "ALLOWANCE", "sequence": 10, "computation_method": "PERCENTAGE", "percentage": 20, "percentage_base": "BASIC"},
        {"name": "Standard Allowance", "code": "ALLOWANCE", "category": "ALLOWANCE", "sequence": 20, "computation_method": "FIXED", "fixed_amount": 2000},
        {"name": "Gross Salary", "code": "GROSS", "category": "GROSS", "sequence": 60, "computation_method": "FORMULA", "formula_expression": 'rules["BASIC"] + rules["HRA"] + rules["ALLOWANCE"]'},
        {"name": "Provident Fund", "code": "PF", "category": "DEDUCTION", "sequence": 80, "computation_method": "PERCENTAGE", "percentage": 10, "percentage_base": "BASIC"},
        {"name": "Net Salary", "code": "NET", "category": "NET", "sequence": 100, "computation_method": "FORMULA", "formula_expression": 'rules["GROSS"] - rules["PF"]'},
    ]
    for rule in rules:
        res = client.post(f"/api/payroll/rules?salary_structure_id={sid}", json=rule, headers=auth_headers(mgr_token))
        assert res.status_code == 200, res.text
    return sid


def _compute_one_payslip(client, mgr_token, sid, wage=50000):
    emp = _bootstrap_employee_with_contract(client, mgr_token, wage=wage)
    payrun = client.post("/api/payroll/payruns", json={
        "salary_structure_id": sid, "period_start": "2026-03-01", "period_end": "2026-03-31", "employee_ids": [emp["id"]],
    }, headers=auth_headers(mgr_token)).json()
    pid = payrun["id"]
    client.post(f"/api/payroll/payruns/{pid}/compute", headers=auth_headers(mgr_token))
    payslip = client.get(f"/api/payroll/payslips?payrun_id={pid}", headers=auth_headers(mgr_token)).json()[0]
    return emp, payrun, payslip


class TestPayTraceStructure:
    def test_full_trace_structure_and_dependencies(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_full_structure(client, mgr_token)
        emp, payrun, payslip = _compute_one_payslip(client, mgr_token, sid, wage=50000)

        res = client.get(f"/api/payroll/payslips/{payslip['id']}/trace", headers=auth_headers(mgr_token))
        assert res.status_code == 200, res.text
        trace = res.json()
        assert trace["available"] is True

        by_code = {e["rule_code"]: e for e in trace["entries"]}

        basic = by_code["BASIC"]
        assert basic["method"] == "PERCENTAGE"
        assert basic["calculation"]["percentage"] == "50.00"
        assert basic["calculation"]["base_code"] == "CONTRACT_WAGE"
        assert basic["calculation"]["base_amount"] == "50000.0000"
        assert basic["result"] == "25000.00"
        assert basic["depends_on"] == []  # CONTRACT_WAGE isn't a rule line

        hra = by_code["HRA"]
        assert hra["calculation"]["base_code"] == "BASIC"
        assert hra["result"] == "5000.00"
        assert hra["depends_on"] == ["BASIC"]  # dependency correctly resolved to BASIC, not Contract Wage

        allowance = by_code["ALLOWANCE"]
        assert allowance["method"] == "FIXED"
        assert allowance["calculation"]["fixed_amount"] == "2000.00"
        assert allowance["result"] == "2000.00"

        gross = by_code["GROSS"]
        assert gross["method"] == "FORMULA"
        assert set(gross["depends_on"]) == {"BASIC", "HRA", "ALLOWANCE"}
        assert gross["calculation"]["inputs"] == {"BASIC": "25000.00", "HRA": "5000.00", "ALLOWANCE": "2000.00"}
        assert gross["result"] == "32000.00"

        pf = by_code["PF"]
        assert pf["calculation"]["base_code"] == "BASIC"
        assert pf["result"] == "2500.00"

        net = by_code["NET"]
        assert set(net["depends_on"]) == {"GROSS", "PF"}
        assert net["result"] == "29500.00"

        assert trace["aggregates"]["net"] == "29500.00"

    def test_trace_order_matches_rule_sequence_not_alphabetical(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_full_structure(client, mgr_token)
        _, _, payslip = _compute_one_payslip(client, mgr_token, sid)

        res = client.get(f"/api/payroll/payslips/{payslip['id']}/trace", headers=auth_headers(mgr_token))
        sequences = [e["sequence"] for e in res.json()["entries"]]
        assert sequences == sorted(sequences)
        codes_in_order = [e["rule_code"] for e in res.json()["entries"]]
        assert codes_in_order == ["BASIC", "HRA", "ALLOWANCE", "GROSS", "PF", "NET"]

    def test_net_invariant_trace_matches_persisted_payslip(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_full_structure(client, mgr_token)
        _, _, payslip = _compute_one_payslip(client, mgr_token, sid, wage=90000)

        res = client.get(f"/api/payroll/payslips/{payslip['id']}/trace", headers=auth_headers(mgr_token))
        trace = res.json()
        net_entry = next(e for e in trace["entries"] if e["rule_code"] == "NET")

        full_payslip = client.get(f"/api/payroll/payslips/{payslip['id']}", headers=auth_headers(mgr_token)).json()
        assert net_entry["result"] == full_payslip["net"]
        assert trace["aggregates"]["net"] == full_payslip["net"]
        assert trace["aggregates"]["gross"] == full_payslip["gross"]

    def test_deduction_not_double_negated(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_full_structure(client, mgr_token)
        _, _, payslip = _compute_one_payslip(client, mgr_token, sid)

        res = client.get(f"/api/payroll/payslips/{payslip['id']}/trace", headers=auth_headers(mgr_token))
        trace = res.json()
        pf = next(e for e in trace["entries"] if e["rule_code"] == "PF")
        # Stored as a positive amount (matches existing engine semantics) —
        # PayTrace must not fabricate a negative sign on the raw result.
        assert pf["result"] == "2500.00"
        assert not pf["result"].startswith("-")


class TestPayTraceHistoricalIntegrity:
    def test_historical_trace_unaffected_by_later_rule_edit(self, client, db_session):
        """Mandatory test per Phase 7 spec section 35/69: editing a live
        SalaryRule after a Payslip was computed must never change that
        Payslip's PayTrace. Only a fresh recompute picks up the new rule."""
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_full_structure(client, mgr_token)
        emp, payrun, payslip = _compute_one_payslip(client, mgr_token, sid, wage=100000)

        before = client.get(f"/api/payroll/payslips/{payslip['id']}/trace", headers=auth_headers(mgr_token)).json()
        hra_before = next(e for e in before["entries"] if e["rule_code"] == "HRA")
        assert hra_before["calculation"]["percentage"] == "20.00"
        assert hra_before["result"] == "10000.00"

        rules = client.get(f"/api/payroll/rules?salary_structure_id={sid}", headers=auth_headers(mgr_token)).json()
        hra_rule_id = next(r["id"] for r in rules if r["code"] == "HRA")
        patch = client.patch(f"/api/payroll/rules/{hra_rule_id}", json={"percentage": 25}, headers=auth_headers(mgr_token))
        assert patch.status_code == 200, patch.text

        after = client.get(f"/api/payroll/payslips/{payslip['id']}/trace", headers=auth_headers(mgr_token)).json()
        hra_after = next(e for e in after["entries"] if e["rule_code"] == "HRA")
        assert hra_after["calculation"]["percentage"] == "20.00", "historical PayTrace must not shift when the live rule changes"
        assert hra_after["result"] == "10000.00"

        # A fresh employee computed AFTER the edit must reflect the new rule.
        emp2 = _bootstrap_employee_with_contract(client, mgr_token, wage=100000, first="Second", last="Employee")
        payrun2 = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-06-01", "period_end": "2026-06-30", "employee_ids": [emp2["id"]],
        }, headers=auth_headers(mgr_token)).json()
        client.post(f"/api/payroll/payruns/{payrun2['id']}/compute", headers=auth_headers(mgr_token))
        new_payslip = client.get(f"/api/payroll/payslips?payrun_id={payrun2['id']}", headers=auth_headers(mgr_token)).json()[0]
        new_trace = client.get(f"/api/payroll/payslips/{new_payslip['id']}/trace", headers=auth_headers(mgr_token)).json()
        new_hra = next(e for e in new_trace["entries"] if e["rule_code"] == "HRA")
        assert new_hra["calculation"]["percentage"] == "25.00"

    def test_legacy_line_without_structured_snapshot_falls_back_gracefully(self, db_session):
        """Lines computed before Phase 7 have NULL structured snapshot
        columns. PayTrace must show the pre-existing human string, not
        fabricate structured numbers it doesn't have."""
        from datetime import date, datetime, timezone
        from app.models.employee import Employee, EmployeeStatus
        from app.models.payroll import SalaryStructure, Payrun

        employee = Employee(first_name="Legacy", last_name="Payee", status=EmployeeStatus.ACTIVE)
        db_session.add(employee)
        structure = SalaryStructure(name="Legacy Structure")
        db_session.add(structure)
        db_session.flush()
        payrun = Payrun(reference="PR/LEGACY/0001", salary_structure_id=structure.id, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31))
        db_session.add(payrun)
        db_session.flush()

        payslip = Payslip(
            payrun_id=payrun.id, employee_id=employee.id, salary_structure_id=structure.id,
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
            basic=Decimal("25000.00"), net=Decimal("25000.00"),
            computed_at=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )
        db_session.add(payslip)
        db_session.flush()
        db_session.add(PayslipLine(
            payslip_id=payslip.id, rule_name_snapshot="Basic Salary", rule_code_snapshot="BASIC",
            category_snapshot=RuleCategory.BASIC, sequence_snapshot=1,
            computation_method_snapshot=ComputationMethod.PERCENTAGE,
            base_description_snapshot="50.00% of Contract Wage (50000.00)",
            amount=Decimal("25000.00"),
            # fixed_amount_snapshot / percentage_snapshot / etc all None (legacy row)
        ))
        db_session.commit()
        db_session.refresh(payslip)

        result = paytrace.build_paytrace(payslip)
        assert result["available"] is True
        entry = result["entries"][0]
        assert entry["has_structured_history"] is False
        assert entry["calculation"] is None
        assert entry["explanation"] == "50.00% of Contract Wage (50000.00)"


class TestPayTraceEdgeCases:
    def test_uncomputed_payslip_returns_unavailable_not_fabricated(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_full_structure(client, mgr_token)
        emp = _bootstrap_employee_with_contract(client, mgr_token)
        payrun = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-05-01", "period_end": "2026-05-31", "employee_ids": [emp["id"]],
        }, headers=auth_headers(mgr_token)).json()
        payslip = client.get(f"/api/payroll/payslips?payrun_id={payrun['id']}", headers=auth_headers(mgr_token)).json()[0]

        res = client.get(f"/api/payroll/payslips/{payslip['id']}/trace", headers=auth_headers(mgr_token))
        assert res.status_code == 200
        body = res.json()
        assert body["available"] is False
        assert body["reason"] == "NOT_COMPUTED"

    def test_trace_endpoint_is_read_only(self, client, db_session):
        """GET /trace must never mutate the Payslip — calling it twice
        must not change the status or recompute anything."""
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_full_structure(client, mgr_token)
        _, _, payslip = _compute_one_payslip(client, mgr_token, sid)

        before = client.get(f"/api/payroll/payslips/{payslip['id']}", headers=auth_headers(mgr_token)).json()
        client.get(f"/api/payroll/payslips/{payslip['id']}/trace", headers=auth_headers(mgr_token))
        client.get(f"/api/payroll/payslips/{payslip['id']}/trace", headers=auth_headers(mgr_token))
        after = client.get(f"/api/payroll/payslips/{payslip['id']}", headers=auth_headers(mgr_token)).json()
        assert before == after


class TestPayTraceRBAC:
    def test_employee_can_trace_own_but_not_others(self, client, employee_token, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_full_structure(client, mgr_token)

        self_user = db_session.query(User).filter(User.work_email == "employee-test@payloom.local").first()
        _give_schedule(db_session, self_user.employee_id)
        dept = client.post("/api/departments", json={"name": "Engineering"}, headers=auth_headers(mgr_token)).json()
        pos = client.post("/api/job-positions", json={"title": "Software Engineer"}, headers=auth_headers(mgr_token)).json()
        client.post("/api/contracts", json={
            "employee_id": self_user.employee_id, "department_id": dept["id"], "job_position_id": pos["id"],
            "start_date": "2026-01-01", "wage_monthly": 40000,
        }, headers=auth_headers(mgr_token))
        other_emp = _bootstrap_employee_with_contract(client, mgr_token, first="Other", last="Person")

        payrun = client.post("/api/payroll/payruns", json={
            "salary_structure_id": sid, "period_start": "2026-04-01", "period_end": "2026-04-30",
            "employee_ids": [self_user.employee_id, other_emp["id"]],
        }, headers=auth_headers(mgr_token)).json()
        pid = payrun["id"]
        payslips = client.get(f"/api/payroll/payslips?payrun_id={pid}", headers=auth_headers(mgr_token)).json()
        self_payslip = next(p for p in payslips if p["employee"]["id"] == self_user.employee_id)
        other_payslip = next(p for p in payslips if p["employee"]["id"] == other_emp["id"])

        client.post(f"/api/payroll/payruns/{pid}/compute", headers=auth_headers(mgr_token))
        client.post(f"/api/payroll/payruns/{pid}/validate", headers=auth_headers(mgr_token))

        res = client.get(f"/api/payroll/payslips/{self_payslip['id']}/trace", headers=auth_headers(employee_token))
        assert res.status_code == 200
        assert res.json()["available"] is True

        res = client.get(f"/api/payroll/payslips/{other_payslip['id']}/trace", headers=auth_headers(employee_token))
        assert res.status_code == 403
        assert res.json()["detail"]["error"]["code"] == "ACCESS_DENIED"

    def test_unauthenticated_rejected(self, client, db_session):
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_full_structure(client, mgr_token)
        _, _, payslip = _compute_one_payslip(client, mgr_token, sid)
        res = client.get(f"/api/payroll/payslips/{payslip['id']}/trace")
        assert res.status_code == 401


class TestPayTraceAINarrator:
    def test_narrator_unavailable_without_api_key_never_raises(self, client, db_session, monkeypatch):
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
        mgr_token = _payroll_manager_token(client, db_session)
        sid = _create_full_structure(client, mgr_token)
        _, _, payslip = _compute_one_payslip(client, mgr_token, sid)

        res = client.get(f"/api/payroll/payslips/{payslip['id']}/trace/explain?mode=employee", headers=auth_headers(mgr_token))
        assert res.status_code == 200
        body = res.json()
        assert body["available"] is False
        assert body["reason"] == "NOT_CONFIGURED"
        assert body["summary"] is None

    def test_narrator_direct_call_handles_provider_timeout(self, monkeypatch):
        import httpx

        def _raise_timeout(*args, **kwargs):
            raise httpx.TimeoutException("boom")

        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "fake-key-for-test")
        monkeypatch.setattr(httpx, "post", _raise_timeout)

        trace = {"employee": {"name": "Test Person"}, "period": {"start": "2026-01-01", "end": "2026-01-31"},
                 "salary_structure": {"name": "Regular"}, "entries": [], "aggregates": {}}
        result = payroll_narrator.explain(trace, mode="employee")
        assert result["available"] is False
        assert result["reason"] == "TIMEOUT"

    def test_narrator_discards_component_referencing_unknown_rule_code(self, monkeypatch):
        """Fact-integrity: even a well-formed model response must be
        filtered against the trace's actual rule codes — a hallucinated
        rule_code must never pass through."""
        import httpx
        import json as _json

        class FakeResponse:
            status_code = 200
            def raise_for_status(self): pass
            def json(self):
                return {"content": [{"text": _json.dumps({
                    "summary": "Your Basic Salary is 50% of your contract wage.",
                    "components": [
                        {"rule_code": "BASIC", "explanation": "Real rule, kept."},
                        {"rule_code": "MADE_UP_TAX", "explanation": "Hallucinated rule, must be dropped."},
                    ],
                })}]}

        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "fake-key-for-test")
        monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse())

        trace = {
            "employee": {"name": "Test Person"}, "period": {"start": "2026-01-01", "end": "2026-01-31"},
            "salary_structure": {"name": "Regular"},
            "entries": [{"sequence": 1, "rule_name": "Basic Salary", "rule_code": "BASIC", "category": "BASIC",
                         "method": "PERCENTAGE", "result": "25000.00", "calculation": {}, "explanation": "..."}],
            "aggregates": {},
        }
        result = payroll_narrator.explain(trace, mode="employee")
        assert result["available"] is True
        codes = [c["rule_code"] for c in result["components"]]
        assert "BASIC" in codes
        assert "MADE_UP_TAX" not in codes
