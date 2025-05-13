from sqlalchemy.orm import Session
import schemas,models

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_po(db: Session, po: schemas.PurchaseOrderCreate):
    db_po = models.PurchaseOrder(**po.dict())
    db.add(db_po)
    db.commit()
    db.refresh(db_po)
    return db_po

def get_all_pos(db: Session):
    return db.query(models.PurchaseOrder).all()

def get_po_by_id(db: Session, po_id: int):
    return db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == po_id).first()
