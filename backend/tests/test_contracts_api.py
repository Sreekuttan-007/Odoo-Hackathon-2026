from tests.conftest import auth_headers


def _bootstrap(client, hr_token):
    dept_id = client.post("/api/departments", json={"name": "Engineering"}, headers=auth_headers(hr_token)).json()["id"]
    pos_id = client.post("/api/job-positions", json={"title": "Software Engineer"}, headers=auth_headers(hr_token)).json()["id"]
    emp_id = client.post("/api/employees", json={"first_name": "Aarav", "last_name": "Mehta"}, headers=auth_headers(hr_token)).json()["id"]
    return dept_id, pos_id, emp_id


def test_contract_create_and_reference(client, hr_token):
    dept_id, pos_id, emp_id = _bootstrap(client, hr_token)
    res = client.post(
        "/api/contracts",
        json={"employee_id": emp_id, "department_id": dept_id, "job_position_id": pos_id, "start_date": "2026-01-01", "wage_monthly": 85000},
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["reference"].startswith("CON/2026/")
    assert body["status"] == "RUNNING"
    assert body["wage_monthly"] == "85000.00"


def test_overlapping_contract_rejected(client, hr_token):
    dept_id, pos_id, emp_id = _bootstrap(client, hr_token)
    client.post(
        "/api/contracts",
        json={"employee_id": emp_id, "department_id": dept_id, "job_position_id": pos_id, "start_date": "2026-01-01", "wage_monthly": 85000},
        headers=auth_headers(hr_token),
    )
    res = client.post(
        "/api/contracts",
        json={"employee_id": emp_id, "department_id": dept_id, "job_position_id": pos_id, "start_date": "2026-06-01", "wage_monthly": 90000},
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 409
    assert res.json()["detail"]["error"]["code"] == "CONTRACT_OVERLAP"


def test_end_before_start_rejected(client, hr_token):
    dept_id, pos_id, emp_id = _bootstrap(client, hr_token)
    res = client.post(
        "/api/contracts",
        json={
            "employee_id": emp_id, "department_id": dept_id, "job_position_id": pos_id,
            "start_date": "2026-06-01", "end_date": "2026-01-01", "wage_monthly": 85000,
        },
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 422


def test_open_ended_contract_behavior(client, hr_token):
    dept_id, pos_id, emp_id = _bootstrap(client, hr_token)
    res = client.post(
        "/api/contracts",
        json={"employee_id": emp_id, "department_id": dept_id, "job_position_id": pos_id, "start_date": "2026-01-01", "wage_monthly": 85000},
        headers=auth_headers(hr_token),
    )
    assert res.json()["end_date"] is None
    assert res.json()["status"] == "RUNNING"


def test_applicable_contract_lookup_missing(client, hr_token):
    dept_id, pos_id, emp_id = _bootstrap(client, hr_token)
    res = client.get(
        f"/api/contracts/applicable?employee_id={emp_id}&period_start=2026-01-01&period_end=2026-01-31",
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 404
    assert res.json()["detail"]["error"]["code"] == "MISSING_CONTRACT"


def test_applicable_contract_lookup_returns_the_covering_contract(client, hr_token):
    dept_id, pos_id, emp_id = _bootstrap(client, hr_token)
    created = client.post(
        "/api/contracts",
        json={"employee_id": emp_id, "department_id": dept_id, "job_position_id": pos_id, "start_date": "2026-01-01", "wage_monthly": 85000},
        headers=auth_headers(hr_token),
    ).json()
    res = client.get(
        f"/api/contracts/applicable?employee_id={emp_id}&period_start=2026-03-01&period_end=2026-03-31",
        headers=auth_headers(hr_token),
    )
    assert res.status_code == 200
    assert res.json()["id"] == created["id"]


def test_rbac_employee_role_cannot_create_contract(client, employee_token, hr_token):
    dept_id, pos_id, emp_id = _bootstrap(client, hr_token)
    res = client.post(
        "/api/contracts",
        json={"employee_id": emp_id, "department_id": dept_id, "job_position_id": pos_id, "start_date": "2026-01-01", "wage_monthly": 85000},
        headers=auth_headers(employee_token),
    )
    assert res.status_code == 403
