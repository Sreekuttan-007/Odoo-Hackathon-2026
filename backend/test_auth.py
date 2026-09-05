from app.db.database import SessionLocal
from app.models.user import User
from app.core.security import verify_password

db = SessionLocal()
user = db.query(User).filter(User.work_email == "admin@payloom.local").first()
if not user:
    print("User not found!")
else:
    print(f"User found: {user.work_email}")
    is_valid = verify_password("admin123", user.hashed_password)
    print(f"Password 'admin123' valid? {is_valid}")
    print(f"Stored Hash: {user.hashed_password}")
