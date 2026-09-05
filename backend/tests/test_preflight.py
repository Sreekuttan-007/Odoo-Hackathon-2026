"""Payroll Preflight (Phase 8) — deterministic readiness & risk engine.

Covers spec sections 70-82: clean payrun, every blocker check, salary
variance, no-previous-payslip, attendance, time off, the backend
validation gate, warnings-don't-block, stale-Preflight protection, RBAC.
"""
from datetime import date, datetime, timezone
from decimal import Decimal

from tests.conftest import auth_headers
from tests.test_payroll_api import (
    _payroll_manager_token, _payroll_user_token, _give_schedule,
    _bootstrap_employee_with_contract, _create_structure_with_rules,
)
from app.models.contract import Contract
from app.models.attendance import Attendance
from app.models.payroll import Payslip
from app.models.time_off import TimeOffType, TimeOffRequest, TimeOffUnit, ApprovalPolicy, RequestStatus


def _make_payrun(client, token, sid, employee_ids, start="2026-03-01", end="2026-03-31"):
    res = client.post("/api/payroll/payruns", json={
        "salary_structure_id": sid, "period_start": start, "period_end": end, "employee_ids": employee_ids,
    }, headers=auth_headers(token))
    assert res.status_code == 200, res.text
    return res.json()


def _compute(client, token, pid):
    res = client.post(f"/api/payroll/payruns/{pid}/compute", headers=auth_headers(token))
    assert res.status_code == 200, res.text
    return res.json()


def _preflight(client, token, pid, method="get"):
    fn = client.get if method == "get" else client.post
    res = fn(f"/api/payroll/payruns/{pid}/preflight", headers=auth_headers(token))
    assert res.status_code == 200, res.text
    return res.json()


def _codes(pf):
    return [f["code"] for f in pf["findings"]]


def _setup(client, db_session, wage=50000, first="Aarav", last="Sharma", start="2026-03-01", end="2026-03-31"):
    token = _payroll_manager_token(client, db_session)
    sid = _create_structure_with_rules(client, token)
    emp = _bootstrap_employee_with_contract(client, token, wage=wage, first=first, last=last)
    _give_schedule(db_session, emp["id"])
    payrun = _make_payrun(client, token, sid, [emp["id"]], start=start, end=end)
    return token, sid, emp, payrun


class TestCleanPayrun:
    def test_clean_payrun_is_ready_and_validates(self, client, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        _compute(client, token, payrun["id"])

        pf = _preflight(client, token, payrun["id"])
        assert pf["summary"]["blockers"] == 0
        assert pf["readiness"] == "READY"
        # first payroll for this employee -> an INFO, never a variance WARNING
        assert "NO_PREVIOUS_PAYSLIP" in _codes(pf)
        assert "LARGE_NET_VARIANCE" not in _codes(pf)

        res = client.post(f"/api/payroll/payruns/{payrun['id']}/validate", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "VALIDATED"

    def test_preflight_is_read_only(self, client, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        _compute(client, token, payrun["id"])
        before = client.get(f"/api/payroll/payruns/{payrun['id']}", headers=auth_headers(token)).json()
        _preflight(client, token, payrun["id"])
        _preflight(client, token, payrun["id"], method="post")
        after = client.get(f"/api/payroll/payruns/{payrun['id']}", headers=auth_headers(token)).json()
        assert before == after

    def test_draft_payrun_reports_not_run(self, client, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        pf = _preflight(client, token, payrun["id"])
        assert pf["readiness"] == "NOT_RUN"
        assert pf["findings"] == []


class TestMissingContract:
    def test_missing_contract_blocks_and_recheck_clears(self, client, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        _compute(client, token, payrun["id"])

        # Break contract applicability AFTER compute (period no longer covered).
        contract = db_session.query(Contract).filter(Contract.employee_id == emp["id"]).first()
        original_start = contract.start_date
        contract.start_date = date(2026, 6, 1)
        db_session.commit()

        pf = _preflight(client, token, payrun["id"])
        assert pf["readiness"] == "ACTION_REQUIRED"
        finding = next(f for f in pf["findings"] if f["code"] == "MISSING_APPLICABLE_CONTRACT")
        assert finding["severity"] == "BLOCKER"
        assert finding["employee_id"] == emp["id"]
        assert finding["resolution"]

        # Backend validation gate must reject it.
        res = client.post(f"/api/payroll/payruns/{payrun['id']}/validate", headers=auth_headers(token))
        assert res.status_code == 409
        assert res.json()["detail"]["error"]["code"] == "VALIDATION_BLOCKED"
        assert client.get(f"/api/payroll/payruns/{payrun['id']}", headers=auth_headers(token)).json()["status"] == "COMPUTED"

        # Fix the contract, re-run Preflight -> blocker gone, validation proceeds.
        contract.start_date = original_start
        db_session.commit()
        pf = _preflight(client, token, payrun["id"], method="post")
        assert "MISSING_APPLICABLE_CONTRACT" not in _codes(pf)
        assert pf["summary"]["blockers"] == 0

        res = client.post(f"/api/payroll/payruns/{payrun['id']}/validate", headers=auth_headers(token))
        assert res.status_code == 200, res.text


class TestContractConflict:
    def test_overlapping_contracts_flagged_with_references(self, client, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        existing = db_session.query(Contract).filter(Contract.employee_id == emp["id"]).first()
        db_session.add(Contract(
            reference="CON/2026/9999", employee_id=emp["id"],
            department_id=existing.department_id, job_position_id=existing.job_position_id,
            start_date=date(2026, 2, 1), end_date=date(2026, 4, 30),
            wage_monthly=Decimal(60000), currency="INR",
        ))
        db_session.commit()
        _compute(client, token, payrun["id"])

        pf = _preflight(client, token, payrun["id"])
        finding = next(f for f in pf["findings"] if f["code"] == "CONTRACT_CONFLICT")
        assert finding["severity"] == "BLOCKER"
        refs = {c["reference"] for c in finding["evidence"]["contracts"]}
        assert refs == {existing.reference, "CON/2026/9999"}


class TestDuplicatePayslip:
    def test_overlapping_payslip_in_other_payrun_is_blocker_not_self(self, client, db_session):
        token, sid, emp, payrun_a = _setup(client, db_session)
        _compute(client, token, payrun_a["id"])
        payrun_b = _make_payrun(client, token, sid, [emp["id"]], start="2026-04-01", end="2026-04-30")
        _compute(client, token, payrun_b["id"])

        # Force payrun B's payslip period to overlap A's.
        b_slip = db_session.query(Payslip).filter(Payslip.payrun_id == payrun_b["id"]).first()
        b_slip.period_start = date(2026, 3, 15)
        b_slip.period_end = date(2026, 4, 15)
        db_session.commit()

        pf = _preflight(client, token, payrun_b["id"])
        dupes = [f for f in pf["findings"] if f["code"] == "DUPLICATE_PAYSLIP"]
        assert len(dupes) == 1
        assert dupes[0]["severity"] == "BLOCKER"
        assert dupes[0]["evidence"]["duplicates"][0]["payrun_reference"] == payrun_a["reference"]


class TestPayslipIntegrity:
    def test_tampered_persisted_total_is_blocker(self, client, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        _compute(client, token, payrun["id"])
        slip = db_session.query(Payslip).filter(Payslip.payrun_id == payrun["id"]).first()
        slip.net = slip.net + Decimal("1000.00")
        db_session.commit()

        pf = _preflight(client, token, payrun["id"])
        finding = next(f for f in pf["findings"] if f["code"] == "PAYSLIP_TOTAL_MISMATCH")
        assert finding["severity"] == "BLOCKER"
        assert "net" in finding["evidence"]["mismatches"]


class TestSalaryVariance:
    def test_large_net_change_is_warning_and_does_not_block(self, client, db_session):
        token, sid, emp, payrun_a = _setup(client, db_session, wage=50000)
        pid_a = payrun_a["id"]
        _compute(client, token, pid_a)
        client.post(f"/api/payroll/payruns/{pid_a}/validate", headers=auth_headers(token))
        client.post(f"/api/payroll/payruns/{pid_a}/mark-paid", headers=auth_headers(token))

        contract = db_session.query(Contract).filter(Contract.employee_id == emp["id"]).first()
        contract.wage_monthly = Decimal(90000)
        db_session.commit()

        payrun_b = _make_payrun(client, token, sid, [emp["id"]], start="2026-04-01", end="2026-04-30")
        _compute(client, token, payrun_b["id"])

        pf = _preflight(client, token, payrun_b["id"])
        finding = next(f for f in pf["findings"] if f["code"] == "LARGE_NET_VARIANCE")
        assert finding["severity"] == "WARNING"
        ev = finding["evidence"]
        assert ev["previous_net"] == "25000.00"
        assert ev["current_net"] == "45000.00"
        assert ev["absolute_delta"] == "20000.00"
        assert ev["percentage_delta"] == "80.00"

        # 0 blockers + a warning -> validation still succeeds (warnings are review-only).
        assert pf["summary"]["blockers"] == 0
        assert pf["readiness"] == "REVIEW_RECOMMENDED"
        res = client.post(f"/api/payroll/payruns/{payrun_b['id']}/validate", headers=auth_headers(token))
        assert res.status_code == 200, res.text

    def test_small_change_below_threshold_not_flagged(self, client, db_session):
        token, sid, emp, payrun_a = _setup(client, db_session, wage=50000)
        _compute(client, token, payrun_a["id"])
        client.post(f"/api/payroll/payruns/{payrun_a['id']}/validate", headers=auth_headers(token))

        contract = db_session.query(Contract).filter(Contract.employee_id == emp["id"]).first()
        contract.wage_monthly = Decimal(51000)  # +500 net, +2% -> below both bars
        db_session.commit()

        payrun_b = _make_payrun(client, token, sid, [emp["id"]], start="2026-04-01", end="2026-04-30")
        _compute(client, token, payrun_b["id"])
        pf = _preflight(client, token, payrun_b["id"])
        assert "LARGE_NET_VARIANCE" not in _codes(pf)


class TestAttendanceAndTimeOff:
    def test_incomplete_attendance_is_warning(self, client, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        db_session.add(Attendance(
            employee_id=emp["id"], attendance_date=date(2026, 3, 10),
            check_in=datetime(2026, 3, 10, 3, 30, tzinfo=timezone.utc), check_out=None,
        ))
        db_session.commit()
        _compute(client, token, payrun["id"])

        pf = _preflight(client, token, payrun["id"])
        finding = next(f for f in pf["findings"] if f["code"] == "INCOMPLETE_ATTENDANCE")
        assert finding["severity"] == "WARNING"
        assert finding["evidence"]["records"][0]["date"] == "2026-03-10"

    def test_approved_time_off_is_info_only(self, client, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        tot = TimeOffType(name="Casual Leave", unit=TimeOffUnit.DAYS, requires_allocation=False, approval_policy=ApprovalPolicy.NONE)
        db_session.add(tot)
        db_session.flush()
        db_session.add(TimeOffRequest(
            employee_id=emp["id"], time_off_type_id=tot.id,
            start_date=date(2026, 3, 5), end_date=date(2026, 3, 6),
            duration_amount=Decimal(2), status=RequestStatus.APPROVED,
        ))
        db_session.commit()
        _compute(client, token, payrun["id"])

        pf = _preflight(client, token, payrun["id"])
        finding = next(f for f in pf["findings"] if f["code"] == "APPROVED_TIME_OFF_IN_PERIOD")
        assert finding["severity"] == "INFO"
        assert finding["evidence"]["requests"][0]["amount"] == "2.00"
        # INFO never changes readiness away from READY on its own
        assert pf["readiness"] == "READY"


class TestValidationGate:
    def test_direct_validate_with_blocker_rejected(self, client, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        _compute(client, token, payrun["id"])
        contract = db_session.query(Contract).filter(Contract.employee_id == emp["id"]).first()
        contract.end_date = date(2026, 2, 1)  # contract now expires before the period
        db_session.commit()

        res = client.post(f"/api/payroll/payruns/{payrun['id']}/validate", headers=auth_headers(token))
        assert res.status_code == 409
        body = res.json()["detail"]["error"]
        assert body["code"] == "VALIDATION_BLOCKED"
        assert any(f["code"] == "MISSING_APPLICABLE_CONTRACT" for f in body["details"]["findings"])
        assert client.get(f"/api/payroll/payruns/{payrun['id']}", headers=auth_headers(token)).json()["status"] == "COMPUTED"

    def test_stale_ready_does_not_survive_data_change(self, client, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        _compute(client, token, payrun["id"])
        assert _preflight(client, token, payrun["id"])["readiness"] == "READY"

        # Introduce a blocker AFTER the "READY" Preflight, then validate
        # WITHOUT re-running Preflight — the gate must still catch it.
        contract = db_session.query(Contract).filter(Contract.employee_id == emp["id"]).first()
        contract.start_date = date(2026, 7, 1)
        db_session.commit()

        res = client.post(f"/api/payroll/payruns/{payrun['id']}/validate", headers=auth_headers(token))
        assert res.status_code == 409
        assert res.json()["detail"]["error"]["code"] == "VALIDATION_BLOCKED"


class TestRBAC:
    def test_employee_cannot_access_payrun_preflight(self, client, employee_token, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        _compute(client, token, payrun["id"])
        res = client.get(f"/api/payroll/payruns/{payrun['id']}/preflight", headers=auth_headers(employee_token))
        assert res.status_code == 403

    def test_payroll_user_can_access_preflight(self, client, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        _compute(client, token, payrun["id"])
        user_token = _payroll_user_token(client, db_session)
        res = client.get(f"/api/payroll/payruns/{payrun['id']}/preflight", headers=auth_headers(user_token))
        assert res.status_code == 200

    def test_unauthenticated_rejected(self, client, db_session):
        token, sid, emp, payrun = _setup(client, db_session)
        res = client.get(f"/api/payroll/payruns/{payrun['id']}/preflight")
        assert res.status_code == 401
