from fastapi import FastAPI, Depends, HTTPException, Security, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from jose import JWTError, jwt
from datetime import datetime, timedelta
import schemas, crud
from schemas import *
from database import SessionLocal, engine, Base,get_db
from models import * 
import os
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import update
import json
import models
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

@app.post("/login", response_model=TokenResponse)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if not db_user or db_user.password_hash != user.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={
            "user": {
                "id": db_user.id,
                "email": db_user.email,
                "username": db_user.username,
                "role_id": db_user.role_id,
            }
        },
        expires_delta=access_token_expires,
    )

    return TokenResponse(
        access_token=token,
        expires_in_minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

@app.post("/purchase-orders/", response_model=schemas.PurchaseOrder)
def create_po(
    po_number: str = Form(...),
    po_date: str = Form(...),
    supplier_name: str = Form(...),
    supplier_address: str = Form(...),
    indent_date: str = Form(...),
    requester_name: str = Form(...),
    quotation_number: str = Form(None),
    quotation_date: str = Form(None),
    email: str = Form(None),
    dated: str = Form(None),
    total_cost: int = Form(...),
    total_including_gst: float = Form(...),
    delivery_date: str = Form(...),
    payment_terms: str = Form(...),
    additional_terms: str = Form(None),
    delivery_mode: str = Form(...),
    is_asset: bool = Form(False),
    asset_type: str = Form(None),
    include_annexure: bool = Form(False),
    annexure_text: str = Form(None),
    annexure_file_path: str = Form(None),
    project_keyword: str = Form(None),
    prefix: str = Form(None),
    suffix: str = Form(None),
    final_suffix : str = Form(None),
    items: str = Form(...),  # JSON string, will parse manually
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    import json
    items_list = json.loads(items)  # Convert items JSON string to Python list

    # ✅ Now use the values to build a POCreate schema manually
    po_data = schemas.PurchaseOrderCreate(
        po_number=po_number,
        po_date=po_date,
        supplier_name=supplier_name,
        supplier_address=supplier_address,
        indent_date=indent_date,
        requester_name=requester_name,
        quotation_number=quotation_number,
        quotation_date=quotation_date,
        email=email,
        dated=dated,
        total_cost=total_cost,
        total_including_gst=total_including_gst,
        delivery_date=delivery_date,
        payment_terms=payment_terms,
        additional_terms=additional_terms,
        delivery_mode=delivery_mode,
        is_asset=is_asset,
        asset_type=asset_type,
        include_annexure=include_annexure,
        annexure_text=annexure_text,
        annexure_file_path=annexure_file_path,
        project_keyword=project_keyword,
        prefix=prefix,
        suffix=suffix,
        final_suffix=final_suffix,
        items=items_list,
        created_by=user['username']
    )

    db_po = crud.create_po(db=db, po=po_data)

    # ✅ Save file (optional)
    if file and file.content_type == "application/pdf":
        import os
        from datetime import datetime

        safe_po_number = po_number.replace("/", "_")
        filename = f"generated_po_{safe_po_number}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        generated_po_dir = "uploads/generated_po_files"
        os.makedirs(generated_po_dir, exist_ok=True)
        file_path = os.path.join(generated_po_dir, filename)

        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        relative_url = f"http://localhost:8000/uploads/generated_po_files/{filename}"
        db_po.preview_file_path = relative_url
        db.commit()

    return db_po



@app.get("/purchase-orders/view", response_model=List[schemas.PurchaseOrder])
def read_pos(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_pos(db)

@app.post("/work-orders/", response_model=schemas.WorkOrder)
def create_work_order(
    work_order_no: str = Form(...),
    prefix: str = Form(...),
    suffix: str = Form(...),
    date: str = Form(...),
    quotation_no: str = Form(None),
    email: str = Form(None),
    supplier_name: str = Form(...),
    address: str = Form(...),
    quotation_date: str = Form(None),
    indent_date: str = Form(...),
    requester_name: str = Form(...),
    scope_of_work: str = Form(...),
    value_of_service: float = Form(...),
    tax: float = Form(...),
    duration_of_service: str = Form(...),
    payment_term: str = Form(...),
    deliverables: str = Form(...),
    additional_terms: str = Form(None),
    include_annexure: bool = Form(False),
    annexure_text: str = Form(None),
    annexure_file_path: str = Form(None),
    project_keyword: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # Create WorkOrderCreate schema instance
    work_order = schemas.WorkOrderCreate(
        work_order_no=work_order_no,
        prefix=prefix,
        suffix=suffix,
        date=date,
        quotation_no=quotation_no,
        email=email,
        supplier_name=supplier_name,
        address=address,
        quotation_date=quotation_date,
        indent_date=indent_date,
        requester_name=requester_name,
        scope_of_work=scope_of_work,
        value_of_service=value_of_service,
        tax=tax,
        duration_of_service=duration_of_service,
        payment_term=payment_term,
        deliverables=deliverables,
        additional_terms=additional_terms,
        include_annexure=include_annexure,
        annexure_text=annexure_text,
        annexure_file_path=annexure_file_path,
        project_keyword=project_keyword,
        created_by=user['username']
    )

    # Store in DB
    db_work_order = crud.create_work_order(db=db, work_order=work_order)

    # ✅ Save uploaded PDF
    if file and file.content_type == "application/pdf":
        safe_no = work_order_no.replace("/", "_")
        filename = f"generated_wo_{safe_no}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        wo_dir = "uploads/generated_work_order_pdfs"
        os.makedirs(wo_dir, exist_ok=True)
        file_path = os.path.join(wo_dir, filename)

        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        relative_url = f"http://localhost:8000/uploads/generated_work_order_pdfs/{filename}"
        db_work_order.preview_file_path = relative_url
        db.commit()

    return db_work_order

@app.get("/work-orders/view", response_model=List[schemas.WorkOrder])
def read_work_orders(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_work_orders(db)


@app.post("/amendment-orders/", response_model=schemas.AMOrder)
def create_am_order(
    amendment_no: str = Form(...),
    reference_no: str = Form(...),
    reference_type: str = Form(...),
    date: str = Form(...),
    company_name: str = Form(...),
    address: str = Form(...),
    req_rec_date: str = Form(...),
    subject: str = Form(...),
    category_date: str = Form(...),
    email: str = Form(...),
    content_text: str = Form(...),
    read_as: str = Form(...),
    file: UploadFile = File(None),  # PDF blob from frontend
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # Create AMOrderCreate object
    am_order = schemas.AMOrderCreate(
        amendment_no=amendment_no,
        reference_no=reference_no,
        reference_type=reference_type,
        date=date,
        company_name=company_name,
        address=address,
        req_rec_date=req_rec_date,
        subject=subject,
        category_date=category_date,
        email=email,
        content_text=content_text,
        read_as=read_as,
        created_by=user['username']
    )

    # Save to DB
    db_am_order = crud.create_am_order(db=db, am_order=am_order)

    # ✅ Save uploaded PDF if provided
    if file and file.content_type == "application/pdf":
        safe_no = amendment_no.replace("/", "_")
        filename = f"amendment_order_{safe_no}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        ao_dir = "uploads/generated_amendment_order_pdfs"
        os.makedirs(ao_dir, exist_ok=True)
        file_path = os.path.join(ao_dir, filename)

        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        relative_url = f"http://localhost:8000/{ao_dir}/{filename}"
        db_am_order.preview_file_path = relative_url
        db.commit()

    return db_am_order


@app.get("/amendment-orders/view", response_model=List[schemas.AMOrder])
def list_am_orders(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_am_orders(db)

@app.get("/token/ping")
def ping(current_user: User = Depends(get_current_user)):
    return {"message": "OK"}

@app.get("/dashboard", response_model=schemas.DashboardCounts)
def get_dashboard_data(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_dashboard_counts(db)

# Upload Directories
SIGNED_PO_UPLOAD_DIR = "uploads/signed_pos"
SIGNED_WO_UPLOAD_DIR = "uploads/signed_wos"
SIGNED_AM_UPLOAD_DIR = "uploads/signed_Ams"
# Ensure upload directory exists
CUSTOM_UPLOAD_DIR = "uploads/custom_uploads"
TOTAL_ORDERS_UPLOAD_DIR = "uploads/total_orders_files"
os.makedirs(TOTAL_ORDERS_UPLOAD_DIR, exist_ok=True)
os.makedirs(CUSTOM_UPLOAD_DIR, exist_ok=True)

os.makedirs(SIGNED_PO_UPLOAD_DIR, exist_ok=True)
os.makedirs(SIGNED_WO_UPLOAD_DIR, exist_ok=True)
os.makedirs(SIGNED_AM_UPLOAD_DIR, exist_ok=True)

app.mount("/uploads/signed_pos", StaticFiles(directory=SIGNED_PO_UPLOAD_DIR), name="signed_pos")
app.mount("/uploads/signed_wos", StaticFiles(directory=SIGNED_WO_UPLOAD_DIR), name="signed_wos")
app.mount("/uploads/signed_Ams", StaticFiles(directory=SIGNED_AM_UPLOAD_DIR), name="signed_Ams")
# Serve static files
app.mount("/uploads/custom_uploads", StaticFiles(directory=CUSTOM_UPLOAD_DIR), name="custom_uploads")
app.mount("/uploads/total_orders_files", StaticFiles(directory=TOTAL_ORDERS_UPLOAD_DIR), name="total_orders_files")
# purchase order
GENERATED_PO_DIR = "uploads/generated_po_files"
os.makedirs(GENERATED_PO_DIR, exist_ok=True)
app.mount("/uploads/generated_po_files", StaticFiles(directory=GENERATED_PO_DIR), name="generated_po_files")
# work order
WORK_ORDER_PDF_DIR = "uploads/generated_work_order_pdfs"
os.makedirs(WORK_ORDER_PDF_DIR, exist_ok=True)

app.mount("/uploads/generated_work_order_pdfs", StaticFiles(directory=WORK_ORDER_PDF_DIR), name="generated_work_order_pdfs")
# amendment order
AMENDMENT_ORDER_PDF_DIR = "uploads/generated_amendment_order_pdfs"
os.makedirs(AMENDMENT_ORDER_PDF_DIR, exist_ok=True)

app.mount("/uploads/generated_amendment_order_pdfs", StaticFiles(directory=AMENDMENT_ORDER_PDF_DIR), name="generated_amendment_order_pdfs")


# upload total  
@app.post("/total-orders/{order_id}/upload-docs")
def upload_total_order_docs(
    order_id: int,
    file: UploadFile = File(...),
    back_papers_completed_date: str = Form(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        parsed_date = datetime.strptime(back_papers_completed_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")

    filename = f"total_order_doc_{order_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    file_path = os.path.join(TOTAL_ORDERS_UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    relative_path = f"http://localhost:8000/uploads/total_orders_files/{filename}"

    db.execute(
        update(TotalOrder)
        .where(TotalOrder.id == order_id)
        .values(
            signed_po_path=relative_path,
            signed_po_uploaded_at=datetime.utcnow(),
            bp_date=parsed_date
        )
    )
    db.commit()

    return JSONResponse(content={
        "message": "Total Order document uploaded successfully",
        "file_path": relative_path,
        "bp_date": parsed_date.isoformat()
    })

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

@app.get("/amendment-source-options")
def get_po_wo_numbers(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    po_data = db.query(
        PurchaseOrder.po_number,
        PurchaseOrder.supplier_name,
        PurchaseOrder.supplier_address
    ).all()

    wo_data = db.query(
        WorkOrder.work_order_no,
        WorkOrder.supplier_name,
        WorkOrder.address
    ).all()

    return {
        "purchase_orders": [
            {
                "po_number": po.po_number,
                "supplier_name": po.supplier_name,
                "supplier_address": po.supplier_address
            } for po in po_data
        ],
        "work_orders": [
            {
                "work_order_no": wo.work_order_no,
                "supplier_name": wo.supplier_name,
                "supplier_address": wo.address
            } for wo in wo_data
        ]
    }

@app.get("/total-orders", response_model=List[schemas.TotalOrder])
def fetch_total_orders(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_total_orders(db)


@app.get("/amendment-source-options")
def get_po_wo_numbers(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    # Fetch POs with supplier_address
    po_list = db.query(
        PurchaseOrder.po_number,
        PurchaseOrder.supplier_name,
        PurchaseOrder.supplier_address
    ).all()

    # Fetch WOs with address
    wo_list = db.query(
        WorkOrder.work_order_no,
        WorkOrder.supplier_name,
        WorkOrder.address
    ).all()

    return {
        "purchase_orders": [
            {
                "po_number": po.po_number,
                "supplier_name": po.supplier_name,
                "supplier_address": po.supplier_address  # ✅ keep supplier_address
            }
            for po in po_list
        ],
        "work_orders": [
            {
                "work_order_no": wo.work_order_no,
                "supplier_name": wo.supplier_name,
                "supplier_address": wo.address  # ✅ map WO 'address' to supplier_address
            }
            for wo in wo_list
        ]
    }

# @app.get("/total-orders", response_model=List[schemas.TotalOrder])
# def fetch_total_orders(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
#     return crud.get_all_total_orders(db)


@app.post("/upload-order-file")
def upload_order_file(
    order_number: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    safe_order_number = order_number.replace("/", "_")
    filename = f"order_{safe_order_number}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    full_dir = os.path.join(CUSTOM_UPLOAD_DIR, safe_order_number)
    os.makedirs(full_dir, exist_ok=True)

    file_path = os.path.join(full_dir, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    relative_url = f"http://localhost:8000/uploads/custom_uploads/{safe_order_number}/{filename}"

    uploaded = UploadedOrder(
        order_number=order_number,
        file_name=filename,
        file_path=relative_url
    )
    db.add(uploaded)
    db.commit()

    return JSONResponse(content={"message": "File uploaded successfully", "file_url": relative_url})


@app.get("/uploaded-orders")
def get_uploaded_orders(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    uploads = db.query(UploadedOrder).all()
    return [
        {
            "id": u.id,
            "order_number": u.order_number,
            "file_name": u.file_name,
            "file_path": u.file_path,
            "uploaded_on": u.uploaded_on
        }
        for u in uploads
    ]

@app.post("/suppliers")
def add_supplier(
    supplier: SupplierCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user["role_id"] != 1:
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only")

    new_supplier = Supplier(
        supplier_name=supplier.supplier_name,
        supplier_address=supplier.supplier_address,
        type=''  # Default value
    )
    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)

    return {"message": "Supplier added successfully"}  # ✅ Now no validation error

@app.get("/purchase-orders/{po_id}", response_model=schemas.PurchaseOrder)
def get_purchase_order(po_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    # Fetch PO with related items
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    # Fetch items linked to this PO
    items = db.query(PurchaseOrderItem).filter(PurchaseOrderItem.po_id == po.id).all()
    po.items = items  # ✅ attach items so it's serialized in response

    # Optional: print or log what’s going out for debug
    print("Returning PO:", {
        "id": po.id,
        "po_number": po.po_number,
        "prefix": po.prefix,
        "suffix": po.suffix,
        "project_keyword": po.project_keyword,
        "requester_name": po.requester_name,
        "items_count": len(po.items)
    })

    return po

@app.put("/purchase-orders/{po_id}", response_model=schemas.PurchaseOrder)
async def update_po(
    po_id: int,
    po_number: str = Form(...),
    po_date: str = Form(...),
    supplier_name: str = Form(...),
    supplier_address: str = Form(...),
    indent_date: str = Form(...),
    requester_name: str = Form(...),
    quotation_number: str = Form(None),
    quotation_date: str = Form(None),
    email: str = Form(None),
    dated: str = Form(None),
    total_cost: float = Form(...),
    total_including_gst: float = Form(...),
    delivery_date: str = Form(...),
    payment_terms: str = Form(...),
    delivery_mode: str = Form(...),
    additional_terms: str = Form(None),
    is_asset: bool = Form(False),
    asset_type: str = Form(None),
    include_annexure: bool = Form(False),
    annexure_text: str = Form(None),
    annexure_file_path: str = Form(None),
    project_keyword: str = Form(None),
    prefix: str = Form(None),
    suffix: str = Form(None),
    items: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # 1. Get PO
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    # 2. Ensure directory exists
    pdf_dir = "uploads/generated_po_files"
    os.makedirs(pdf_dir, exist_ok=True)

    # 3. Save PDF
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    pdf_filename = f"generated_po_{po_number.replace('/', '_')}_{timestamp}.pdf"
    pdf_path = os.path.join(pdf_dir, pdf_filename)

    with open(pdf_path, "wb") as f:
      f.write(await file.read())

    base_url = "http://localhost:8000"
    # 4. Update fields
    po.po_number = po_number
    po.po_date = po_date
    po.supplier_name = supplier_name
    po.supplier_address = supplier_address
    po.indent_date = indent_date
    po.requester_name = requester_name
    po.quotation_number = quotation_number
    po.quotation_date = quotation_date
    po.email = email
    po.dated = dated
    po.total_cost = total_cost
    po.total_including_gst = total_including_gst
    po.delivery_date = delivery_date
    po.payment_terms = payment_terms
    po.delivery_mode = delivery_mode
    po.additional_terms = additional_terms
    po.is_asset = is_asset
    po.asset_type = asset_type
    po.include_annexure = include_annexure
    po.annexure_text = annexure_text
    po.annexure_file_path = annexure_file_path
    po.project_keyword = project_keyword
    po.prefix = prefix
    po.suffix = suffix
    po.preview_file_path = f"{base_url}/uploads/generated_po_files/{pdf_filename}"

    # 5. Replace items
    db.query(PurchaseOrderItem).filter(PurchaseOrderItem.po_id == po.id).delete()

    for item in json.loads(items):
        db.add(PurchaseOrderItem(
            po_id=po.id,
            item_description=item['item_description'],
            quantity=item['quantity'],
            unit_price=item['unit_price'],
            item_total=item['item_total'],
            gst=item['gst']
        ))

    db.commit()
    db.refresh(po)
    return po
@app.get("/work-orders/{wo_id}", response_model=schemas.WorkOrder)
def get_work_order(wo_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")
    return wo
@app.put("/work-orders/{wo_id}", response_model=schemas.WorkOrder)
async def update_work_order(
    wo_id: int,
    work_order_no: str = Form(...),
    prefix: str = Form(...),
    suffix: str = Form(...),
    date: str = Form(...),
    quotation_no: str = Form(None),
    quotation_date: str = Form(None),
    email: str = Form(None),
    supplier_name: str = Form(...),
    address: str = Form(...),
    indent_date: str = Form(...),
    requester_name: str = Form(...),
    scope_of_work: str = Form(...),
    value_of_service: int = Form(...),
    tax: int = Form(...),
    duration_of_service: str = Form(...),
    payment_term: str = Form(...),
    deliverables: str = Form(None),
    additional_terms: str = Form(None),
    include_annexure: bool = Form(False),
    annexure_text: str = Form(None),
    annexure_file_path: str = Form(None),
    project_keyword: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    # Save new PDF to correct folder
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_wo_number = work_order_no.replace("/", "_")
    pdf_filename = f"generated_wo_{safe_wo_number}_{timestamp}.pdf"
    pdf_dir = "uploads/generated_work_order_pdfs"
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, pdf_filename)

    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    # Full preview URL (served via /uploads mount)
    preview_url = f"http://localhost:8000/uploads/generated_work_order_pdfs/{pdf_filename}"

    # Update DB fields
    wo.work_order_no = work_order_no
    wo.prefix = prefix
    wo.suffix = suffix
    wo.date = date
    wo.quotation_no = quotation_no
    wo.quotation_date = quotation_date
    wo.email = email
    wo.supplier_name = supplier_name
    wo.address = address
    wo.indent_date = indent_date
    wo.requester_name = requester_name
    wo.scope_of_work = scope_of_work
    wo.value_of_service = value_of_service
    wo.tax = tax
    wo.duration_of_service = duration_of_service
    wo.payment_term = payment_term
    wo.deliverables = deliverables
    wo.additional_terms = additional_terms
    wo.include_annexure = include_annexure
    wo.annexure_text = annexure_text
    wo.annexure_file_path = annexure_file_path
    wo.project_keyword = project_keyword
    wo.preview_file_path = preview_url
    wo.updated_at = datetime.now()

    db.commit()
    db.refresh(wo)
    return wo
@app.get("/amendment-orders/next-no")
def get_next_amendment_no(db: Session = Depends(get_db)):
    last_order = db.query(models.AmendmentOrder).order_by(models.AmendmentOrder.id.desc()).first()
    if last_order and last_order.amendment_no:
        prefix = "AO"
        last_number = int(last_order.amendment_no.replace(prefix, ""))
        next_number = f"{prefix}{last_number + 1:02d}"
    else:
        next_number = "AO01"
    return {"next_amendment_no": next_number}
