"""Payloom Intelligence (Phase 10) — the grounded AI payroll brief.

Read-only by construction: this module builds a sanitised evidence
packet from the deterministic engines (Preflight, payrun totals,
optionally a just-run Simulator scenario), asks the AI provider to
communicate it, validates every claim against the evidence's source
registry, and returns the brief. Nothing here writes to any payroll
table, and the endpoint works (with a deterministic fallback) even when
no AI provider is configured. See app/services/intelligence.py.

RBAC (spec section 44): same visibility as Payrun operations —
HR_PAYROLL_USER / HR_PAYROLL_MANAGER / ADMIN. EMPLOYEE and HR_MANAGER
must not reach a Payrun-level brief.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_payroll_operator
from app.db.database import get_db
from app.models.payroll import Payrun
from app.models.user import User
from app.schemas.intelligence import PayrollBriefResponse
from app.services import intelligence

router = APIRouter()


class SimulatorScenarioIn(BaseModel):
    """Optional — a scenario the user *just* ran in the Simulator and chose
    to attach. Simulator results are ephemeral; this is passed through by
    the client, never stored, and only its already-computed display
    strings are used (spec sections 22-23)."""
    description: Optional[str] = None
    assumption: Optional[str] = None
    aggregate_net_delta_display: Optional[str] = None
    annualized_note: Optional[str] = None
    employees_simulated: Optional[int] = None


class PayrollBriefRequest(BaseModel):
    simulator_scenario: Optional[SimulatorScenarioIn] = None


@router.post("/payroll/payruns/{payrun_id}/intelligence/brief", response_model=PayrollBriefResponse)
def generate_payroll_brief(
    payrun_id: int,
    body: Optional[PayrollBriefRequest] = None,
    db: Session = Depends(get_db),
    current_operator: User = Depends(get_current_payroll_operator),
):
    payrun = db.query(Payrun).filter(Payrun.id == payrun_id).first()
    if not payrun:
        raise HTTPException(404, detail={"error": {"code": "NOT_FOUND", "message": "Payrun not found."}})

    scenario = None
    if body and body.simulator_scenario:
        scenario = body.simulator_scenario.model_dump(exclude_none=True)

    return intelligence.run(db, payrun, simulator_scenario=scenario)
