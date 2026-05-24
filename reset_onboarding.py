"""
Reset onboarding state for testing
"""
from backend.db.database import engine
from sqlalchemy import text

def reset():
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM onboarding_state"))
        conn.commit()
        print("Onboarding state reset successfully!")

if __name__ == "__main__":
    reset()
