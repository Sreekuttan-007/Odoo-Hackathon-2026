# ATTENDANCE RULES — PeoplePay360

## Worked Hours Calculation

For a completed attendance record:

```
worked_hours = (check_out - check_in) - applicable_break
```

`applicable_break` for MVP is derived from the employee's WorkingSchedule line
for that day of week (its `break_duration_minutes`), not re-entered per
attendance record. If no schedule line exists for that day (e.g. a weekend
check-in), break defaults to 0 and the record is flagged (see Status table).

If `check_out` is null, `worked_hours` is null and status is `MISSING_CHECK_OUT`
(see below) — it is never guessed or defaulted to a full day.

## Status Derivation

Status is computed, not manually chosen, from comparing the attendance record
against the employee's WorkingSchedule line for that date:

| Condition | Status |
|---|---|
| `check_in` is null (no record for a scheduled work day) | `ABSENT` |
| `check_out` is null and it is not still the same day/session | `MISSING_CHECK_OUT` |
| `check_in` later than the schedule line's `start_time` (+ grace, e.g. 0 min MVP) | `LATE` |
| `worked_hours` > the schedule line's expected duration (+ tolerance) | `OVERTIME` |
| Otherwise, within expected schedule | `PRESENT` |

A record can conceptually satisfy more than one condition (e.g. late AND
overtime); MVP stores a single primary `status` chosen by the above priority
order (`MISSING_CHECK_OUT` > `ABSENT` > `LATE` > `OVERTIME` > `PRESENT`), and
this ordering is deliberately simple — not a scoring system per section 0.11's
instruction to avoid excessive complexity.

## Corrections (0.12)

Only `HR_MANAGER` and above may edit another employee's attendance. An
employee may create their own check-in/out but not retroactively edit a past
record's times (that requires HR correction).

On correction, set:
- `manually_edited = true`
- `corrected_by = <acting user id>`
- `corrected_at = now()`
- `correction_reason` (free text, required)
- recompute `worked_hours` and `status` from the new values

This is the entire audit trail for MVP — no separate audit-log table, no
before/after diff history. Sufficient to answer "was this touched, by whom,
why" without building a generic auditing subsystem.

## Relationship to Payroll (0.11, non-goal note)

Attendance feeds `calculateWorkedDays()` in the payroll engine (worked days /
absences within the payroll period), and feeds dashboard attendance-health
metrics. It does **not** itself compute pay for overtime/lateness in MVP —
that would require a paid-overtime salary rule, which is explicitly deferred
(see REQUIREMENTS.md ambiguity #5). Attendance in MVP answers "did they work,
roughly how much, and were there exceptions" — not "calculate shift differential
pay."
