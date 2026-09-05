# Payloom — Demo Checklist (Phase 12)

Everything below is verified against the live Neon (Singapore) database. Commands assume
the backend is on `http://localhost:8000` and you have `curl` + `python` on PATH.

---

## T‑minus 30 minutes

**Infrastructure**
- [ ] Internet is stable (Gemini + Neon both need it).
- [ ] Neon project is awake — hit `GET http://localhost:8000/api/health` twice (first call wakes a cold Neon compute, ~6 s).
- [ ] Backend running: `cd backend && venv/Scripts/python -m uvicorn app.main:app --port 8000` → `{"status":"ok"}`.
- [ ] Frontend running: `cd frontend && npm run dev` → `http://localhost:5173` returns 200.
- [ ] `.env` has `AI_PROVIDER=gemini` and a **non-empty** `GEMINI_API_KEY`.
- [ ] AI smoke test — see **Arm the AI** below. If it fails, the demo runs on the deterministic fallback (still fine — see script fallback).

**Demo data (all against `admin@payloom.local` / `admin123`)**

Get a token once:
```bash
BASE=http://localhost:8000/api
T=$(curl -s -X POST $BASE/auth/login -H 'Content-Type: application/json' \
    -d '{"email":"admin@payloom.local","password":"admin123"}' \
    | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $T"
```

- [ ] **Payruns exist and are in the right state:**
  ```bash
  curl -s $BASE/payroll/payruns -H "$AUTH" \
    | python -c "import sys,json;[print(p['id'],p['reference'],p['status'],p['period_start'],p['period_end']) for p in json.load(sys.stdin)]"
  ```
  Expected:
  | id | reference | status | period |
  |----|-----------|--------|--------|
  | 5 | PR/2026/0005 | **DRAFT** | 2026‑12‑01 → 2026‑12‑31 (Dave) |
  | 4 | PR/2026/0004 | **COMPUTED** | 2026‑10‑01 → 2026‑10‑31 (Dave) |
  | 3 | PR/2026/0003 | **COMPUTED** | 2026‑09‑01 → 2026‑09‑30 (Dave, ₹29,500) |
  | 2 | PR/2026/0002 | PAID | 2026‑08 (Aarav) |
  | 1 | PR/2026/0001 | PAID | 2026‑02 (Aarav + Dave) |

  If **PR/2026/0005** is missing or not DRAFT, recreate it:
  ```bash
  curl -s -X POST $BASE/payroll/payruns -H "$AUTH" -H 'Content-Type: application/json' \
    -d '{"salary_structure_id":1,"period_start":"2026-12-01","period_end":"2026-12-31","employee_ids":[4]}' \
    | python -m json.tool
  ```
  (Then delete any leftover DRAFT dupes from earlier rehearsals via the Neon SQL console:
  `DELETE FROM payslips WHERE payrun_id IN (SELECT id FROM payruns WHERE reference > 'PR/2026/0005'); DELETE FROM payruns WHERE reference > 'PR/2026/0005';`)

- [ ] **PR/2026/0004 is DISARMED and clean:**
  ```bash
  curl -s -X PATCH $BASE/contracts/$(curl -s "$BASE/contracts?employee_id=4" -H "$AUTH" | python -c "import sys,json;print([c['id'] for c in json.load(sys.stdin) if c['end_date'] is None][0])") \
    -H "$AUTH" -H 'Content-Type: application/json' -d '{"end_date":null}' > /dev/null
  curl -s -X POST $BASE/payroll/payruns/4/compute -H "$AUTH" > /dev/null
  curl -s $BASE/payroll/payruns/4/preflight -H "$AUTH" \
    | python -c "import sys,json;print('PR0004 readiness:', json.load(sys.stdin)['readiness'])"   # expect READY
  ```

- [ ] **PR/2026/0003 Preflight → READY** (the safety-net for the Preflight segment):
  ```bash
  curl -s $BASE/payroll/payruns/3/preflight -H "$AUTH" \
    | python -c "import sys,json;print(json.load(sys.stdin)['readiness'])"   # expect READY
  ```

- [ ] **Simulator canonical scenario works** (Dave, Nov 2026 — a period with no Payslip for Dave):
  ```bash
  curl -s -X POST $BASE/payroll/simulator/run -H "$AUTH" -H 'Content-Type: application/json' \
    -d '{"salary_structure_id":1,"period_start":"2026-11-01","period_end":"2026-11-30","employee_ids":[4],"rule_overrides":[{"rule_id":2,"percentage":"25.00"}]}' \
    | python -c "import sys,json;d=json.load(sys.stdin);e=d['employees'][0];print('excluded' if e['excluded'] else f\"{e['current']['net']} -> {e['simulated']['net']}  delta {e['delta_net']}\")"
  ```
  Expect `29500.00 -> 30750.00  delta 1250.00`. If it says `excluded` (`DUPLICATE_PAYSLIP`), pick a later month in the demo.

- [ ] **PDF renders:** open `http://localhost:8000/api/payroll/payslips/1/pdf` in the browser (Aarav, PAID) — a PDF should display.

**Rule id reference** (structure 1 "Regular Salary"): `1 BASIC` · `2 HRA` · `3 ALLOWANCE` · `4 GROSS` · `5 PF` · `6 NET`. Confirm HRA is id 2:
```bash
curl -s "$BASE/payroll/rules?salary_structure_id=1" -H "$AUTH" | python -c "import sys,json;print({r['code']:r['id'] for r in json.load(sys.stdin)})"
```

---

## Arm the AI (T‑minus 15 min)

```bash
curl -s -X POST $BASE/payroll/payruns/3/intelligence/brief -H "$AUTH" -H 'Content-Type: application/json' -d '{}' \
  | python -c "import sys,json;d=json.load(sys.stdin);print('available:',d['available'],'| provider:',d['provider'],'| reason:',d['reason'])"
```
- `available: True, provider: gemini` → AI path is live. Good.
- `available: False, reason: NOT_CONFIGURED` → key not loaded; check `.env`, restart backend.
- `available: False, reason: PROVIDER_ERROR / TIMEOUT` → provider/network issue; **the demo still works** on the deterministic fallback. Use the script's Intelligence fallback line.

---

## Arm the Preflight blocker (T‑minus 2 min, optional but recommended)

This makes **PR/2026/0004** show a live `MISSING_APPLICABLE_CONTRACT` blocker. It is one reversible PATCH — Dave's current contract gets an `end_date` of `2026‑09‑30`, so his October Payrun has no applicable contract.

**ARM:**
```bash
CID=$(curl -s "$BASE/contracts?employee_id=4" -H "$AUTH" | python -c "import sys,json;print([c['id'] for c in json.load(sys.stdin) if c['end_date'] is None][0])")
curl -s -X PATCH $BASE/contracts/$CID -H "$AUTH" -H 'Content-Type: application/json' -d '{"end_date":"2026-09-30"}' > /dev/null
curl -s $BASE/payroll/payruns/4/preflight -H "$AUTH" | python -c "import sys,json;d=json.load(sys.stdin);print(d['readiness'], [f['code'] for f in d['findings']])"
# expect: ACTION_REQUIRED ['MISSING_APPLICABLE_CONTRACT']
```

**DISARM (immediately after the demo):**
```bash
curl -s -X PATCH $BASE/contracts/$CID -H "$AUTH" -H 'Content-Type: application/json' -d '{"end_date":null}' > /dev/null
curl -s -X POST $BASE/payroll/payruns/4/compute -H "$AUTH" > /dev/null   # rebuild the clean snapshot
```

> Armed state is safe: it does not affect PR/2026/0003 (Sept still overlaps `2026‑09‑30`), PR/2026/0001/0002 (PAID, snapshot-stable), or the Simulator (Nov period, contract dates don't matter for a period that ends before Oct). It only makes PR/2026/0004's October period contract‑less.

---

## T‑minus 5 minutes

- [ ] Restart backend + frontend one last time; re-check `/api/health` and `:5173`.
- [ ] Log in as `admin@payloom.local` in the demo browser; land on `/dashboard`.
- [ ] Close every other browser tab. Hide the terminal / editor.
- [ ] Browser zoom **100–110%**; OS notifications **off**; screen-share the right window.
- [ ] Open tabs in order (or bookmark): `/dashboard` · `/employees/4` · `/payroll/salary-structures/1` · `/payroll/payruns` · `/payroll/simulator`.
- [ ] Run the **Arm the AI** check once more — confirm `available: True`.
- [ ] Arm the Preflight blocker (above).
- [ ] Have `JUDGE_QA.md` open on a second device.
- [ ] Role accounts ready in case RBAC is questioned: `hr@payloom.local`/`hr123` (HR_MANAGER — no payroll), `employee@payloom.local`/`employee123` (EMPLOYEE — own data only).

---

## During the demo

- No code editing. No long typing. No live department/rule creation.
- If a click fails: use the segment's **Fallback** in `FINAL_DEMO_SCRIPT.md`, or navigate directly to a known route. Recover calmly, don't narrate the error.
- Don't apologize for deliberate scope boundaries (no tax engine, no bank rails, attendance-as-context). State them as design decisions.
- If you don't know an answer: say so. Don't bluff. Don't argue with judges.

---

## After the demo

- [ ] **Disarm the Preflight blocker** (PATCH `end_date` back to `null` + recompute PR/2026/0004).
- [ ] Optionally delete rehearsal-created Payruns above `PR/2026/0005` (Neon SQL console).
- [ ] Leave `PR/2026/0005` as PAID if you walked it through — or reset it to DRAFT for the next run:
  Neon SQL console: `UPDATE payruns SET status='DRAFT', computed_at=NULL, validated_at=NULL, validated_by_user_id=NULL, paid_at=NULL, paid_by_user_id=NULL WHERE reference='PR/2026/0005'; UPDATE payslips SET status='DRAFT', computed_at=NULL, validated_at=NULL, paid_at=NULL, basic=0, allowances=0, gross=0, deductions=0, net=0, warning_count=0 WHERE payrun_id=5; DELETE FROM payslip_lines WHERE payslip_id IN (SELECT id FROM payslips WHERE payrun_id=5); DELETE FROM payroll_warnings WHERE payslip_id IN (SELECT id FROM payslips WHERE payrun_id=5);`
