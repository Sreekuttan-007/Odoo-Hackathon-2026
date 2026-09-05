from tests.conftest import auth_headers
from datetime import date, time
from app.models.working_schedule import WorkingSchedule, WorkingScheduleLine, ScheduleStatus, DayOfWeek
from app.models.user import User


def _give_schedule(db_session, employee_id):
    schedule = WorkingSchedule(name="40 Hours / Week", status=ScheduleStatus.ACTIVE)
    db_session.add(schedule)
    db_session.flush()
    for day in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]:
        db_session.add(WorkingScheduleLine(working_schedule_id=schedule.id, day_of_week=day, start_time=time(9, 0), end_time=time(18, 0), break_minutes=60))
    db_session.commit()
    from app.models.employee import Employee
    employee = db_session.query(Employee).filter(Employee.id == employee_id).first()
    employee.working_schedule_id = schedule.id
    db_session.commit()


def _employee_id_for(db_session, email):
    user = db_session.query(User).filter(User.work_email == email).first()
    return user.employee_id


def _create_type(client, hr_token, **overrides):
    payload = {
        "name": "Paid Time Off", "code": "PTO", "unit": "DAYS",
        "requires_allocation": True, "approval_policy": "MANAGER", "is_active": True,
    }
    payload.update(overrides)
    res = client.post("/api/time-off/types", json=payload, headers=auth_headers(hr_token))
    assert res.status_code == 200, res.text
    return res.json()


def _create_allocation(client, hr_token, employee_id, type_id, allocated_amount=20, valid_from="2026-01-01", valid_to="2026-12-31"):
    res = client.post(
        "/api/time-off/allocations",
        json={"employee_id": employee_id, "time_off_type_id": type_id, "allocated_amount": allocated_amount, "valid_from": valid_from, "valid_to": valid_to},
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 200, res.text
    return res.json()


def _approve_allocation(client, hr_token, allocation_id):
    res = client.post(f"/api/time-off/allocations/{allocation_id}/approve", headers=auth_headers(hr_token))
    assert res.status_code == 200, res.text
    return res.json()


class TestTimeOffTypes:
    def test_create_and_list_type(self, client, hr_token):
        _create_type(client, hr_token)
        res = client.get("/api/time-off/types", headers=auth_headers(hr_token))
        assert res.status_code == 200
        assert any(t["code"] == "PTO" for t in res.json())

    def test_employee_cannot_create_type(self, client, employee_token):
        res = client.post(
            "/api/time-off/types",
            json={"name": "Paid Time Off", "unit": "DAYS", "requires_allocation": True, "approval_policy": "MANAGER"},
            headers=auth_headers(employee_token),
        )
        assert res.status_code == 403

    def test_unit_change_blocked_once_referenced(self, client, hr_token, employee_token, db_session):
        type_ = _create_type(client, hr_token)
        _give_schedule(db_session, _employee_id_for(db_session, "employee-test@payloom.local"))
        allocation = _create_allocation(client, hr_token, _employee_id_for(db_session, "employee-test@payloom.local"), type_["id"])
        res = client.patch(f"/api/time-off/types/{type_['id']}", json={"unit": "HOURS"}, headers=auth_headers(hr_token))
        assert res.status_code == 409
        assert res.json()["detail"]["error"]["code"] == "UNIT_LOCKED"


class TestAllocations:
    def test_pending_allocation_gives_no_balance(self, client, hr_token, employee_token, db_session):
        type_ = _create_type(client, hr_token)
        employee_id = _employee_id_for(db_session, "employee-test@payloom.local")
        allocation = _create_allocation(client, hr_token, employee_id, type_["id"])
        assert allocation["status"] == "TO_APPROVE"
        assert allocation["remaining_amount"] == "0"

    def test_approve_allocation_creates_balance(self, client, hr_token, employee_token, db_session):
        type_ = _create_type(client, hr_token)
        employee_id = _employee_id_for(db_session, "employee-test@payloom.local")
        allocation = _create_allocation(client, hr_token, employee_id, type_["id"], allocated_amount=20)
        approved = _approve_allocation(client, hr_token, allocation["id"])
        assert approved["status"] == "APPROVED"
        assert approved["remaining_amount"] == "20.00"

    def test_refused_allocation_gives_no_balance(self, client, hr_token, employee_token, db_session):
        type_ = _create_type(client, hr_token)
        employee_id = _employee_id_for(db_session, "employee-test@payloom.local")
        allocation = _create_allocation(client, hr_token, employee_id, type_["id"])
        res = client.post(f"/api/time-off/allocations/{allocation['id']}/refuse", headers=auth_headers(hr_token))
        assert res.status_code == 200
        assert res.json()["status"] == "REFUSED"
        assert res.json()["remaining_amount"] == "0"

    def test_overlapping_approved_allocation_rejected(self, client, hr_token, employee_token, db_session):
        type_ = _create_type(client, hr_token)
        employee_id = _employee_id_for(db_session, "employee-test@payloom.local")
        a1 = _create_allocation(client, hr_token, employee_id, type_["id"])
        _approve_allocation(client, hr_token, a1["id"])
        a2 = _create_allocation(client, hr_token, employee_id, type_["id"], valid_from="2026-06-01", valid_to="2026-06-30")
        res = client.post(f"/api/time-off/allocations/{a2['id']}/approve", headers=auth_headers(hr_token))
        assert res.status_code == 409
        assert res.json()["detail"]["error"]["code"] == "ALLOCATION_OVERLAP"

    def test_employee_cannot_create_allocation(self, client, employee_token):
        res = client.post(
            "/api/time-off/allocations",
            json={"employee_id": 1, "time_off_type_id": 1, "allocated_amount": 10, "valid_from": "2026-01-01", "valid_to": "2026-12-31"},
            headers=auth_headers(employee_token),
        )
        assert res.status_code == 403


class TestRequests:
    def _setup(self, client, hr_token, db_session, requires_allocation=True, allocated=20):
        type_ = _create_type(client, hr_token, requires_allocation=requires_allocation)
        employee_id = _employee_id_for(db_session, "employee-test@payloom.local")
        _give_schedule(db_session, employee_id)
        if requires_allocation:
            allocation = _create_allocation(client, hr_token, employee_id, type_["id"], allocated_amount=allocated)
            _approve_allocation(client, hr_token, allocation["id"])
        return type_, employee_id

    def test_request_duration_computed_from_schedule(self, client, hr_token, employee_token, db_session):
        type_, _ = self._setup(client, hr_token, db_session)
        res = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-05", "end_date": "2026-01-09", "reason": "Trip"},
            headers=auth_headers(employee_token),
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["duration_amount"] == "5.00"
        assert body["status"] == "TO_APPROVE"

    def test_no_allocation_rejected(self, client, hr_token, employee_token, db_session):
        type_ = _create_type(client, hr_token, requires_allocation=True)
        employee_id = _employee_id_for(db_session, "employee-test@payloom.local")
        _give_schedule(db_session, employee_id)
        res = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-05", "end_date": "2026-01-06"},
            headers=auth_headers(employee_token),
        )
        assert res.status_code == 404
        assert res.json()["detail"]["error"]["code"] == "NO_ALLOCATION"

    def test_insufficient_balance_rejected(self, client, hr_token, employee_token, db_session):
        type_, _ = self._setup(client, hr_token, db_session, allocated=2)
        res = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-05", "end_date": "2026-01-09"},
            headers=auth_headers(employee_token),
        )
        assert res.status_code == 409
        assert res.json()["detail"]["error"]["code"] == "INSUFFICIENT_BALANCE"

    def test_no_allocation_required_path_works(self, client, hr_token, employee_token, db_session):
        type_, _ = self._setup(client, hr_token, db_session, requires_allocation=False)
        res = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-05", "end_date": "2026-01-05"},
            headers=auth_headers(employee_token),
        )
        assert res.status_code == 200, res.text
        assert res.json()["allocation_id"] is None

    def test_overlapping_request_rejected(self, client, hr_token, employee_token, db_session):
        type_, _ = self._setup(client, hr_token, db_session)
        client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-05", "end_date": "2026-01-07"},
            headers=auth_headers(employee_token),
        )
        res = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-07", "end_date": "2026-01-08"},
            headers=auth_headers(employee_token),
        )
        assert res.status_code == 409
        assert res.json()["detail"]["error"]["code"] == "REQUEST_OVERLAP"

    def test_inactive_type_rejected(self, client, hr_token, employee_token, db_session):
        type_, _ = self._setup(client, hr_token, db_session, requires_allocation=False)
        client.patch(f"/api/time-off/types/{type_['id']}", json={"is_active": False}, headers=auth_headers(hr_token))
        res = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-05", "end_date": "2026-01-05"},
            headers=auth_headers(employee_token),
        )
        assert res.status_code == 400
        assert res.json()["detail"]["error"]["code"] == "TYPE_INACTIVE"

    def test_full_approval_consumes_balance_exactly_once(self, client, hr_token, employee_token, db_session):
        # Mirrors the Phase 4 spec's canonical balance test (section 73):
        # 20 allocated, 5 already approved elsewhere, new request of 3 ->
        # remaining 15 before approval, 12 after; re-approving must not
        # double-deduct.
        type_, employee_id = self._setup(client, hr_token, db_session, allocated=20)

        prior = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-05", "end_date": "2026-01-09"},
            headers=auth_headers(employee_token),
        ).json()
        client.post(f"/api/time-off/requests/{prior['id']}/approve", headers=auth_headers(hr_token))

        new_request = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-12", "end_date": "2026-01-14"},
            headers=auth_headers(employee_token),
        ).json()
        assert new_request["duration_amount"] == "3.00"

        res = client.post(f"/api/time-off/requests/{new_request['id']}/approve", headers=auth_headers(hr_token))
        assert res.status_code == 200, res.text
        assert res.json()["balance"]["remaining"] == "12.00"

        # Duplicate approval must fail, not double-deduct.
        res = client.post(f"/api/time-off/requests/{new_request['id']}/approve", headers=auth_headers(hr_token))
        assert res.status_code == 409
        assert res.json()["detail"]["error"]["code"] == "ALREADY_DECIDED"

        allocation_res = client.get(f"/api/time-off/allocations/{new_request['allocation_id']}", headers=auth_headers(hr_token))
        assert allocation_res.json()["remaining_amount"] == "12.00"

    def test_refused_request_consumes_nothing(self, client, hr_token, employee_token, db_session):
        type_, employee_id = self._setup(client, hr_token, db_session, allocated=20)
        req = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-05", "end_date": "2026-01-09"},
            headers=auth_headers(employee_token),
        ).json()
        res = client.post(f"/api/time-off/requests/{req['id']}/refuse", headers=auth_headers(hr_token))
        assert res.status_code == 200
        assert res.json()["status"] == "REFUSED"
        allocation_res = client.get(f"/api/time-off/allocations/{req['allocation_id']}", headers=auth_headers(hr_token))
        assert allocation_res.json()["remaining_amount"] == "20.00"

    def test_employee_cannot_approve_own_request(self, client, hr_token, employee_token, db_session):
        type_, _ = self._setup(client, hr_token, db_session, requires_allocation=False)
        # employee_token's role is EMPLOYEE so get_current_hr already blocks this
        req = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-05", "end_date": "2026-01-05"},
            headers=auth_headers(employee_token),
        ).json()
        res = client.post(f"/api/time-off/requests/{req['id']}/approve", headers=auth_headers(employee_token))
        assert res.status_code == 403

    def test_hr_manager_cannot_approve_their_own_request(self, client, hr_token, db_session):
        type_ = _create_type(client, hr_token, requires_allocation=False)
        employee_id = _employee_id_for(db_session, "hr-test@payloom.local")
        _give_schedule(db_session, employee_id)
        req = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-05", "end_date": "2026-01-05"},
            headers=auth_headers(hr_token),
        ).json()
        res = client.post(f"/api/time-off/requests/{req['id']}/approve", headers=auth_headers(hr_token))
        assert res.status_code == 403
        assert res.json()["detail"]["error"]["code"] == "SELF_APPROVAL"

    def test_employee_cannot_view_others_requests(self, client, hr_token, employee_token, db_session):
        type_ = _create_type(client, hr_token, requires_allocation=False)
        employee_id = _employee_id_for(db_session, "hr-test@payloom.local")
        _give_schedule(db_session, employee_id)
        req = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-05", "end_date": "2026-01-05"},
            headers=auth_headers(hr_token),
        ).json()
        res = client.get(f"/api/time-off/requests/{req['id']}", headers=auth_headers(employee_token))
        assert res.status_code == 403

    def test_employee_list_only_returns_own_requests(self, client, hr_token, employee_token, db_session):
        type_, employee_id = self._setup(client, hr_token, db_session, requires_allocation=False)
        client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "start_date": "2026-01-05", "end_date": "2026-01-05"},
            headers=auth_headers(employee_token),
        )
        client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "employee_id": _employee_id_for(db_session, "hr-test@payloom.local"), "start_date": "2026-02-05", "end_date": "2026-02-05"},
            headers=auth_headers(hr_token),
        )
        res = client.get("/api/time-off/requests", headers=auth_headers(employee_token))
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_employee_cannot_create_request_for_others(self, client, hr_token, employee_token, db_session):
        type_ = _create_type(client, hr_token, requires_allocation=False)
        other_employee_id = _employee_id_for(db_session, "hr-test@payloom.local")
        res = client.post(
            "/api/time-off/requests",
            json={"time_off_type_id": type_["id"], "employee_id": other_employee_id, "start_date": "2026-01-05", "end_date": "2026-01-05"},
            headers=auth_headers(employee_token),
        )
        assert res.status_code == 403


class TestBalanceEndpoint:
    def test_balance_reflects_allocation_and_consumption(self, client, hr_token, employee_token, db_session):
        type_ = _create_type(client, hr_token)
        employee_id = _employee_id_for(db_session, "employee-test@payloom.local")
        _give_schedule(db_session, employee_id)
        allocation = _create_allocation(client, hr_token, employee_id, type_["id"], allocated_amount=20)
        _approve_allocation(client, hr_token, allocation["id"])

        res = client.get(f"/api/time-off/balance?employee_id={employee_id}&time_off_type_id={type_['id']}", headers=auth_headers(employee_token))
        assert res.status_code == 200
        assert res.json()["remaining"] == "20.00"

    def test_employee_cannot_query_others_balance(self, client, hr_token, employee_token, db_session):
        type_ = _create_type(client, hr_token)
        other_employee_id = _employee_id_for(db_session, "hr-test@payloom.local")
        res = client.get(f"/api/time-off/balance?employee_id={other_employee_id}&time_off_type_id={type_['id']}", headers=auth_headers(employee_token))
        assert res.status_code == 403
