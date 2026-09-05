"""Payloom Intelligence (Phase 10) — a GROUNDED AI explanation layer that
sits *above* Payloom's deterministic payroll systems.

    Payroll Engine -> PayTrace -> Preflight -> Simulator
                         -> verified structured evidence ->
                    Payloom Intelligence -> grounded payroll brief

The core rule (spec sections 2 / 37): the LLM may explain, summarise,
prioritise and communicate verified payroll facts. It may NEVER
calculate or modify payroll, invent numbers, invent risks, or change a
severity label. If the model disagrees with Payloom, Payloom wins.

How that rule is enforced here, not just asserted:
- `build_brief_evidence()` produces a deterministic, sanitised evidence
  packet with an explicit SOURCE REGISTRY. Every fact the model is
  allowed to cite has a stable `id`. Numbers are pre-computed by the
  deterministic engine (Preflight / payrun totals / Simulator) — the
  model never derives one.
- The model is constrained to reference `source_ids` from that registry.
- `_validate_items()` drops any item that cites an unknown id, cites
  nothing, upgrades a severity, or states a ₹-figure that doesn't appear
  verbatim in a cited source. What survives is grounded by construction.
- Every failure path (no API key, timeout, provider 4xx/5xx, malformed
  JSON, schema mismatch) degrades to a backend-generated deterministic
  fallback. `run()` never raises. Payroll is never affected.

Privacy / data minimisation (spec sections 8-9 / 57): the evidence packet
carries employee *codes* (EMP-0042), never names, bank details, IDs,
addresses, phones, emails, tokens or secrets — and there is a test that
asserts the packet's JSON contains none of those.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.orm import Session

from app.models.payroll import Payrun, PayrunStatus, WarningSeverity
from app.services import ai_provider, preflight

logger = logging.getLogger("payloom.intelligence")

_SEVERITY_RANK = {"BLOCKER": 0, "WARNING": 1, "INFO": 2}
_TWO = Decimal("0.01")


# --------------------------------------------------------------------------
# Evidence builder
# --------------------------------------------------------------------------
def _q2(value) -> Decimal:
    return Decimal(value or 0).quantize(_TWO, rounding=ROUND_HALF_UP)


def _money(value) -> dict:
    d = _q2(value)
    # en-IN grouping without a locale dependency.
    whole, _, frac = f"{d:.2f}".partition(".")
    neg = whole.startswith("-")
    digits = whole.lstrip("-")
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        head = re.sub(r"(?<=\d)(?=(\d\d)+$)", ",", head)
        grouped = f"{head},{tail}"
    else:
        grouped = digits
    return {"raw": str(d), "display": f"{'-' if neg else ''}₹{grouped}.{frac}"}


def _employee_ref(employee) -> str:
    if employee is None:
        return "EMP-?"
    if getattr(employee, "employee_code", None):
        return employee.employee_code
    return f"EMP-{employee.id:04d}"


def _payrun_totals(payrun: Payrun) -> dict:
    payslips = list(payrun.payslips)
    return {
        "payslip_count": len(payslips),
        "gross": _money(sum((p.gross or Decimal(0) for p in payslips), Decimal(0))),
        "deductions": _money(sum((p.deductions or Decimal(0) for p in payslips), Decimal(0))),
        "net": _money(sum((p.net or Decimal(0) for p in payslips), Decimal(0))),
        "computed_count": sum(1 for p in payslips if p.computed_at is not None),
        "blocked_count": sum(
            1 for p in payslips if any(w.severity == WarningSeverity.BLOCKER for w in p.warnings)
        ),
    }


def _finding_route(finding: dict) -> Optional[str]:
    code = finding.get("code")
    eid = finding.get("employee_id")
    psid = finding.get("payslip_id")
    if code in {"MISSING_APPLICABLE_CONTRACT", "CONTRACT_CONFLICT"} and eid:
        return f"/contracts?employee_id={eid}"
    if code in {"INCOMPLETE_ATTENDANCE", "LONG_ATTENDANCE_SESSION", "ATTENDANCE_ABOVE_SCHEDULE"} and eid:
        return f"/attendance?employee_id={eid}"
    if code == "LARGE_NET_VARIANCE" and psid:
        return f"/payroll/payslips/{psid}/trace"
    if psid:
        return f"/payroll/payslips/{psid}"
    return None


def build_brief_evidence(
    db: Session, payrun: Payrun, simulator_scenario: Optional[dict] = None
) -> dict:
    """The deterministic, sanitised evidence packet + source registry.
    Persists nothing. Reuses `preflight.run_preflight` verbatim for the
    findings — Intelligence never re-derives severity."""
    pf = preflight.run_preflight(db, payrun)
    totals = _payrun_totals(payrun)
    employee_by_id = {p.employee_id: p.employee for p in payrun.payslips}

    sources: list[dict] = []

    def add(sid, stype, code, label, *, severity=None, detail=None, employee_ref=None, route=None):
        sources.append({
            "id": sid, "type": stype, "code": code, "label": label,
            "severity": severity, "detail": detail,
            "employee_ref": employee_ref, "route": route,
        })

    add("src_total_net", "PAYROLL", "TOTAL_NET",
        f"Total net payroll is {totals['net']['display']}",
        detail=f"raw={totals['net']['raw']}", route=f"/payroll/payruns/{payrun.id}")
    add("src_total_gross", "PAYROLL", "TOTAL_GROSS",
        f"Total gross payroll is {totals['gross']['display']}",
        detail=f"raw={totals['gross']['raw']}")
    add("src_total_deductions", "PAYROLL", "TOTAL_DEDUCTIONS",
        f"Total deductions are {totals['deductions']['display']}",
        detail=f"raw={totals['deductions']['raw']}")
    add("src_scope", "PAYROLL", "SCOPE",
        f"Payroll scope: {totals['payslip_count']} payslip(s), "
        f"{totals['computed_count']} computed, {totals['blocked_count']} blocked",
        route=f"/payroll/payruns/{payrun.id}")

    findings = pf.get("findings", [])
    seen_codes: dict[str, int] = {}
    finding_sources: list[dict] = []
    for f in findings:
        code = f.get("code", "UNKNOWN")
        seen_codes[code] = seen_codes.get(code, 0) + 1
        ref = None
        if f.get("employee_id") in employee_by_id:
            ref = _employee_ref(employee_by_id[f["employee_id"]])
        sid = f"src_pf_{code.lower()}_{seen_codes[code]}"
        entry = {
            "id": sid, "type": "PREFLIGHT", "code": code,
            "label": _sanitise_message(f.get("message", ""), employee_by_id.get(f.get("employee_id"))),
            "severity": f.get("severity"),
            "detail": f.get("resolution"),
            "employee_ref": ref,
            "route": _finding_route(f),
        }
        finding_sources.append(entry)
        sources.append(entry)

    if simulator_scenario:
        sim = simulator_scenario
        add("src_sim_scenario", "SIMULATOR", "SCENARIO",
            sim.get("description") or "A payroll simulation scenario was run.",
            detail=sim.get("assumption"),
            route="/payroll/simulator")
        if sim.get("aggregate_net_delta_display"):
            add("src_sim_net_delta", "SIMULATOR", "NET_DELTA",
                f"Simulated monthly net payroll change: {sim['aggregate_net_delta_display']} "
                f"across {sim.get('employees_simulated', '?')} employee(s)",
                detail=sim.get("annualized_note"))

    evidence = {
        "payrun": {
            "id": payrun.id,
            "reference": payrun.reference,
            "status": payrun.status.value,
            "period": {"start": payrun.period_start.isoformat(), "end": payrun.period_end.isoformat()},
        },
        "totals": totals,
        "preflight": {
            "readiness": pf.get("readiness"),
            "summary": pf.get("summary", {"blockers": 0, "warnings": 0, "info": 0}),
        },
        "sources": sources,
    }
    evidence["fingerprint"] = _fingerprint(evidence)
    return evidence


_SENSITIVE_HINT = re.compile(
    r"account|ifsc|swift|aadhaar|aadhar|\bpan\b|passport|\bssn\b|password|token|secret|"
    r"@|\+\d{6,}|\bkey\b",
    re.IGNORECASE,
)


def _sanitise_message(message: str, employee) -> str:
    """Replace a full employee name with their code so names never leave
    in the evidence label, and strip anything that smells like a secret /
    contact detail (defence in depth — Preflight messages don't contain
    these, but free-form data must never be trusted)."""
    text = message or ""
    if employee is not None:
        full = f"{employee.first_name} {employee.last_name}".strip()
        if full:
            text = text.replace(full, _employee_ref(employee))
    if _SENSITIVE_HINT.search(text):
        return "(finding detail withheld)"
    return text


def _fingerprint(evidence: dict) -> str:
    canonical = json.dumps(
        {k: v for k, v in evidence.items() if k != "fingerprint"},
        sort_keys=True, default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# --------------------------------------------------------------------------
# Deterministic (non-AI) summary + fallback brief
# --------------------------------------------------------------------------
def deterministic_summary(evidence: dict) -> str:
    s = evidence["preflight"]["summary"]
    t = evidence["totals"]
    parts = [f"Payroll computed for {t['payslip_count']} employee(s); total net {t['net']['display']}."]
    if s["blockers"] or s["warnings"]:
        parts.append(
            f"{s['blockers']} blocker(s) and {s['warnings']} warning(s) require review "
            f"before validation."
        )
    else:
        parts.append("No blockers or warnings were detected.")
    return " ".join(parts)


def _fallback_items(evidence: dict) -> tuple[list[dict], list[dict]]:
    """Backend-generated attention/observation items straight from the
    source registry — used when the AI layer is unavailable. Deterministic,
    not AI, and labelled as such by the caller."""
    attention, observations = [], []
    for src in evidence["sources"]:
        if src["type"] == "PREFLIGHT" and src["severity"] in {"BLOCKER", "WARNING"}:
            attention.append({
                "title": src["code"].replace("_", " ").title(),
                "text": src["label"],
                "priority": src["severity"],
                "source_ids": [src["id"]],
            })
        elif src["type"] == "PAYROLL" and src["code"] in {"TOTAL_NET", "SCOPE"}:
            observations.append({
                "title": src["code"].replace("_", " ").title(),
                "text": src["label"],
                "source_ids": [src["id"]],
            })
        elif src["type"] == "SIMULATOR":
            observations.append({
                "title": "Simulation", "text": src["label"], "source_ids": [src["id"]],
            })
    attention.sort(key=lambda i: _SEVERITY_RANK.get(i["priority"], 9))
    return attention, observations


# --------------------------------------------------------------------------
# Provider call
# --------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are Payloom Intelligence. You convert verified payroll facts supplied by Payloom into a concise operational brief for a payroll professional.

Rules:
1. Use ONLY the supplied evidence and its sources. Do not use outside knowledge.
2. Never calculate payroll. Never invent, restate differently, or "correct" any number.
3. Never infer a missing reason. If evidence is insufficient, omit the point.
4. Never change a severity label. Severity is owned by Payloom.
5. Never recommend salary changes, compensation policy, or legal/tax conclusions. The strongest thing you may say is "review <finding> before validation" because Payloom already established that priority.
6. Every attention_item and observation MUST cite one or more supplied source ids in "source_ids". An item citing nothing, or an unknown id, will be discarded.
7. Keep it short: 1 summary sentence group, 2-6 attention items, 2-5 observations, a brief review order.
8. Respond with a JSON object only, no markdown fencing, matching exactly:
{"headline": "...", "summary": "...", "attention_items": [{"title": "...", "text": "...", "source_ids": ["..."]}], "observations": [{"title": "...", "text": "...", "source_ids": ["..."]}], "suggested_review_order": [{"title": "...", "text": "...", "source_ids": ["..."]}]}
"""


def _unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason}


def generate_brief(evidence: dict) -> dict:
    """Calls the active provider with the sanitised evidence. Returns
    either {"available": True, "parsed": {...}} or
    {"available": False, "reason": ...}. Never raises."""
    if not ai_provider.is_configured():
        return _unavailable("NOT_CONFIGURED")

    model_input = {
        "payrun": evidence["payrun"],
        "totals": {
            "gross": evidence["totals"]["gross"],
            "deductions": evidence["totals"]["deductions"],
            "net": evidence["totals"]["net"],
            "payslip_count": evidence["totals"]["payslip_count"],
            "computed_count": evidence["totals"]["computed_count"],
        },
        "preflight": evidence["preflight"],
        "sources": [
            {k: s[k] for k in ("id", "type", "code", "severity", "label", "detail", "employee_ref")}
            for s in evidence["sources"]
        ],
    }
    user_content = (
        "Produce the payroll brief for this verified evidence packet. "
        "Cite source ids for every attention item and observation.\n\n"
        f"{json.dumps(model_input, default=str)}"
    )

    try:
        text = ai_provider.complete_json(_SYSTEM_PROMPT, user_content, max_tokens=1400)
        parsed = json.loads(text)
    except ai_provider.ProviderError as exc:
        return _unavailable(exc.reason)
    except (ValueError, TypeError):
        return _unavailable("MALFORMED_RESPONSE")

    if not isinstance(parsed, dict):
        return _unavailable("MALFORMED_RESPONSE")
    return {"available": True, "parsed": parsed}


# --------------------------------------------------------------------------
# Validation — the grounding gate
# --------------------------------------------------------------------------
_MONEY_TOKEN = re.compile(r"[₹]\s?[\d,]+(?:\.\d+)?|\b\d[\d,]*\.\d{2}\b")


def _grounded_numbers(text: str, cited: list[dict], evidence: dict) -> bool:
    """Every ₹-figure / decimal-amount in `text` must appear verbatim in a
    cited source's label/detail or in the payrun totals (spec section 55).
    Percentages and plain integers (counts) are allowed through — those
    are formatting, not fabricated money."""
    haystack = " ".join(
        [s.get("label") or "" for s in cited] + [s.get("detail") or "" for s in cited]
    )
    for tk in ("net", "gross", "deductions"):
        m = evidence["totals"][tk]
        haystack += f" {m['display']} {m['raw']}"
    haystack_digits = re.sub(r"[,\s]", "", haystack)
    for token in _MONEY_TOKEN.findall(text):
        norm = re.sub(r"[₹,\s]", "", token)
        if norm and norm not in haystack_digits:
            return False
    return True


def _validate_items(raw_items, registry: dict[str, dict], evidence: dict) -> list[dict]:
    out = []
    if not isinstance(raw_items, list):
        return out
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        title = str(item.get("title", "")).strip() or "Note"
        ids = [i for i in item.get("source_ids", []) if isinstance(i, str)]
        cited = [registry[i] for i in ids if i in registry]
        if not cited:
            # Section 14 / 52 / 54: an item that cannot be grounded is dropped.
            continue
        if not _grounded_numbers(text, cited, evidence):
            continue
        # Section 18 / 53: severity is the deterministic max of the cited
        # sources — never whatever the model wrote.
        severities = [c["severity"] for c in cited if c.get("severity")]
        priority = min(severities, key=lambda s: _SEVERITY_RANK.get(s, 9)) if severities else None
        primary = cited[0]
        out.append({
            "title": title[:120],
            "text": text[:600],
            "priority": priority,
            "source_ids": [c["id"] for c in cited],
            "source_type": primary["type"],
            "source_code": primary["code"],
            "source_ref": primary.get("employee_ref"),
            "route": primary.get("route"),
        })
    return out


def _build_response(payrun: Payrun, evidence: dict, *, ai: Optional[dict], reason: Optional[str]) -> dict:
    registry = {s["id"]: s for s in evidence["sources"]}
    det_summary = deterministic_summary(evidence)
    base = {
        "payrun_id": payrun.id,
        "reference": payrun.reference,
        "period": evidence["payrun"]["period"],
        "status": payrun.status.value,
        "sources": evidence["sources"],
        "deterministic_summary": det_summary,
        "generated_at": datetime.now(timezone.utc),
        "evidence_fingerprint": evidence["fingerprint"],
        "provider": ai_provider.active_provider_name(),
    }

    if ai is None:
        attention, observations = _fallback_items(evidence)
        review = sorted(
            [dict(i, source_type="PREFLIGHT") for i in attention],
            key=lambda i: _SEVERITY_RANK.get(i.get("priority"), 9),
        )
        return {
            **base,
            "available": False,
            "reason": reason,
            "is_fallback": True,
            "headline": f"{payrun.reference} — payroll brief",
            "summary": det_summary,
            "attention_items": attention,
            "observations": observations,
            "suggested_review_order": review,
        }

    parsed = ai
    attention = _validate_items(parsed.get("attention_items"), registry, evidence)
    observations = _validate_items(parsed.get("observations"), registry, evidence)
    review = _validate_items(parsed.get("suggested_review_order"), registry, evidence)
    review.sort(key=lambda i: _SEVERITY_RANK.get(i.get("priority"), 9))

    # "Needs Attention" means an actual BLOCKER/WARNING finding. If the model
    # files a severity-less item (a payroll total, an INFO note) there, move
    # it to Observations — the deterministic severity decides placement, not
    # the model's choice of bucket.
    demoted = [i for i in attention if i.get("priority") not in ("BLOCKER", "WARNING")]
    attention = [i for i in attention if i.get("priority") in ("BLOCKER", "WARNING")]
    attention.sort(key=lambda i: _SEVERITY_RANK.get(i.get("priority"), 9))
    observations = demoted + observations

    headline = str(parsed.get("headline") or f"{payrun.reference} — payroll brief")[:160]
    summary = str(parsed.get("summary") or det_summary).strip()[:1200]
    return {
        **base,
        "available": True,
        "reason": None,
        "is_fallback": False,
        "headline": headline,
        "summary": summary,
        "attention_items": attention,
        "observations": observations,
        "suggested_review_order": review,
    }


def run(db: Session, payrun: Payrun, simulator_scenario: Optional[dict] = None) -> dict:
    """Orchestrator for the brief endpoint. Deterministic evidence first,
    then the AI layer on top; any AI failure falls back to a
    backend-generated deterministic brief. Never raises, never persists."""
    if payrun.status == PayrunStatus.DRAFT:
        now = datetime.now(timezone.utc)
        return {
            "available": False, "reason": "NOT_COMPUTED", "is_fallback": True, "provider": None,
            "payrun_id": payrun.id, "reference": payrun.reference,
            "period": {"start": payrun.period_start.isoformat(), "end": payrun.period_end.isoformat()},
            "status": payrun.status.value,
            "headline": None, "summary": "Compute this Payrun before generating a payroll brief.",
            "attention_items": [], "observations": [], "suggested_review_order": [],
            "sources": [], "deterministic_summary": "Payrun not yet computed.",
            "generated_at": now, "evidence_fingerprint": "",
        }

    evidence = build_brief_evidence(db, payrun, simulator_scenario)
    ai_result = generate_brief(evidence)
    if ai_result.get("available"):
        return _build_response(payrun, evidence, ai=ai_result["parsed"], reason=None)
    return _build_response(payrun, evidence, ai=None, reason=ai_result.get("reason"))
