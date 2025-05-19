from sqlalchemy.orm import Session
from fastapi import FastAPI, Depends, HTTPException, Header, Security
from typing import List
import secrets
import schemas, crud
from models import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta  # ✅ Import for expiration

# ✅ In-memory store for active tokens with expiration
active_tokens = {}

Base.metadata.create_all(bind=engine)
security = HTTPBearer()

app = FastAPI()
security = HTTPBearer()  # Enables Swagger "Authorize" button

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to a specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Dependency to get DB session
from models import User  # If needed
from database import SessionLocal, engine, Base

# ✅ Create DB tables
Base.metadata.create_all(bind=engine)

# ✅ In-memory token store
active_tokens = {}

# ✅ FastAPI app and security scheme
app = FastAPI()
security = HTTPBearer()  # Enables Swagger "Authorize" button

# ✅ Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Token Auth Dependency with Expiration Check
def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    token_data = active_tokens.get(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token")

    # ✅ Check token expiration
    if datetime.utcnow() > token_data["expires_at"]:
        del active_tokens[token]  # Remove expired token
        raise HTTPException(status_code=401, detail="Token has expired")

    return token_data["user"]

# ✅ Login Route with Expiration
@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if not db_user or db_user.password_hash != user.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    token = secrets.token_urlsafe(32)
    active_tokens[token] = {
        "user": {"id": db_user.id, "email": db_user.email},
        "expires_at": datetime.utcnow() + timedelta(minutes=60)  # ✅ Token expires in 60 mins
    }

    return {"access_token": token, "expires_in_minutes": 60}

# ✅ Protected Endpoints
@app.post("/purchase-orders/", response_model=schemas.PurchaseOrder)
def create_po(po: schemas.PurchaseOrderCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.create_po(db=db, po=po)

@app.get("/purchase-orders/view", response_model=List[schemas.PurchaseOrder])
def read_pos(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_pos(db)

@app.post("/work-orders/", response_model=schemas.WorkOrder)
def create_work_order(work_order: schemas.WorkOrderCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.create_work_order(db=db, work_order=work_order)

@app.get("/work-orders/view", response_model=List[schemas.WorkOrder])
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
@app.get("/amendment-orders/view", response_model=List[schemas.AMOrder])
def list_am_orders(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    return crud.get_all_am_orders(db)
