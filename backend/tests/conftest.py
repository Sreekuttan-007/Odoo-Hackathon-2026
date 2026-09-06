import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.database import get_db
from app.main import app
from app.models.user import User, Role, AccountStatus
from app.models.employee import Employee, EmployeeStatus
from app.core.security import get_password_hash

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _make_user(db_session, role: Role, email: str) -> str:
    employee = Employee(first_name=role.value.title(), last_name="User", work_email=email, status=EmployeeStatus.ACTIVE)
    db_session.add(employee)
    db_session.flush()
    user = User(
        employee_id=employee.id,
        work_email=email,
        role=role,
        status=AccountStatus.ACTIVE,
        hashed_password=get_password_hash("password123"),
    )
    db_session.add(user)
    db_session.commit()
    return email


@pytest.fixture()
def hr_token(client, db_session):
    email = _make_user(db_session, Role.HR_MANAGER, "hr-test@payloom.local")
    res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.fixture()
def admin_token(client, db_session):
    email = _make_user(db_session, Role.ADMIN, "admin-test@payloom.local")
    res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.fixture()
def employee_token(client, db_session):
    email = _make_user(db_session, Role.EMPLOYEE, "employee-test@payloom.local")
    res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
