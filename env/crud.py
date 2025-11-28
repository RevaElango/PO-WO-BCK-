from sqlalchemy.orm import Session, joinedload
import schemas, models,re
from datetime import date

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


# -------------------------
# Purchase Orders (PO)
# -------------------------

def get_financial_year() -> str:
    """Get current financial year in YY-YY format (Apr-Mar)"""
    today = date.today()
    if today.month >= 4:
        return f"{today.year % 100:02d}-{(today.year + 1) % 100:02d}"
    else:
        return f"{(today.year - 1) % 100:02d}-{today.year % 100:02d}"


def generate_po_number_atomic(db: Session, prefix: str, suffix: str, final_suffix: str) -> str:
    """
    Generate the next PO number atomically.
    Uses GLOBAL increment across ALL PO numbers for the financial year.
    """
    fy = get_financial_year()
    
    # ✅ STEP 1: Lock and get ALL PO numbers for this financial year (any prefix/suffix)
    # Pattern matches: */*/25-26/*  (anything with this FY in 3rd position)
    existing_pos = db.query(models.PurchaseOrder.po_number).filter(
        models.PurchaseOrder.po_number.like(f"%/%/{fy}/%")
    ).with_for_update().all()
    
    # ✅ STEP 2: Also check total_orders table if it exists
    existing_orders = []
    try:
        # Check if you have a TotalOrders model, adjust the model name as needed
        if hasattr(models, 'TotalOrders'):
            existing_orders = db.query(models.TotalOrders.Order_No).filter(
                models.TotalOrders.Order_No.like(f"%/%/{fy}/%")
            ).with_for_update().all()
        elif hasattr(models, 'TotalOrder'):
            existing_orders = db.query(models.TotalOrder.Order_No).filter(
                models.TotalOrder.Order_No.like(f"%/%/{fy}/%")
            ).with_for_update().all()
    except Exception as e:
        print(f"Warning: Could not query total_orders: {e}")
        existing_orders = []
    
    # ✅ STEP 3: Extract increment numbers from ALL PO numbers
    # Pattern: PREFIX/SUFFIX/FY/INCREMENT or PREFIX/SUFFIX/FY/INCREMENT/FINAL
    # Captures the increment (4th segment)
    pattern = re.compile(
        r'^[^/]+/[^/]+/' + re.escape(fy) + r'/(\d+)(?:/[^/]+)?$'
    )
    
    max_inc = 0
    
    # Check purchase_orders table
    for (po_num,) in existing_pos:
        if po_num:
            match = pattern.match(po_num.strip())
            if match:
                try:
                    inc = int(match.group(1))
                    max_inc = max(max_inc, inc)
                    print(f"Found in purchase_orders: {po_num} -> increment {inc}")
                except ValueError:
                    pass
    
    # Check total_orders table
    for row in existing_orders:
        order_no = row[0] if isinstance(row, tuple) else row.Order_No if hasattr(row, 'Order_No') else str(row)
        if order_no:
            match = pattern.match(str(order_no).strip())
            if match:
                try:
                    inc = int(match.group(1))
                    max_inc = max(max_inc, inc)
                    print(f"Found in total_orders: {order_no} -> increment {inc}")
                except ValueError:
                    pass
    
    # ✅ STEP 4: Calculate next increment (minimum 134)
    next_inc = max(max_inc + 1, 134)
    
    generated = f"{prefix}/{suffix}/{fy}/{next_inc:03d}/{final_suffix}"
    print(f"Generated PO Number: {generated} (max was {max_inc})")
    
    return generated


def create_po(db: Session, po: schemas.PurchaseOrderCreate):
    """
    Create a PurchaseOrder with atomic PO number generation.
    """
    # Resolve project details
    project_no = None
    if po.project_keyword:
        proj = db.query(models.ProjectNoDetails).filter(
            models.ProjectNoDetails.project_keyword == po.project_keyword
        ).first()
        if proj:
            project_no = proj.project_no

    # ✅ GENERATE PO NUMBER ATOMICALLY
    generated_po_number = generate_po_number_atomic(
        db=db,
        prefix=po.prefix or '',
        suffix=po.suffix or '',
        final_suffix=po.final_suffix or 'SPLX'
    )

    # Prepare data
    po_data = po.dict(exclude={"items"})
    po_data["po_number"] = generated_po_number  # ✅ Use generated number
    po_data["project_no"] = project_no

    db_po = models.PurchaseOrder(**po_data)
    db.add(db_po)
    db.flush()

    # Attach items
    db_po.items = [
        models.PurchaseOrderItem(**(item.dict() if hasattr(item, "dict") else item))
        for item in po.items
    ]

    db.commit()
    db.refresh(db_po)
    return db_po


def get_all_pos(db: Session):
    return (
        db.query(models.PurchaseOrder)
        .options(joinedload(models.PurchaseOrder.items))
        .all()
    )


# -------------------------
# Work Orders (WO)
# -------------------------

def generate_wo_number_atomic(db: Session, prefix: str, pi_code: str, final_suffix: str) -> str:
    """
    Generate the next Work Order number atomically.
    Uses GLOBAL increment across ALL work orders for the financial year.
    Format: PREFIX/PICODE/FY/NNN/SUFFIX
    """
    fy = get_financial_year()
    
    # Get ALL work order numbers for this financial year (any prefix/suffix)
    existing_wos = db.query(models.WorkOrder.work_order_no).filter(
        models.WorkOrder.work_order_no.like(f"%/%/{fy}/%")
    ).with_for_update().all()
    
    # Also check total_orders table
    existing_orders = []
    try:
        if hasattr(models, 'TotalOrders'):
            existing_orders = db.query(models.TotalOrders.Order_No).filter(
                models.TotalOrders.Order_No.like(f"%/%/{fy}/%")
            ).with_for_update().all()
        elif hasattr(models, 'TotalOrder'):
            existing_orders = db.query(models.TotalOrder.Order_No).filter(
                models.TotalOrder.Order_No.like(f"%/%/{fy}/%")
            ).with_for_update().all()
    except Exception as e:
        print(f"Warning: Could not query total_orders: {e}")
    
    # Also check purchase_orders table (shared increment)
    existing_pos = []
    try:
        existing_pos = db.query(models.PurchaseOrder.po_number).filter(
            models.PurchaseOrder.po_number.like(f"%/%/{fy}/%")
        ).with_for_update().all()
    except Exception as e:
        print(f"Warning: Could not query purchase_orders: {e}")
    
    # Pattern: PREFIX/PICODE/FY/INCREMENT or PREFIX/PICODE/FY/INCREMENT/FINAL
    # Captures the increment (4th segment)
    pattern = re.compile(
        r'^[^/]+/[^/]+/' + re.escape(fy) + r'/(\d+)(?:/[^/]+)?$'
    )
    
    max_inc = 0
    
    # Check work_orders table
    for (wo_num,) in existing_wos:
        if wo_num:
            match = pattern.match(wo_num.strip())
            if match:
                try:
                    inc = int(match.group(1))
                    max_inc = max(max_inc, inc)
                except ValueError:
                    pass
    
    # Check total_orders table
    for row in existing_orders:
        order_no = row[0] if isinstance(row, tuple) else getattr(row, 'Order_No', str(row))
        if order_no:
            match = pattern.match(str(order_no).strip())
            if match:
                try:
                    inc = int(match.group(1))
                    max_inc = max(max_inc, inc)
                except ValueError:
                    pass
    
    # Check purchase_orders table
    for (po_num,) in existing_pos:
        if po_num:
            match = pattern.match(po_num.strip())
            if match:
                try:
                    inc = int(match.group(1))
                    max_inc = max(max_inc, inc)
                except ValueError:
                    pass
    
    # Calculate next increment (minimum 134)
    next_inc = max(max_inc + 1, 134)
    
    generated = f"{prefix}/{pi_code}/{fy}/{next_inc:03d}/{final_suffix}"
    print(f"Generated Work Order Number: {generated} (max was {max_inc})")
    
    return generated


def create_work_order(db: Session, work_order: schemas.WorkOrderCreate, generate_number: bool = True):
    """
    Create a WorkOrder with atomic number generation.
    """
    # Resolve project details
    project_no = None
    if work_order.project_keyword:
        proj = db.query(models.ProjectNoDetails).filter(
            models.ProjectNoDetails.project_keyword == work_order.project_keyword
        ).first()
        if proj:
            project_no = proj.project_no

    wo_data = work_order.dict(exclude={"items"})
    wo_data["project_no"] = project_no
    wo_data["created_by"] = work_order.created_by

    # ✅ Generate work order number atomically if requested
    if generate_number and hasattr(work_order, 'prefix') and hasattr(work_order, 'pi_code'):
        generated_wo_number = generate_wo_number_atomic(
            db=db,
            prefix=work_order.prefix or '',
            pi_code=work_order.pi_code or '',
            final_suffix=work_order.suffix or 'SPLX'
        )
        wo_data["work_order_no"] = generated_wo_number

    db_work_order = models.WorkOrder(**wo_data)
    db.add(db_work_order)
    db.flush()

    # Attach items
    db_work_order.items = [
        models.WorkOrderItem(
            item_description=it.item_description,
            quantity=int(it.quantity),
            unit_price=it.unit_price,
            item_total=it.item_total,
            gst=it.gst,
        )
        for it in work_order.items
    ]

    db.commit()
    db.refresh(db_work_order)
    return db_work_order


def get_all_work_orders(db: Session):
    return (
        db.query(models.WorkOrder)
        .options(joinedload(models.WorkOrder.items))
        .all()
    )


# -------------------------
# Amendment Orders (AM)
# -------------------------
def create_am_order(db: Session, am_order: schemas.AMOrderCreate):
    amendment_no = get_latest_amendment_no(db)
    am_data = am_order.dict(exclude={"amendment_no"})
    db_am_order = models.AmendmentOrder(
        amendment_no=amendment_no,
        **am_data
    )
    db.add(db_am_order)
    db.commit()
    db.refresh(db_am_order)
    return db_am_order


# -------------------------
# Totals / Dashboard
# -------------------------
def get_all_total_orders(db: Session):
    return db.query(models.TotalOrder).all()


def get_all_am_orders(db: Session):
    return db.query(models.AmendmentOrder).all()


def get_dashboard_counts(db: Session):
    po_count = db.query(models.PurchaseOrder).count()
    wo_count = db.query(models.WorkOrder).count()
    am_count = db.query(models.AmendmentOrder).count()
    total = db.query(models.TotalOrder).count()
    return {
        "purchase_orders": po_count,
        "work_orders": wo_count,
        "amendment_orders": am_count,
        "total_orders": total
    }
# -------------------------
# Helpers
# -------------------------
def mark_reference_amended(db: Session, reference_no: str):
    """
    Sets the amendment='Yes' for the referenced PO or WO.
    """
    if reference_no.startswith("PO:"):
        po_number = reference_no.replace("PO:", "").strip()
        db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_number == po_number).update({"amendment": "Yes"})
    elif reference_no.startswith("WO:"):
        wo_number = reference_no.replace("WO:", "").strip()
        db.query(models.WorkOrder).filter(models.WorkOrder.work_order_no == wo_number).update({"amendment": "Yes"})
    db.commit()


def get_latest_amendment_no(db: Session) -> str:
    latest_order = (
        db.query(models.AmendmentOrder)
        .filter(models.AmendmentOrder.amendment_no.like("AO%"))
        .order_by(models.AmendmentOrder.id.desc())
        .first()
    )
    if latest_order and latest_order.amendment_no:
        try:
            last_num = int(latest_order.amendment_no[2:])
            next_num = last_num + 1
        except ValueError:
            next_num = 1
    else:
        next_num = 1
    return f"AO{next_num:02d}"


def create_project_no(db: Session, data: schemas.ProjectNoCreate):
    entry = models.ProjectNoDetails(
        project_no=data.project_no,
        project_keyword=data.project_keyword,
        pn_prefix=data.pn_prefix,
        pn_suffix=data.pn_suffix
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
def create_supplier(db: Session, supplier: schemas.SupplierCreate):
    """
    Add a new supplier to the suppliers table.
    """
    db_supplier = models.Supplier(
        supplier_name=supplier.supplier_name,
        supplier_address=supplier.supplier_address,
        type=supplier.type
    )
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


def get_suppliers(db: Session):
    """
    Retrieve all suppliers from the suppliers table.
    """
    return db.query(models.Supplier).order_by(models.Supplier.id.desc()).all()


def delete_supplier(db: Session, supplier_id: int):
    """
    Delete a supplier by ID.
    """
    supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if supplier:
        db.delete(supplier)
        db.commit()
        return True
    return False