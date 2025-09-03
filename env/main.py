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
from passlib.context import CryptContext
import secrets,smtplib 
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decimal import Decimal, ROUND_HALF_UP


from models import User
BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Secret key and algorithm
SECRET_KEY = "k3#4f%9*bsAY32%tio$9.015gBS"
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
    
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

@app.post("/login", response_model=TokenResponse)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # Step 1: Detect if password is in plain text and needs hashing
    if not db_user.password_hash.startswith("$2b$"):
        # Compare plain passwords
        if db_user.password_hash == user.password:
            # Hash and update in DB
            db_user.password_hash = hash_password(user.password)
            db.commit()
        else:
            raise HTTPException(status_code=400, detail="Invalid email or password")
    else:
        # Step 2: Normal bcrypt password verification
        if not verify_password(user.password, db_user.password_hash):
            raise HTTPException(status_code=400, detail="Invalid email or password")

    # Step 3: Generate JWT token
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
@app.get("/get-email-from-token")
def get_email_from_token(token: str):
    email = reset_tokens.get(token)
    if not email:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    return {"email": email}


@app.post("/change-password")
def change_password(email: str = Form(...), new_password: str = Form(...), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(new_password)
    db.commit()

    return {"message": "Password changed successfully"}


reset_tokens = {}

# SMTP Configuration
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587
SENDER_EMAIL = "Automation@iitmpravartak.net"
SENDER_PASSWORD = "Itjwh$1%852"  # 🔐 Replace with a secure method in production

@app.post("/send-reset-link")
async def send_reset_link(email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    # Generate a secure token
    token = secrets.token_urlsafe(32)
    reset_tokens[token] = email

    # Construct reset URL
    reset_url = f"http://localhost:4200/change-password?token={token}"
    subject = "Password Reset Request"

    # HTML content with button
    html_body = f"""
    <html>
      <body>
        <p>Dear {user.name if hasattr(user, 'name') else 'user'},</p>
        <p>You have requested to reset your password. Please click the button below to proceed:</p>
        <a href="{reset_url}" 
           style="background-color: #007BFF; color: white; padding: 10px 20px; text-decoration: none; 
                  border-radius: 5px; display: inline-block;">
           Reset Password
        </a>
        <p>If you did not request this, you can ignore this email.</p>
        <p>Best regards,<br>IT Team</p>
      </body>
    </html>
    """

    # Create email message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = email

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())

        return {"message": "Reset link sent successfully"}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/purchase-orders/", response_model=schemas.PurchaseOrder)
async def create_po(
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
    additional_terms: str = Form(None),
    delivery_mode: str = Form(...),
    is_asset: bool = Form(False),
    asset_type: str = Form(None),
    include_annexure: bool = Form(False),
    annexure_text: str = Form(None),
    annexure_file_path: str = Form(None),
    project_keyword: str = Form(None),   # may be ID
    budget_head: str = Form(None),
    prefix: str = Form(None),
    suffix: str = Form(None),
    final_suffix: str = Form(None),
    items: str = Form(...),  # JSON string
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    import json

    # --- Parse items JSON safely ---
    try:
        items_list = json.loads(items)
        if not isinstance(items_list, list):
            raise ValueError("items must be a JSON array")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid items JSON: {e}")

    # --- ✅ Resolve project_keyword like update_po ---
    project_no = None
    resolved_keyword = None

    if project_keyword and project_keyword.isdigit():
        project_detail = (
            db.query(ProjectNoDetails)
            .filter(ProjectNoDetails.id == int(project_keyword))
            .first()
        )
        if project_detail:
            resolved_keyword = project_detail.project_keyword
            project_no = project_detail.project_no
    else:
        resolved_keyword = project_keyword

    # --- Build schema ---
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
        project_keyword=resolved_keyword,   # ✅ always text
        project_no=project_no,              # ✅ stored correctly
        budget_head=budget_head,
        prefix=prefix,
        suffix=suffix,
        final_suffix=final_suffix,
        items=items_list,
        created_by=user['username']
    )

    db_po = crud.create_po(db=db, po=po_data)

    # --- Save file if present ---
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

        relative_url = f"{BASE_URL}/uploads/generated_po_files/{filename}"
        db_po.preview_file_path = relative_url
        db.commit()

    return db_po

@app.get("/purchase-orders/view", response_model=List[schemas.PurchaseOrder])
def read_pos(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_pos(db)

@app.post("/work-orders/", response_model=schemas.WorkOrder)
def create_work_order(
    # Core identifiers
    work_order_no: str = Form(...),
    prefix: str = Form(...),
    suffix: str = Form(...),

    # Dates (as strings; Pydantic will coerce)
    date: str = Form(...),
    quotation_date: Optional[str] = Form(None),
    indent_date: str = Form(...),

    # Optional toggles
    quotation_no: Optional[str] = Form(None),
    email: Optional[str] = Form(None),

    # Parties/terms
    supplier_name: str = Form(...),
    address: str = Form(...),
    requester_name: str = Form(...),
    duration_of_service: str = Form(...),
    payment_term: str = Form(...),
    deliverables: str = Form(...),
    additional_terms: Optional[str] = Form(None),

    # numbers
    tax: float = Form(0),

    # Annexure
    include_annexure: bool = Form(False),
    annexure_text: Optional[str] = Form(None),
    annexure_file_path: Optional[str] = Form(None),

    # Project ref
    project_keyword: Optional[str] = Form(None),  # may be ID
    budget_head: str = Form(None),

    # Totals
    total_cost: float = Form(...),
    total_including_gst: float = Form(...),

    # Items
    items: str = Form(...),

    # PDF is REQUIRED
    file: UploadFile = File(...),

    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # --- Validate & parse items ---
    if not items or not items.strip():
        raise HTTPException(status_code=400, detail="Items field is missing or empty.")

    try:
        ilist = json.loads(items)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for items.")

    if not isinstance(ilist, list) or not all(isinstance(x, dict) for x in ilist):
        raise HTTPException(status_code=400, detail="Items should be a JSON array of objects.")

    # --- Compute scope_of_work and value_of_service ---
    scope_of_work = ", ".join(
        s for s in (str(i.get("item_description", "")).strip() for i in ilist) if s
    )

    value_of_service = sum(
        Decimal(str(i.get("quantity") or 0)) * Decimal(str(i.get("unit_price") or 0))
        for i in ilist
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    tax_dec = Decimal(str(tax or 0)).quantize(Decimal("0.00"))
    total_cost_dec = Decimal(str(total_cost)).quantize(Decimal("0.01"))
    total_incl_gst_dec = Decimal(str(total_including_gst)).quantize(Decimal("0.01"))

    # --- ✅ Resolve project_keyword if it’s an ID ---
    resolved_keyword = None
    project_no = None

    if project_keyword and project_keyword.isdigit():
        project_detail = (
            db.query(ProjectNoDetails)
            .filter(ProjectNoDetails.id == int(project_keyword))
            .first()
        )
        if project_detail:
            resolved_keyword = project_detail.project_keyword
            project_no = project_detail.project_no
    else:
        resolved_keyword = project_keyword

    # --- Build schema ---
    wo = schemas.WorkOrderCreate(
        work_order_no=work_order_no,
        date=date,
        quotation_no=quotation_no or None,
        email=email or None,
        quotation_date=quotation_date or None,
        requester_name=requester_name,
        indent_date=indent_date,

        scope_of_work=scope_of_work,
        value_of_service=value_of_service,

        duration_of_service=duration_of_service,
        tax=tax_dec,
        payment_term=payment_term,
        supplier_name=supplier_name,
        address=address,
        deliverables=deliverables,
        additional_terms=additional_terms or None,

        include_annexure=include_annexure,
        annexure_text=annexure_text or None,
        annexure_file_path=annexure_file_path or None,

        project_keyword=resolved_keyword,   # ✅ resolved text, not ID
        project_no=project_no,              # ✅ now stored
        budget_head=budget_head,

        total_cost=total_cost_dec,
        total_including_gst=total_incl_gst_dec,

        items=ilist,
        created_by=user["username"],
    )

    # --- Persist ---
    db_work_order = crud.create_work_order(db=db, work_order=wo)

    # --- Save the PDF ---
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="A PDF (application/pdf) is required for 'file'.")

    safe_no = work_order_no.replace("/", "_")
    filename = f"generated_wo_{safe_no}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    wo_dir = os.path.join("uploads", "generated_work_order_pdfs")
    os.makedirs(wo_dir, exist_ok=True)
    disk_path = os.path.join(wo_dir, filename)

    with open(disk_path, "wb") as buffer:
        buffer.write(file.file.read())

    relative_url = f"/uploads/generated_work_order_pdfs/{filename}"
    full_url = f"{BASE_URL}{relative_url}" if BASE_URL else relative_url

    db_work_order.preview_file_path = full_url
    db.add(db_work_order)
    db.commit()
    db.refresh(db_work_order)

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

        relative_url = f"{BASE_URL}/{ao_dir}/{filename}"
        db_am_order.preview_file_path = relative_url
        db.commit()

    return db_am_order


@app.get("/amendment-orders/view", response_model=List[schemas.AMOrder])
def list_am_orders(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return crud.get_all_am_orders(db)



@app.put("/amendment-orders/{am_id}", response_model=schemas.AMOrder)
async def update_am_order(
    am_id: int,
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
    file: UploadFile = File(None),  # Optional PDF
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    am_order = db.query(AmendmentOrder).filter(AmendmentOrder.id == am_id).first()
    if not am_order:
        raise HTTPException(status_code=404, detail="Amendment Order not found")

    # Update fields
    am_order.amendment_no = amendment_no
    am_order.reference_no = reference_no
    am_order.reference_type = reference_type
    am_order.date = date
    am_order.company_name = company_name
    am_order.address = address
    am_order.req_rec_date = req_rec_date
    am_order.subject = subject
    am_order.category_date = category_date
    am_order.email = email
    am_order.content_text = content_text
    am_order.read_as = read_as
    am_order.updated_at = datetime.utcnow()

    # ✅ If file provided, save and update preview_file_path
    if file and file.content_type == "application/pdf":
        safe_no = amendment_no.replace("/", "_")
        filename = f"amendment_order_{safe_no}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        ao_dir = "uploads/generated_amendment_order_pdfs"
        os.makedirs(ao_dir, exist_ok=True)
        file_path = os.path.join(ao_dir, filename)

        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        preview_path = f"{BASE_URL}/{ao_dir}/{filename}"
        am_order.preview_file_path = preview_path

    db.commit()
    db.refresh(am_order)
    return am_order


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

    relative_path = f"{BASE_URL}/uploads/total_orders_files/{filename}"

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
    relative_path = f"{BASE_URL}/uploads/signed_pos/{filename}"
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
    relative_path = f"{BASE_URL}/uploads/signed_wos/{filename}"
    db.execute(update(WorkOrder).where(WorkOrder.id == wo_id).values(signed_wo_path=relative_path, signed_wo_uploaded_at=datetime.utcnow()))
    db.commit()
    return JSONResponse(content={"message": "Signed WO uploaded successfully", "signed_wo_path": relative_path})

# Upload Signed AM
@app.post("/Amendment-orders/{Am_id}/upload-signed-Am")
def upload_signed_Am(
    Am_id: int,
    file: UploadFile = File(...),
    back_papers_completed_date: str = Form(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # ✅ Check file type
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # ✅ Parse date
    try:
        parsed_date = datetime.strptime(back_papers_completed_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")

    # ✅ Save file
    filename = f"signed_Am_{Am_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    file_path = os.path.join(SIGNED_AM_UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    relative_path = f"{BASE_URL}/uploads/signed_Ams/{filename}"

    # ✅ Update DB: signed_Am_path, signed_Am_uploaded_at, and bp_date
    db.execute(
        update(AmendmentOrder)
        .where(AmendmentOrder.id == Am_id)
        .values(
            signed_Am_path=relative_path,
            signed_Am_uploaded_at=datetime.utcnow(),
            bp_date=parsed_date  # ✅ This must exist in your table
        )
    )
    db.commit()

    return JSONResponse(content={
        "message": "Signed AM uploaded successfully",
        "signed_Am_path": relative_path,
        "bp_date": parsed_date.isoformat()
    })


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
            "pn_prefix": project.pn_prefix,
            "pn_suffix": project.pn_suffix
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

    relative_url = f"{BASE_URL}/uploads/custom_uploads/{safe_order_number}/{filename}"

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
def get_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # Fetch PO with related items
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    # Fetch items linked to this PO
    items = db.query(PurchaseOrderItem).filter(PurchaseOrderItem.po_id == po.id).all()
    po.items = items  # ✅ attach items so it's serialized in response

    # ✅ Fetch project_no from project_no_details
    project_detail = (
        db.query(ProjectNoDetails)
        .filter(ProjectNoDetails.project_keyword == po.project_keyword)
        .first()
    )
    po.project_no = project_detail.project_no if project_detail else None

    # Debug logging (optional)
    print("Returning PO:", {
        "id": po.id,
        "po_number": po.po_number,
        "prefix": po.prefix,
        "suffix": po.suffix,
        "project_keyword": po.project_keyword,
        "project_no": po.project_no,
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
    project_keyword: str = Form(None),   # may come as ID from UI
    project_no: str = Form(None),        # may come null
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

    base_url = BASE_URL

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

    # ✅ Resolve project_keyword if UI sent ID
    if project_keyword and project_keyword.isdigit():
        project_detail = (
            db.query(ProjectNoDetails)
            .filter(ProjectNoDetails.id == int(project_keyword))
            .first()
        )
        if project_detail:
            po.project_keyword = project_detail.project_keyword
            po.project_no = project_detail.project_no
        else:
            po.project_keyword = None
            po.project_no = None
    else:
        # If frontend sent actual keyword string, use it directly
        po.project_keyword = project_keyword
        po.project_no = project_no

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
def get_work_order(
    wo_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # Fetch work order
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    # ✅ Fetch project_no from project_no_details
    project_detail = (
        db.query(ProjectNoDetails)
        .filter(ProjectNoDetails.project_keyword == wo.project_keyword)
        .first()
    )
    wo.project_no = project_detail.project_no if project_detail else None

    # Debug logging (optional)
    print("Returning WO:", {
        "id": wo.id,
        "work_order_no": wo.work_order_no,
        "project_keyword": wo.project_keyword,
        "project_no": wo.project_no,
        "requester_name": wo.requester_name,
    })

    return wo

@app.put("/work-orders/{wo_id}", response_model=schemas.WorkOrder)
async def update_work_order(
    wo_id: int,
    work_order_no: str = Form(...),
    prefix: str = Form(...),
    suffix: str = Form(...),
    date: str = Form(...),
    quotation_no: Optional[str] = Form(None),
    quotation_date: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    supplier_name: str = Form(...),
    address: str = Form(...),
    indent_date: str = Form(...),
    requester_name: str = Form(...),
    tax: int = Form(...),
    duration_of_service: str = Form(...),
    payment_term: str = Form(...),
    deliverables: Optional[str] = Form(None),
    additional_terms: Optional[str] = Form(None),
    include_annexure: bool = Form(False),
    annexure_text: Optional[str] = Form(None),
    annexure_file_path: Optional[str] = Form(None),
    project_keyword: Optional[str] = Form(None),   # may come as ID from UI
    budget_head: Optional[str] = Form(None),

    # NEW: totals (optional)
    total_cost: Optional[float] = Form(None),
    total_including_gst: Optional[float] = Form(None),

    # NEW: items payload (JSON string)
    items: Optional[str] = Form(None),

    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    # --- Save new PDF ---
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_wo_number = work_order_no.replace("/", "_")
    pdf_filename = f"generated_wo_{safe_wo_number}_{timestamp}.pdf"
    pdf_dir = "uploads/generated_work_order_pdfs"
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, pdf_filename)

    try:
        with open(pdf_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write PDF: {e}")

    preview_url = f"{BASE_URL}/uploads/generated_work_order_pdfs/{pdf_filename}"

    # --- Update WO header fields ---
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
    wo.tax = tax
    wo.duration_of_service = duration_of_service
    wo.payment_term = payment_term
    wo.deliverables = deliverables
    wo.additional_terms = additional_terms
    wo.include_annexure = include_annexure
    wo.annexure_text = annexure_text
    wo.annexure_file_path = annexure_file_path
    wo.budget_head = budget_head 
    wo.preview_file_path = preview_url
    wo.updated_at = datetime.now()

    # ✅ Resolve project_keyword if UI sent ID
    if project_keyword and project_keyword.isdigit():
        project_detail = (
            db.query(ProjectNoDetails)
            .filter(ProjectNoDetails.id == int(project_keyword))
            .first()
        )
        if project_detail:
            wo.project_keyword = project_detail.project_keyword
            wo.project_no = project_detail.project_no
        else:
            wo.project_keyword = None
            wo.project_no = None
    else:
        wo.project_keyword = project_keyword
        # don’t override project_no unless explicitly passed
        # (so it keeps old value if frontend doesn’t send it)

    # --- Replace items if provided ---
    parsed_items: Optional[List[dict]] = None
    if items is not None:
        try:
            parsed_items = json.loads(items)
            if not isinstance(parsed_items, list):
                raise ValueError("items must be a JSON array")
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid items JSON: {e}")

        db.query(WorkOrderItem).filter(WorkOrderItem.wo_id == wo_id).delete(synchronize_session=False)

        new_rows = []
        for it in parsed_items:
            desc = (it.get("item_description") or "").strip()
            qty = float(it.get("quantity") or 0)
            unit = float(it.get("unit_price") or 0)
            gst = float(it.get("gst") or 0)
            total = float(it.get("item_total") or (qty * unit * (1 + gst/100.0)))

            new_rows.append(
                WorkOrderItem(
                    wo_id=wo_id,
                    item_description=desc,
                    quantity=qty,
                    unit_price=unit,
                    gst=gst,
                    item_total=total,
                )
            )

        if new_rows:
            db.bulk_save_objects(new_rows)

        if total_cost is None or total_including_gst is None:
            excl, incl = 0.0, 0.0
            for it in parsed_items:
                qty = float(it.get("quantity") or 0)
                unit = float(it.get("unit_price") or 0)
                gst = float(it.get("gst") or 0)
                subtotal = qty * unit
                excl += subtotal
                incl += subtotal * (1 + gst/100.0)
            if total_cost is None:
                total_cost = round(excl, 2)
            if total_including_gst is None:
                total_including_gst = round(incl, 2)

    # --- Persist totals ---
    if total_cost is not None:
        wo.total_cost = float(total_cost)
    if total_including_gst is not None:
        wo.total_including_gst = float(total_including_gst)

    try:
        db.commit()
        db.refresh(wo)
    except Exception as e:
        db.rollback()
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    return wo

# ✅ Place this route FIRST
@app.get("/amendment-orders/next-no")
def get_next_amendment_no(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    last_order = db.query(models.AmendmentOrder).order_by(models.AmendmentOrder.id.desc()).first()
    if last_order and last_order.amendment_no:
        prefix = "AO"
        last_number = int(last_order.amendment_no.replace(prefix, ""))
        next_number = f"{prefix}{last_number + 1:02d}"
    else:
        next_number = "AO01"
    return {"next_amendment_no": next_number}


@app.get("/amendment-orders/{am_id}", response_model=schemas.AMOrder)
def get_amendment_order(am_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    am = db.query(AmendmentOrder).filter(AmendmentOrder.id == am_id).first()
    if not am:
        raise HTTPException(status_code=404, detail="Amendment Order not found")
    return am


@app.post("/project-no-details", response_model=schemas.ProjectNoResponse)
def create_project_no_detail(
    payload: schemas.ProjectNoCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # Only admins can create project number details
    if user["role_id"] != 1:
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only")

    return crud.create_project_no(db, payload)


