from app.core.database import get_db
from app.core.security import hash_password
from app.models.admin import Admin
from app.models import *  # saare models load ho jayen

db = next(get_db())

email = "admin@gmail.com"      # apna email likho
password = "12345678"       # apna strong password likho

if db.query(Admin).filter(Admin.email == email).first():
    print("Admin already exists")
else:
    db.add(Admin(name="Admin", email=email.lower(), password=hash_password(password)))
    db.commit()
    print("Admin created")