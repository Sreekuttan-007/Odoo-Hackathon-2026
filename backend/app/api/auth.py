from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User, AccountStatus
from app.schemas.user import LoginRequest, Token, UserResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.work_email == request.email).first()
    
    # Generic error message to prevent enumeration
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "INVALID_CREDENTIALS", "message": "The email or password is incorrect."}}
    )

    if not user or not verify_password(request.password, user.hashed_password):
        raise invalid_credentials

    if user.status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "INACTIVE_ACCOUNT", "message": "This account is inactive. Contact your administrator."}}
        )
        
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
