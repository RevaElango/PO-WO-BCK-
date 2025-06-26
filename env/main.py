from fastapi import FastAPI, Depends, HTTPException, Security, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from jose import JWTError, jwt
from datetime import datetime, timedelta
import schemas, crud
from database import SessionLocal, engine, Base
from models import *
import os
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import update

# Secret key and algorithm
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# FastAPI app
app = FastAPI()
security = HTTPBearer()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
Base.metadata.create_all(bind=engine)

# DB session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# JWT creation

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Token verification
def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_data = payload.get("user")
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_data
    except JWTError:
        raise HTTPException(status_code=401, detail="Token is invalid or expired")

@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if not db_user or db_user.password_hash != user.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={"user": {"id": db_user.id, "email": db_user.email}},
        expires_delta=access_token_expires,
    )

    return {"access_token": token, "token_type": "bearer", "expires_in_minutes": ACCESS_TOKEN_EXPIRE_MINUTES}

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

@app.post("/amendment-orders/", response_model=schemas.AMOrder)
def create_am_order(am_order: schemas.AMOrderCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    crud.mark_reference_amended(db, am_order.reference_no)
    return crud.create_am_order(db=db, am_order=am_order)

@app.get("/amendment-orders/view", response_model=List[schemas.AMOrder])
def list_am_orders(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_am_orders(db)

@app.get("/token/ping")
def ping(current_user: User = Depends(get_current_user)):
    return {"message": "OK"}

@app.get("/dashboard", response_model=schemas.DashboardCounts)
def get_dashboard_data(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_dashboard_counts(db)

@app.get("/suppliers")
def get_suppliers(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    suppliers = db.query(Supplier).all()
    return [
        {
            "id": supplier.id,
            "name": supplier.supplier_name,
            "address": supplier.supplier_address
        }
        for supplier in suppliers
    ]

@app.get("/project-keywords")
def get_project_keywords(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    projects = db.query(ProjectNoDetails).all()
    return [
        {
            "id": project.id,
            "project_keyword": project.project_keyword,
            "project_no":project.project_no,
            "pn_prefix": project.pn_prefix,   # updated
            "pn_suffix": project.pn_suffix    # updated
        }
        for project in projects
    ]
@app.get("/total-orders", response_model=List[schemas.TotalOrder])
def fetch_total_orders(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_total_orders(db)

# Upload Directories
SIGNED_PO_UPLOAD_DIR = "uploads/signed_pos"
SIGNED_WO_UPLOAD_DIR = "uploads/signed_wos"
SIGNED_AM_UPLOAD_DIR = "uploads/signed_Ams"

os.makedirs(SIGNED_PO_UPLOAD_DIR, exist_ok=True)
os.makedirs(SIGNED_WO_UPLOAD_DIR, exist_ok=True)
os.makedirs(SIGNED_AM_UPLOAD_DIR, exist_ok=True)

app.mount("/uploads/signed_pos", StaticFiles(directory=SIGNED_PO_UPLOAD_DIR), name="signed_pos")
app.mount("/uploads/signed_wos", StaticFiles(directory=SIGNED_WO_UPLOAD_DIR), name="signed_wos")
app.mount("/uploads/signed_Ams", StaticFiles(directory=SIGNED_AM_UPLOAD_DIR), name="signed_Ams")

# Upload Signed PO
@app.post("/purchase-orders/{po_id}/upload-signed-po")
def upload_signed_po(po_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    filename = f"signed_po_{po_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    file_path = os.path.join(SIGNED_PO_UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
    relative_path = f"http://localhost:8000/uploads/signed_pos/{filename}"
    db.execute(update(PurchaseOrder).where(PurchaseOrder.id == po_id).values(signed_po_path=relative_path, signed_po_uploaded_at=datetime.utcnow()))
    db.commit()
    return JSONResponse(content={"message": "Signed PO uploaded successfully", "signed_po_path": relative_path})

# Upload Signed WO
@app.post("/work-orders/{wo_id}/upload-signed-wo")
def upload_signed_wo(wo_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    filename = f"signed_wo_{wo_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    file_path = os.path.join(SIGNED_WO_UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
    relative_path = f"http://localhost:8000/uploads/signed_wos/{filename}"
    db.execute(update(WorkOrder).where(WorkOrder.id == wo_id).values(signed_wo_path=relative_path, signed_wo_uploaded_at=datetime.utcnow()))
    db.commit()
    return JSONResponse(content={"message": "Signed WO uploaded successfully", "signed_wo_path": relative_path})

# Upload Signed AM
@app.post("/Amendment-orders/{Am_id}/upload-signed-Am")
def upload_signed_Am(Am_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    filename = f"signed_Am_{Am_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    file_path = os.path.join(SIGNED_AM_UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
    relative_path = f"http://localhost:8000/uploads/signed_Ams/{filename}"
    db.execute(update(AmendmentOrder).where(AmendmentOrder.id == Am_id).values(signed_Am_path=relative_path, signed_Am_uploaded_at=datetime.utcnow()))
    db.commit()
    return JSONResponse(content={"message": "Signed AM uploaded successfully", "signed_Am_path": relative_path})

@app.get("/amendment-source-options")
def get_po_wo_numbers(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    po_numbers = db.query(PurchaseOrder.po_number).all()
    wo_numbers = db.query(WorkOrder.work_order_no).all()

    return {
        "purchase_orders": [po[0] for po in po_numbers],
        "work_orders": [wo[0] for wo in wo_numbers]
    }
