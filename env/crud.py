from sqlalchemy.orm import Session, joinedload
import schemas, models

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


# -------------------------
# Purchase Orders (PO)
# -------------------------
def create_po(db: Session, po: schemas.PurchaseOrderCreate):
    """
    Create a PurchaseOrder and its items.
    ProjectNoDetails does not have `project_no`; if you want a display value,
    you can derive it from pn_prefix/pn_suffix. Otherwise set None.
    """
    project_no = None
    proj = db.query(models.ProjectNoDetails).filter(
        models.ProjectNoDetails.project_keyword == po.project_keyword
    ).first()
    if proj:
        project_no = proj.project_no   # ✅ store exact project_no from DB


    # Exclude items for the parent row; attach them afterward
    po_data = po.dict(exclude={"items"})
    po_data["project_no"] = project_no  # OK if the column exists; None is allowed if nullable

    db_po = models.PurchaseOrder(**po_data)
    db.add(db_po)
    db.flush()  # get db_po.id

    # Attach items via relationship (FK auto-populated)
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
def create_work_order(db: Session, work_order: schemas.WorkOrderCreate):
    """
    Create a WorkOrder and its items.
    Do NOT read `project.project_no` (it doesn't exist in ProjectNoDetails).
    """
    project_no = None
    if work_order.project_keyword:
        proj = db.query(models.ProjectNoDetails).filter(
            models.ProjectNoDetails.project_keyword == work_order.project_keyword
        ).first()
        if proj:
            # Example: derive a display value; adjust as needed or keep None.
            project_no = proj.project_no

    wo_data = work_order.dict(exclude={"items"})
    wo_data["project_no"] = project_no
    wo_data["created_by"] = work_order.created_by

    db_work_order = models.WorkOrder(**wo_data)
    db.add(db_work_order)
    db.flush()  # get db_work_order.id

    # Attach items via relationship (FK auto-populated)
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