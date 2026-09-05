from tests.conftest import auth_headers


def test_check_in_and_current_state(client, employee_token):
    res = client.get("/api/attendance/current", headers=auth_headers(employee_token))
    assert res.json()["checked_in"] is False

    res = client.post("/api/attendance/check-in", headers=auth_headers(employee_token))
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "ACTIVE"

    res = client.get("/api/attendance/current", headers=auth_headers(employee_token))
    assert res.json()["checked_in"] is True


def test_duplicate_check_in_rejected(client, employee_token):
    client.post("/api/attendance/check-in", headers=auth_headers(employee_token))
    res = client.post("/api/attendance/check-in", headers=auth_headers(employee_token))
    assert res.status_code == 409
    assert res.json()["detail"]["error"]["code"] == "ALREADY_CHECKED_IN"


def test_check_out_without_open_session_rejected(client, employee_token):
    res = client.post("/api/attendance/check-out", headers=auth_headers(employee_token))
    assert res.status_code == 409
    assert res.json()["detail"]["error"]["code"] == "NO_OPEN_SESSION"


def test_check_in_then_check_out_completes(client, employee_token):
    client.post("/api/attendance/check-in", headers=auth_headers(employee_token))
    res = client.post("/api/attendance/check-out", headers=auth_headers(employee_token))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "COMPLETED"
    assert body["worked_minutes"] is not None

    res = client.get("/api/attendance/current", headers=auth_headers(employee_token))
    assert res.json()["checked_in"] is False


def test_employee_cannot_view_others_attendance(client, employee_token, hr_token, db_session):
    # HR checks in (a different employee than the EMPLOYEE-role test user)
    client.post("/api/attendance/check-in", headers=auth_headers(hr_token))
    res = client.get("/api/attendance", headers=auth_headers(hr_token))
    hr_attendance_id = res.json()[0]["id"]

    res = client.get(f"/api/attendance/{hr_attendance_id}", headers=auth_headers(employee_token))
    assert res.status_code == 403


def test_employee_list_only_returns_own_records(client, employee_token, hr_token):
    client.post("/api/attendance/check-in", headers=auth_headers(employee_token))
    client.post("/api/attendance/check-in", headers=auth_headers(hr_token))

    res = client.get("/api/attendance", headers=auth_headers(employee_token))
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_hr_can_filter_by_employee(client, employee_token, hr_token, db_session):
    client.post("/api/attendance/check-in", headers=auth_headers(employee_token))
    from app.models.user import User
    employee_user = db_session.query(User).filter(User.work_email == "employee-test@payloom.local").first()

    res = client.get(f"/api/attendance?employee_id={employee_user.employee_id}", headers=auth_headers(hr_token))
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["employee"]["id"] == employee_user.employee_id


def test_correction_recalculates_worked_time(client, employee_token, hr_token):
    client.post("/api/attendance/check-in", headers=auth_headers(employee_token))
    check_out_res = client.post("/api/attendance/check-out", headers=auth_headers(employee_token))
    attendance_id = check_out_res.json()["id"]

    res = client.patch(
        f"/api/attendance/{attendance_id}",
        json={"check_in": "2026-01-01T09:00:00Z", "check_out": "2026-01-01T18:10:00Z", "notes": "Corrected forgotten checkout"},
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["worked_minutes"] == 9 * 60 + 10
    assert body["corrected_by_name"]


def test_correction_rejects_end_before_start(client, employee_token, hr_token):
    client.post("/api/attendance/check-in", headers=auth_headers(employee_token))
    check_out_res = client.post("/api/attendance/check-out", headers=auth_headers(employee_token))
    attendance_id = check_out_res.json()["id"]

    res = client.patch(
        f"/api/attendance/{attendance_id}",
        json={"check_in": "2026-01-01T18:00:00Z", "check_out": "2026-01-01T09:00:00Z"},
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 422


def test_employee_role_cannot_correct_attendance(client, employee_token):
    client.post("/api/attendance/check-in", headers=auth_headers(employee_token))
    check_out_res = client.post("/api/attendance/check-out", headers=auth_headers(employee_token))
    attendance_id = check_out_res.json()["id"]

    res = client.patch(
        f"/api/attendance/{attendance_id}",
        json={"notes": "self-correction attempt"},
        headers=auth_headers(employee_token),
    )
    assert res.status_code == 403


def test_unauthenticated_rejected(client):
    res = client.get("/api/attendance")
    assert res.status_code == 401
