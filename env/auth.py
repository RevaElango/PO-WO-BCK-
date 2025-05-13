from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserLogin, TokenResponse

router = APIRouter()

# In-memory token storage
active_tokens = {}

@router.post("/login", response_model=TokenResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user or db_user.password_hash != user.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = f"token-{db_user.id}"
    active_tokens[token] = db_user.email
    return {"access_token": token}
