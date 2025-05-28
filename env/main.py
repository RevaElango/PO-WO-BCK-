from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
import secrets
from fastapi.middleware.cors import CORSMiddleware

import schemas, crud
from models import User  # If needed
from database import SessionLocal, engine, Base

# ✅ Create DB tables
Base.metadata.create_all(bind=engine)

# ✅ In-memory token store
active_tokens = {}

# ✅ FastAPI app and security scheme
app = FastAPI()
security = HTTPBearer()  # Enables Swagger "Authorize" button

# ✅ Allow CORS for frontend (Angular)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Change to frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ✅ Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Token authentication dependency
def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if not token or token not in active_tokens:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing token")
    return active_tokens[token]  # Return user info (id, email)

# ✅ Login route
@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if not db_user or db_user.password_hash != user.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # ✅ Generate secure token
    token = secrets.token_urlsafe(32)
    active_tokens[token] = {"id": db_user.id, "email": db_user.email}
    return {"access_token": token}

# ✅ Protected route: Create Purchase Order
@app.post("/purchase-orders/", response_model=schemas.PurchaseOrder)
def create_po(po: schemas.PurchaseOrderCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.create_po(db=db, po=po)

# ✅ Protected route: Get all Purchase Orders
@app.get("/purchase-orders/view", response_model=List[schemas.PurchaseOrder])
def read_pos(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_pos(db)

# ✅ Protected route: Create Work Order
@app.post("/work-orders/", response_model=schemas.WorkOrder)
def create_work_order(work_order: schemas.WorkOrderCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.create_work_order(db=db, work_order=work_order)

# ✅ Protected route: Get all Work Orders
@app.get("/work-orders/", response_model=List[schemas.WorkOrder])
def read_work_orders(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_work_orders(db)

# ✅ 🔐 Authenticated route: Create Amendment Order
@app.post("/amendment-orders/", response_model=schemas.AMOrder)
def create_am_order(
    am_order: schemas.AMOrderCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    return crud.create_am_order(db=db, am_order=am_order)

# ✅ 🔐 Authenticated route: Get Amendment Orders
@app.get("/amendment-orders/", response_model=List[schemas.AMOrder])
def list_am_orders(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    return crud.get_all_am_orders(db)
