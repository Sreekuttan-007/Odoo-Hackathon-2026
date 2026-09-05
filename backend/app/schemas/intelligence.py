"""Payloom Intelligence (Phase 10) — request/response schemas for the
grounded AI payroll brief.

The brief is an EXPLANATION layer. Nothing in this module (or the
service / route behind it) ever writes to any payroll table, and no
number a model returns is ever treated as authoritative — every
displayed figure originates in the deterministic evidence packet the
backend built, and every displayed statement is validated against that
packet's source registry before it reaches this response.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class BriefSource(BaseModel):
    """One deterministic fact the AI is allowed to cite. Generated
    backend-side from Preflight / payroll totals / Simulator output; the
    model may only reference `id`s that appear here."""
    id: str
    type: str          # PAYROLL | PREFLIGHT | SIMULATOR
    code: str
    severity: Optional[str] = None   # BLOCKER | WARNING | INFO — owned by the backend
    label: str
    detail: Optional[str] = None
    employee_ref: Optional[str] = None
    route: Optional[str] = None      # a real in-app route, or None


class BriefItem(BaseModel):
    title: str
    text: str
    priority: Optional[str] = None   # normalised to the cited source's deterministic severity
    source_ids: List[str] = []
    source_type: Optional[str] = None
    source_code: Optional[str] = None
    source_ref: Optional[str] = None
    route: Optional[str] = None


class PayrollBriefResponse(BaseModel):
    available: bool
    reason: Optional[str] = None          # NOT_CONFIGURED | TIMEOUT | PROVIDER_ERROR | RATE_LIMITED | MALFORMED_RESPONSE | NOT_COMPUTED
    is_fallback: bool = False             # True => headline/summary are backend-generated, not AI
    provider: Optional[str] = None

    payrun_id: int
    reference: str
    period: dict
    status: str

    headline: Optional[str] = None
    summary: Optional[str] = None
    attention_items: List[BriefItem] = []
    observations: List[BriefItem] = []
    suggested_review_order: List[BriefItem] = []

    sources: List[BriefSource] = []
    deterministic_summary: str            # always present — the non-AI one-liner

    generated_at: datetime
    evidence_fingerprint: str
