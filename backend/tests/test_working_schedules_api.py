from tests.conftest import auth_headers


def test_schedule_create_with_lines_derives_hours(client, hr_token):
    res = client.post(
        "/api/working-schedules",
        json={
            "name": "40 Hours / Week",
            "lines": [
                {"day_of_week": d, "start_time": "09:00:00", "end_time": "18:00:00", "break_minutes": 60}
                for d in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
            ],
        },
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["days_per_week"] == 5
    assert body["hours_per_week"] == 40.0
    assert all(line["derived_hours"] == 8.0 for line in body["lines"])


def test_negative_break_rejected(client, hr_token):
    res = client.post(
        "/api/working-schedules",
        json={"name": "Bad Schedule", "lines": [{"day_of_week": "MONDAY", "start_time": "09:00:00", "end_time": "18:00:00", "break_minutes": -10}]},
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 422


def test_break_longer_than_shift_rejected(client, hr_token):
    res = client.post(
        "/api/working-schedules",
        json={"name": "Bad Schedule", "lines": [{"day_of_week": "MONDAY", "start_time": "09:00:00", "end_time": "10:00:00", "break_minutes": 90}]},
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 422


def test_schedule_line_update_recalculates_total(client, hr_token):
    res = client.post(
        "/api/working-schedules",
        json={"name": "Flex", "lines": [{"day_of_week": "MONDAY", "start_time": "09:00:00", "end_time": "18:00:00", "break_minutes": 60}]},
        headers=auth_headers(hr_token),
    )
    schedule_id = res.json()["id"]
    res = client.patch(
        f"/api/working-schedules/{schedule_id}",
        json={"lines": [
            {"day_of_week": "MONDAY", "start_time": "09:00:00", "end_time": "18:00:00", "break_minutes": 60},
            {"day_of_week": "TUESDAY", "start_time": "09:00:00", "end_time": "18:00:00", "break_minutes": 60},
        ]},
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 200, res.text
    assert res.json()["days_per_week"] == 2
    assert res.json()["hours_per_week"] == 16.0


def test_inactive_schedule_remains_retrievable(client, hr_token):
    res = client.post("/api/working-schedules", json={"name": "Old Schedule", "status": "INACTIVE", "lines": []}, headers=auth_headers(hr_token))
    schedule_id = res.json()["id"]
    res = client.get(f"/api/working-schedules/{schedule_id}", headers=auth_headers(hr_token))
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_invalid_schedule_reference_rejected_on_employee(client, hr_token):
    res = client.post(
        "/api/employees", json={"first_name": "Ivy", "last_name": "Nolan", "working_schedule_id": 9999}, headers=auth_headers(hr_token)
    )
    assert res.status_code == 400


def test_rbac_employee_role_cannot_create_schedule(client, employee_token):
    res = client.post("/api/working-schedules", json={"name": "Nope", "lines": []}, headers=auth_headers(employee_token))
    assert res.status_code == 403
