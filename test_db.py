from sqlalchemy import text

from database.session import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        print("✅ PostgreSQL Connected Successfully!")
        print(result.scalar())

except Exception as e:
    print("❌ Database Connection Failed")
    print(e)