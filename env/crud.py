from sqlalchemy.orm import Session
import schemas,models

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_po(db: Session, po: schemas.PurchaseOrderCreate):
    # ✅ Step 1: Lookup project_no using project_keyword
    project_detail = db.query(models.ProjectNoDetails).filter(
        models.ProjectNoDetails.project_keyword == po.project_keyword
    ).first()
    project_no = project_detail.project_no if project_detail else None  # <- FIXED HERE

    # ✅ Step 2: Prepare PO data (excluding items)
    po_data = po.dict(exclude={"items"})
    po_data["project_no"] = project_no

    # ✅ Step 3: Create and save
    db_po = models.PurchaseOrder(**po_data)
    db_po.items = [
    models.PurchaseOrderItem(**(item.dict() if hasattr(item, 'dict') else item))
    for item in po.items
]


    db.add(db_po)
    db.commit()
    db.refresh(db_po)
    return db_po


def get_all_pos(db: Session):
    return db.query(models.PurchaseOrder).all()

# def get_po_by_id(db: Session, po_id: int):
#     return db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == po_id).first()

def create_work_order(db: Session, work_order: schemas.WorkOrderCreate):
    db_work_order = models.WorkOrder(**work_order.dict())
    db.add(db_work_order)
    db.commit()
    db.refresh(db_work_order)
    return db_work_order

def get_all_work_orders(db: Session):
    return db.query(models.WorkOrder).all()

# ✅ Fixed AM Order CRUD functions (correct model name used)
def create_am_order(db: Session, am_order: schemas.AMOrderCreate):
    db_am_order = models.AmendmentOrder(**am_order.dict())  # ✅ use AmendmentOrder
    db.add(db_am_order)
    db.commit()
    db.refresh(db_am_order)
    return db_am_order

def get_all_am_orders(db: Session):
    return db.query(models.AmendmentOrder).all()  # ✅ use AmendmentOrder

def get_dashboard_counts(db: Session):
    po_count = db.query(models.PurchaseOrder).count()
    wo_count = db.query(models.WorkOrder).count()
    am_count = db.query(models.AmendmentOrder).count()
    total = po_count + wo_count + am_count
    return {
        "purchase_orders": po_count,
        "work_orders": wo_count,
        "amendment_orders": am_count,
        "total_orders": total
    }
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
