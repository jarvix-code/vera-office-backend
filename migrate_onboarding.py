"""
Migration script to add onboarding_chat_data column
"""
from backend.db.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("PRAGMA table_info(onboarding_state)"))
        columns = [row[1] for row in result]
        
        if 'onboarding_chat_data' not in columns:
            print("Adding onboarding_chat_data column...")
            conn.execute(text("ALTER TABLE onboarding_state ADD COLUMN onboarding_chat_data JSON"))
            conn.commit()
            print("Column added successfully!")
        else:
            print("Column already exists.")

if __name__ == "__main__":
    migrate()
