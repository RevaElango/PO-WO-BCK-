from sqlalchemy.orm import Session# ✅ Correct import
from fastapi import FastAPI, Depends, HTTPException, Header
from typing import List
from database import SessionLocal, engine, Base
import schemas, crud
from models import User  # If needed
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security

# 🔐 Store active tokens (for simple in-memory session)
active_tokens = {}

Base.metadata.create_all(bind=engine)
security = HTTPBearer()  # This enables the "Authorize" button in Swagger


app = FastAPI()

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 🧠 Get current user from token header
def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if not token or token not in active_tokens:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing token")
    return active_tokens[token]


# Example Protected Route
@app.post("/purchase-orders/", response_model=schemas.PurchaseOrder)
def create_po(po: schemas.PurchaseOrderCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.create_po(db=db, po=po)

@app.get("/purchase-orders/", response_model=List[schemas.PurchaseOrder])
def read_pos(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_pos(db)

@app.get("/purchase-orders/{po_id}", response_model=schemas.PurchaseOrder)
def read_po(po_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    po = crud.get_po_by_id(db, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    return po

# Add your login route here (if not already)
@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if not db_user or db_user.password_hash != user.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    # Simple token generation (not secure, just for demo)
    token = f"token-{db_user.id}"
    active_tokens[token] = {"id": db_user.id, "email": db_user.email}
    return {"access_token": token}
