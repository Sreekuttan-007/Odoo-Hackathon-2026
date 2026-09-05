from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import get_db
from app.models.employee import Employee
from app.models.user import User, AccountStatus

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "INVALID_TOKEN", "message": "Could not validate credentials."}},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if user.status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "INACTIVE_ACCOUNT", "message": "This account is inactive."}}
        )
    return user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ACCESS_DENIED", "message": "You don't have access to this area."}}
        )
    return current_user


HR_CAPABLE_ROLES = {"HR_MANAGER", "HR_PAYROLL_USER", "HR_PAYROLL_MANAGER", "ADMIN"}


def get_current_hr(current_user: User = Depends(get_current_user)) -> User:
    """Employees/Contracts/Working Schedules administration is restricted to
    HR-capable roles; plain EMPLOYEE accounts have read-only access."""
    if current_user.role not in HR_CAPABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ACCESS_DENIED", "message": "You don't have access to this area."}}
        )
    return current_user


PAYROLL_OPERATOR_ROLES = {"HR_PAYROLL_USER", "HR_PAYROLL_MANAGER", "ADMIN"}
PAYROLL_CONFIG_ROLES = {"HR_PAYROLL_MANAGER", "ADMIN"}


def get_current_payroll_operator(current_user: User = Depends(get_current_user)) -> User:
    """Payrun/Payslip operations (create, compute, validate, mark paid, send).
    HR_MANAGER explicitly has no payroll mutation access (Phase 5 spec
    section 67) even though it's HR-capable elsewhere."""
    if current_user.role not in PAYROLL_OPERATOR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ACCESS_DENIED", "message": "You don't have access to payroll operations."}}
        )
    return current_user


def get_current_payroll_manager(current_user: User = Depends(get_current_user)) -> User:
    """Salary Structure/Rule configuration is HR_PAYROLL_MANAGER/ADMIN only;
    HR_PAYROLL_USER has read-only access to configuration (section 68)."""
    if current_user.role not in PAYROLL_CONFIG_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ACCESS_DENIED", "message": "You don't have access to payroll configuration."}}
        )
    return current_user
