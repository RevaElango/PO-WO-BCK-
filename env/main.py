from sqlalchemy.orm import Session  # ✅ Correct import
from fastapi import FastAPI, Depends, HTTPException, Header, Security
from typing import List
from database import SessionLocal, engine, Base
import schemas, crud
from models import User  # If needed
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets  # ✅ Secure random token generation

#  Store active tokens (simple in-memory session store)
active_tokens = {}

Base.metadata.create_all(bind=engine)
security = HTTPBearer()  # Enables Swagger "Authorize" button

app = FastAPI()

# ✅ Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Token Auth Dependency
def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if not token or token not in active_tokens:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing token")
    return active_tokens[token]

# ✅ Login Route
@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if not db_user or db_user.password_hash != user.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    # ✅ Generate secure random token
    token = secrets.token_urlsafe(32)
    active_tokens[token] = {"id": db_user.id, "email": db_user.email}
    
    return {"access_token": token}

# ✅ Protected Routes
@app.post("/purchase-orders/", response_model=schemas.PurchaseOrder)
def create_po(po: schemas.PurchaseOrderCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.create_po(db=db, po=po)

@app.get("/purchase-orders/", response_model=List[schemas.PurchaseOrder])
def read_pos(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_pos(db)
# ✅ Create Work Order
@app.post("/work-orders/", response_model=schemas.WorkOrder)
def create_work_order(work_order: schemas.WorkOrderCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.create_work_order(db=db, work_order=work_order)

# ✅ Read All Work Orders
@app.get("/work-orders/", response_model=List[schemas.WorkOrder])
def read_work_orders(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_work_orders(db)

