from sqlalchemy import text
from app.core.database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Database Connected Successfully!")
        print(result.scalar())

except Exception as e:
    print("Database Connection Failed:", e)


# python test_db.py   db connnection test camand