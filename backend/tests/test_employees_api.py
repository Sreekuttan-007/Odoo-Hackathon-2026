from tests.conftest import auth_headers


def _create_department(client, hr_token, name="Engineering"):
    res = client.post("/api/departments", json={"name": name}, headers=auth_headers(hr_token))
    assert res.status_code == 200, res.text
    return res.json()["id"]


def _create_job_position(client, hr_token, title="Software Engineer"):
    res = client.post("/api/job-positions", json={"title": title}, headers=auth_headers(hr_token))
    assert res.status_code == 200, res.text
    return res.json()["id"]


def test_employee_create(client, hr_token):
    dept_id = _create_department(client, hr_token)
    pos_id = _create_job_position(client, hr_token)
    res = client.post(
        "/api/employees",
        json={"first_name": "Aarav", "last_name": "Mehta", "work_email": "aarav@payloom.local", "department_id": dept_id, "job_position_id": pos_id},
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["employee_code"]
    assert body["department"]["id"] == dept_id
    assert body["job_position"]["id"] == pos_id


def test_employee_update(client, hr_token):
    res = client.post("/api/employees", json={"first_name": "Bea", "last_name": "Lopez"}, headers=auth_headers(hr_token))
    emp_id = res.json()["id"]
    res = client.patch(f"/api/employees/{emp_id}", json={"work_email": "bea@payloom.local"}, headers=auth_headers(hr_token))
    assert res.status_code == 200, res.text
    assert res.json()["work_email"] == "bea@payloom.local"


def test_department_relation_rejects_unknown_id(client, hr_token):
    res = client.post(
        "/api/employees", json={"first_name": "Ivy", "last_name": "Nolan", "department_id": 9999}, headers=auth_headers(hr_token)
    )
    assert res.status_code == 400


def test_job_position_relation_rejects_unknown_id(client, hr_token):
    res = client.post(
        "/api/employees", json={"first_name": "Ivy", "last_name": "Nolan", "job_position_id": 9999}, headers=auth_headers(hr_token)
    )
    assert res.status_code == 400


def test_manager_relation_valid(client, hr_token):
    res = client.post("/api/employees", json={"first_name": "Dave", "last_name": "Staff"}, headers=auth_headers(hr_token))
    manager_id = res.json()["id"]
    res = client.post(
        "/api/employees", json={"first_name": "Aarav", "last_name": "Mehta", "manager_id": manager_id}, headers=auth_headers(hr_token)
    )
    assert res.status_code == 200, res.text
    assert res.json()["manager"]["id"] == manager_id


def test_self_manager_rejected(client, hr_token):
    res = client.post("/api/employees", json={"first_name": "Solo", "last_name": "Worker"}, headers=auth_headers(hr_token))
    emp_id = res.json()["id"]
    res = client.patch(f"/api/employees/{emp_id}", json={"manager_id": emp_id}, headers=auth_headers(hr_token))
    assert res.status_code == 400
    assert res.json()["detail"]["error"]["code"] == "INVALID_MANAGER"


def test_manager_relation_rejects_unknown_id(client, hr_token):
    res = client.post(
        "/api/employees", json={"first_name": "Ghost", "last_name": "Boss", "manager_id": 9999}, headers=auth_headers(hr_token)
    )
    assert res.status_code == 400


def test_working_schedule_relation_valid(client, hr_token):
    res = client.post(
        "/api/working-schedules",
        json={"name": "40 Hours / Week", "lines": [
            {"day_of_week": "MONDAY", "start_time": "09:00:00", "end_time": "18:00:00", "break_minutes": 60}
        ]},
        headers=auth_headers(hr_token),
    )
    schedule_id = res.json()["id"]
    res = client.post(
        "/api/employees", json={"first_name": "Fay", "last_name": "Torres", "working_schedule_id": schedule_id}, headers=auth_headers(hr_token)
    )
    assert res.status_code == 200, res.text
    assert res.json()["working_schedule"]["id"] == schedule_id
    assert res.json()["working_schedule"]["hours_per_week"] == 8.0


def test_employee_contracts_filter(client, hr_token):
    dept_id = _create_department(client, hr_token)
    pos_id = _create_job_position(client, hr_token)
    res = client.post("/api/employees", json={"first_name": "Aarav", "last_name": "Mehta"}, headers=auth_headers(hr_token))
    emp_id = res.json()["id"]
    client.post(
        "/api/contracts",
        json={"employee_id": emp_id, "department_id": dept_id, "job_position_id": pos_id, "start_date": "2026-01-01", "wage_monthly": 85000},
        headers=auth_headers(hr_token),
    )
    res = client.get(f"/api/contracts?employee_id={emp_id}", headers=auth_headers(hr_token))
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["employee"]["id"] == emp_id


def test_rbac_employee_role_cannot_create_employee(client, employee_token):
    res = client.post("/api/employees", json={"first_name": "Nope", "last_name": "Denied"}, headers=auth_headers(employee_token))
    assert res.status_code == 403


def test_rbac_employee_role_can_read_employees(client, employee_token):
    res = client.get("/api/employees", headers=auth_headers(employee_token))
    assert res.status_code == 200


def test_rbac_unauthenticated_rejected(client):
    res = client.get("/api/employees")
    assert res.status_code == 401
