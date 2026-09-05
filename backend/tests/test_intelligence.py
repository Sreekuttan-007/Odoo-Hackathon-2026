"""Payloom Intelligence (Phase 10) — grounded AI payroll brief.

Covers spec sections 51-62 / 74: evidence privacy + determinism, valid
brief, unknown source rejection, severity tampering, invented claims,
numeric hallucination, every provider-failure path, RBAC, the
non-mutation invariant, and a payroll-flow regression with the brief in
the loop.

The AI provider is always mocked — no test makes a network call.
"""
import json as _json
from decimal import Decimal

import httpx
import pytest

from tests.conftest import auth_headers, _make_user
from tests.test_payroll_api import (
    _payroll_manager_token, _payroll_user_token, _give_schedule,
    _bootstrap_employee_with_contract,
)
from app.core.config import settings
from app.models.user import Role
from app.models.contract import Contract
from app.models.payroll import Payrun, Payslip, PayslipLine, SalaryRule
from app.services import intelligence


# --------------------------------------------------------------------- setup
def _hra_structure(client, token):
    """BASIC 50% of wage, HRA 20% of BASIC, GROSS, PF 10% of BASIC, NET."""
    sid = client.post("/api/payroll/structures", json={"name": "Intelligence Test"},
                      headers=auth_headers(token)).json()["id"]
    rules = [
        {"name": "Basic", "code": "BASIC", "category": "BASIC", "sequence": 1,
         "computation_method": "PERCENTAGE", "percentage": 50, "percentage_base": "CONTRACT_WAGE"},
        {"name": "HRA", "code": "HRA", "category": "ALLOWANCE", "sequence": 10,
         "computation_method": "PERCENTAGE", "percentage": 20, "percentage_base": "BASIC"},
        {"name": "Gross", "code": "GROSS", "category": "GROSS", "sequence": 60,
         "computation_method": "FORMULA", "formula_expression": 'rules["BASIC"] + rules["HRA"]'},
        {"name": "PF", "code": "PF", "category": "DEDUCTION", "sequence": 80,
         "computation_method": "PERCENTAGE", "percentage": 10, "percentage_base": "BASIC"},
        {"name": "Net", "code": "NET", "category": "NET", "sequence": 100,
         "computation_method": "FORMULA", "formula_expression": 'rules["GROSS"] - rules["PF"]'},
    ]
    for r in rules:
        res = client.post(f"/api/payroll/rules?salary_structure_id={sid}", json=r, headers=auth_headers(token))
        assert res.status_code == 200, res.text
    return sid


def _computed_payrun(client, token, db_session, wage=50000, start="2026-09-01", end="2026-09-30"):
    sid = _hra_structure(client, token)
    emp = _bootstrap_employee_with_contract(client, token, wage=wage, first="Aarav", last="Mehta")
    _give_schedule(db_session, emp["id"])
    payrun = client.post("/api/payroll/payruns", json={
        "salary_structure_id": sid, "period_start": start, "period_end": end, "employee_ids": [emp["id"]],
    }, headers=auth_headers(token)).json()
    client.post(f"/api/payroll/payruns/{payrun['id']}/compute", headers=auth_headers(token))
    return sid, emp, payrun


def _brief(client, token, payrun_id, body=None):
    return client.post(f"/api/payroll/payruns/{payrun_id}/intelligence/brief",
                       json=body or {}, headers=auth_headers(token))


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return {"content": [{"text": _json.dumps(self._payload)}]}


def _mock_provider(monkeypatch, payload):
    # Force the Anthropic path so the wire-format FakeResponse below matches.
    monkeypatch.setattr(settings, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _FakeResponse(payload))


# --------------------------------------------------------------- evidence
def test_evidence_packet_carries_no_sensitive_data(client, db_session):
    token = _payroll_manager_token(client, db_session)
    _, emp, payrun = _computed_payrun(client, token, db_session)
    pr = db_session.query(Payrun).filter(Payrun.id == payrun["id"]).first()

    evidence = intelligence.build_brief_evidence(db_session, pr)
    blob = _json.dumps(evidence).lower()

    for banned in ("account", "ifsc", "swift", "aadhaar", "passport", "password",
                   "token", "secret", "@payloom", "api_key", "bearer"):
        assert banned not in blob, f"evidence packet leaked '{banned}'"
    # names must be reduced to employee codes
    assert "aarav" not in blob and "mehta" not in blob
    assert any(s["type"] == "PAYROLL" and s["code"] == "TOTAL_NET" for s in evidence["sources"])


def test_evidence_fingerprint_is_deterministic(client, db_session):
    token = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, token, db_session)
    pr = db_session.query(Payrun).filter(Payrun.id == payrun["id"]).first()
    f1 = intelligence.build_brief_evidence(db_session, pr)["fingerprint"]
    f2 = intelligence.build_brief_evidence(db_session, pr)["fingerprint"]
    assert f1 == f2 and len(f1) == 16


# --------------------------------------------------------------- fallback
def test_brief_without_api_key_is_deterministic_fallback(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    token = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, token, db_session)

    res = _brief(client, token, payrun["id"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["available"] is False
    assert data["is_fallback"] is True
    assert data["reason"] == "NOT_CONFIGURED"
    assert data["deterministic_summary"]
    assert data["summary"]  # backend-generated, not AI
    # first payroll -> NO_PREVIOUS_PAYSLIP INFO source exists but is not an attention item
    assert all(i["priority"] in ("BLOCKER", "WARNING") for i in data["attention_items"])


def test_draft_payrun_reports_not_computed(client, db_session):
    token = _payroll_manager_token(client, db_session)
    sid = _hra_structure(client, token)
    emp = _bootstrap_employee_with_contract(client, token, wage=50000)
    _give_schedule(db_session, emp["id"])
    payrun = client.post("/api/payroll/payruns", json={
        "salary_structure_id": sid, "period_start": "2026-09-01", "period_end": "2026-09-30",
        "employee_ids": [emp["id"]],
    }, headers=auth_headers(token)).json()

    data = _brief(client, token, payrun["id"]).json()
    assert data["available"] is False
    assert data["reason"] == "NOT_COMPUTED"


# --------------------------------------------------------------- valid brief
def test_valid_brief_is_accepted_and_grounded(client, db_session, monkeypatch):
    token = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, token, db_session)
    pr = db_session.query(Payrun).filter(Payrun.id == payrun["id"]).first()
    evidence = intelligence.build_brief_evidence(db_session, pr)
    net_src = next(s for s in evidence["sources"] if s["code"] == "TOTAL_NET")

    _mock_provider(monkeypatch, {
        "headline": "September Payroll Brief",
        "summary": "Payroll has been computed for one employee.",
        "attention_items": [],
        "observations": [
            {"title": "Total net", "text": net_src["label"], "source_ids": [net_src["id"]]},
        ],
        "suggested_review_order": [],
    })

    data = _brief(client, token, payrun["id"]).json()
    assert data["available"] is True
    assert data["is_fallback"] is False
    assert data["headline"] == "September Payroll Brief"
    assert len(data["observations"]) == 1
    assert data["observations"][0]["source_type"] == "PAYROLL"
    assert data["observations"][0]["source_code"] == "TOTAL_NET"


def test_gemini_provider_path_is_wired(client, db_session, monkeypatch):
    """AI_PROVIDER=gemini uses the Gemini wire format end to end."""
    token = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, token, db_session)
    pr = db_session.query(Payrun).filter(Payrun.id == payrun["id"]).first()
    net_src = next(s for s in intelligence.build_brief_evidence(db_session, pr)["sources"] if s["code"] == "TOTAL_NET")

    class _Gemini:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": _json.dumps({
                "headline": "Gemini brief", "summary": "ok", "attention_items": [],
                "observations": [{"title": "Net", "text": net_src["label"], "source_ids": [net_src["id"]]}],
                "suggested_review_order": [],
            })}]}}]}

    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Gemini())

    data = _brief(client, token, payrun["id"]).json()
    assert data["available"] is True
    assert data["provider"] == "gemini"
    assert data["headline"] == "Gemini brief"
    assert len(data["observations"]) == 1


def test_unknown_source_id_is_dropped(client, db_session, monkeypatch):
    token = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, token, db_session)
    _mock_provider(monkeypatch, {
        "headline": "Brief", "summary": "…",
        "attention_items": [
            {"title": "Made up", "text": "A tax compliance issue was found.", "source_ids": ["src_999"]},
        ],
        "observations": [], "suggested_review_order": [],
    })
    data = _brief(client, token, payrun["id"]).json()
    assert data["available"] is True
    assert data["attention_items"] == []


def test_item_without_any_source_is_dropped(client, db_session, monkeypatch):
    token = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, token, db_session)
    _mock_provider(monkeypatch, {
        "headline": "Brief", "summary": "…",
        "attention_items": [],
        "observations": [{"title": "Ungrounded", "text": "Everything looks great.", "source_ids": []}],
        "suggested_review_order": [],
    })
    data = _brief(client, token, payrun["id"]).json()
    assert data["observations"] == []


def test_severity_cannot_be_upgraded_by_ai(client, db_session, monkeypatch):
    """A WARNING-severity source cited by an item the model tags BLOCKER
    must come back with the deterministic WARNING severity."""
    token = _payroll_manager_token(client, db_session)
    _, emp, payrun = _computed_payrun(client, token, db_session)

    # Force a WARNING: add a second, strictly-earlier computed payslip with a
    # very different net so Preflight raises LARGE_NET_VARIANCE.
    pr = db_session.query(Payrun).filter(Payrun.id == payrun["id"]).first()
    ps = pr.payslips[0]
    prior = Payslip(
        payrun_id=pr.id, employee_id=ps.employee_id, salary_structure_id=ps.salary_structure_id,
        period_start=__import__("datetime").date(2026, 8, 1), period_end=__import__("datetime").date(2026, 8, 31),
        status=ps.status, net=Decimal("1000.00"), gross=Decimal("1000.00"),
        computed_at=ps.computed_at,
    )
    # different payrun to avoid the unique (payrun, employee) constraint
    other_pr = Payrun(reference="PR/2026/9999", salary_structure_id=pr.salary_structure_id,
                      period_start=prior.period_start, period_end=prior.period_end, status=pr.status)
    db_session.add(other_pr)
    db_session.flush()
    prior.payrun_id = other_pr.id
    db_session.add(prior)
    db_session.commit()

    pr = db_session.query(Payrun).filter(Payrun.id == payrun["id"]).first()
    evidence = intelligence.build_brief_evidence(db_session, pr)
    variance = next((s for s in evidence["sources"] if s["code"] == "LARGE_NET_VARIANCE"), None)
    assert variance is not None and variance["severity"] == "WARNING"

    _mock_provider(monkeypatch, {
        "headline": "Brief", "summary": "…",
        "attention_items": [
            {"title": "Variance", "text": variance["label"], "priority": "BLOCKER",
             "source_ids": [variance["id"]]},
        ],
        "observations": [], "suggested_review_order": [],
    })
    data = _brief(client, token, payrun["id"]).json()
    assert len(data["attention_items"]) == 1
    assert data["attention_items"][0]["priority"] == "WARNING"


def test_numeric_hallucination_is_dropped(client, db_session, monkeypatch):
    token = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, token, db_session)
    pr = db_session.query(Payrun).filter(Payrun.id == payrun["id"]).first()
    evidence = intelligence.build_brief_evidence(db_session, pr)
    net_src = next(s for s in evidence["sources"] if s["code"] == "TOTAL_NET")

    _mock_provider(monkeypatch, {
        "headline": "Brief", "summary": "…",
        "attention_items": [],
        "observations": [
            {"title": "Wrong total", "text": "The total net payroll is ₹9,99,999.00.",
             "source_ids": [net_src["id"]]},
        ],
        "suggested_review_order": [],
    })
    data = _brief(client, token, payrun["id"]).json()
    assert data["observations"] == []


# --------------------------------------------------------------- provider failure
@pytest.mark.parametrize("break_it", ["timeout", "http_500", "malformed"])
def test_provider_failure_falls_back_and_never_raises(client, db_session, monkeypatch, break_it):
    token = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, token, db_session)
    monkeypatch.setattr(settings, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "fake-key-for-test")

    if break_it == "timeout":
        def boom(*a, **k):
            raise httpx.TimeoutException("slow")
        monkeypatch.setattr(httpx, "post", boom)
        expected = "TIMEOUT"
    elif break_it == "http_500":
        class R:
            status_code = 500
            def raise_for_status(self):
                raise httpx.HTTPStatusError("err", request=None, response=httpx.Response(500))
        monkeypatch.setattr(httpx, "post", lambda *a, **k: R())
        expected = "PROVIDER_ERROR"
    else:
        class R:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return {"content": [{"text": "not json at all"}]}
        monkeypatch.setattr(httpx, "post", lambda *a, **k: R())
        expected = "MALFORMED_RESPONSE"

    res = _brief(client, token, payrun["id"])
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["available"] is False
    assert data["reason"] == expected
    assert data["is_fallback"] is True
    assert data["deterministic_summary"]


# --------------------------------------------------------------- RBAC
def test_employee_cannot_generate_payrun_brief(client, db_session, employee_token):
    token = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, token, db_session)
    res = _brief(client, employee_token, payrun["id"])
    assert res.status_code == 403


def test_hr_manager_cannot_generate_payrun_brief(client, db_session, hr_token):
    token = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, token, db_session)
    res = _brief(client, hr_token, payrun["id"])
    assert res.status_code == 403


def test_payroll_user_can_generate_brief(client, db_session, monkeypatch):
    mgr = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, mgr, db_session)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
    user = _payroll_user_token(client, db_session)
    res = _brief(client, user, payrun["id"])
    assert res.status_code == 200


# --------------------------------------------------------------- non-mutation
def _snapshot(db):
    def rows(model, *cols):
        out = []
        for obj in db.query(model).all():
            out.append(tuple(str(getattr(obj, c)) for c in cols))
        return sorted(out)
    return {
        "rules": rows(SalaryRule, "id", "computation_method", "percentage", "fixed_amount", "formula_expression"),
        "payruns": rows(Payrun, "id", "status", "computed_at", "validated_at", "paid_at"),
        "payslips": rows(Payslip, "id", "status", "basic", "gross", "deductions", "net", "computed_at"),
        "lines": rows(PayslipLine, "id", "amount", "rule_code_snapshot"),
        "contracts": rows(Contract, "id", "wage_monthly", "start_date", "end_date"),
    }


def test_brief_does_not_mutate_the_database(client, db_session, monkeypatch):
    token = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, token, db_session)
    pr = db_session.query(Payrun).filter(Payrun.id == payrun["id"]).first()
    net_src = next(s for s in intelligence.build_brief_evidence(db_session, pr)["sources"] if s["code"] == "TOTAL_NET")
    _mock_provider(monkeypatch, {
        "headline": "Brief", "summary": "…", "attention_items": [],
        "observations": [{"title": "Net", "text": net_src["label"], "source_ids": [net_src["id"]]}],
        "suggested_review_order": [],
    })

    before = _snapshot(db_session)
    for _ in range(3):
        assert _brief(client, token, payrun["id"]).status_code == 200
    db_session.expire_all()
    after = _snapshot(db_session)
    assert before == after


def test_payroll_flow_still_validates_with_brief_in_the_loop(client, db_session, monkeypatch):
    token = _payroll_manager_token(client, db_session)
    _, _, payrun = _computed_payrun(client, token, db_session)
    pid = payrun["id"]
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)

    assert _brief(client, token, pid).status_code == 200
    pf = client.get(f"/api/payroll/payruns/{pid}/preflight", headers=auth_headers(token)).json()
    assert pf["readiness"] == "READY"
    val = client.post(f"/api/payroll/payruns/{pid}/validate", headers=auth_headers(token))
    assert val.status_code == 200 and val.json()["status"] == "VALIDATED"
    assert _brief(client, token, pid).status_code == 200
    paid = client.post(f"/api/payroll/payruns/{pid}/mark-paid", headers=auth_headers(token))
    assert paid.status_code == 200 and paid.json()["status"] == "PAID"
