from sqlalchemy.orm import Session

from app.models.admin import Admin


class AdminRepository:

    @staticmethod
    def get_by_email(db: Session, email: str, lock: bool = False):
        query = db.query(Admin).filter(Admin.email == email)
        if lock:
            query = query.with_for_update()
        return query.first()

    @staticmethod
    def get_by_id(db: Session, admin_id: int):
        return db.query(Admin).filter(Admin.id == admin_id).first()
    