"""PayTrace AI Narrator (Phase 7B) — OPTIONAL plain-language explanation
layer over the verified deterministic PayTrace (see app/services/paytrace.py).

This is an enhancement, never a dependency. Every failure path — no API
key configured, network error, timeout, rate limit, malformed model
output — degrades to `{"available": False}` rather than raising. The
deterministic /trace endpoint doesn't call this module at all, so its
correctness is never affected by anything here.

Fact integrity (mandatory, see Phase 7 spec invariants 6-7): the model
receives ONLY the already-computed, verified trace — rule codes,
categories, methods, percentages/formula text, amounts, period, and the
employee's first name. It never gets raw DB access, PII beyond that
first name, or any ability to compute payroll. Its JSON output is
explanatory copy only: components are filtered post-hoc against the set
of rule codes that actually exist in the trace, so the model cannot
introduce a reference to a calculation that never happened, and nothing
it returns is ever written back as an authoritative numeric field.
"""
import json
from typing import Literal
from app.services import ai_provider

_SYSTEM_PROMPT = """You explain payroll calculations in clear, plain language.

Use only the verified payroll trace data provided to you. Do not perform new payroll calculations. Do not invent reasons, deductions, tax rules, attendance effects, leave effects, or company policies not present in the data. Do not change, restate differently, or "correct" any number — repeat amounts exactly as given.

If information referenced in the trace is missing or unclear, say it is not available rather than guessing.

Keep the explanation concise (3-6 sentences) and factual. Respond with a JSON object only, no markdown fencing, matching exactly this shape:
{"summary": "...", "components": [{"rule_code": "...", "explanation": "..."}]}
"""


def _sanitize_trace_for_ai(trace: dict, mode: str) -> dict:
    """Minimum necessary data only: first name, not employee_code/id;
    no contract reference or currency details beyond what's already in
    each entry's calculation."""
    first_name = trace["employee"]["name"].split(" ")[0]
    return {
        "employee_first_name": first_name,
        "period": trace["period"],
        "salary_structure": trace["salary_structure"]["name"],
        "mode": mode,
        "entries": [
            {
                "sequence": e["sequence"],
                "rule_name": e["rule_name"],
                "rule_code": e["rule_code"],
                "category": e["category"],
                "method": e["method"],
                "result": e["result"],
                "calculation": e["calculation"],
                "explanation": e["explanation"],
            }
            for e in trace["entries"]
        ],
        "aggregates": trace["aggregates"],
    }


def _unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason, "summary": None, "components": None}


def explain(trace: dict, mode: Literal["employee", "payroll"] = "employee") -> dict:
    """Returns {available, reason, summary, components}. Never raises."""
    if not ai_provider.is_configured():
        return _unavailable("NOT_CONFIGURED")

    sanitized = _sanitize_trace_for_ai(trace, mode)
    persona = (
        "Explain this for the employee reading their own payslip: simple, warm, no jargon."
        if mode == "employee"
        else "Explain this for a payroll professional auditing the calculation: precise and technical, referencing rule codes and sequence."
    )
    user_content = f"{persona}\n\nVerified payroll trace (JSON):\n{json.dumps(sanitized, default=str)}"

    try:
        text = ai_provider.complete_json(_SYSTEM_PROMPT, user_content, max_tokens=700)
        parsed = json.loads(text)
    except ai_provider.ProviderError as exc:
        return _unavailable(exc.reason)
    except (ValueError, TypeError):
        return _unavailable("MALFORMED_RESPONSE")

    summary = parsed.get("summary") if isinstance(parsed, dict) else None
    if not isinstance(summary, str) or not summary.strip():
        return _unavailable("MALFORMED_RESPONSE")

    raw_components = parsed.get("components")
    known_codes = {e["rule_code"] for e in trace["entries"]}
    components = [
        {"rule_code": c.get("rule_code"), "explanation": str(c.get("explanation", ""))[:600]}
        for c in (raw_components if isinstance(raw_components, list) else [])
        if isinstance(c, dict) and c.get("rule_code") in known_codes
    ]

    return {"available": True, "reason": None, "summary": summary.strip()[:2000], "components": components}
