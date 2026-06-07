import sys
import os

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine
from app.models.paper_trading import PaperPortfolio

def verify_all():
    print("Starting database verification...")
    
    try:
        with engine.connect() as conn:
            # 1. Basic connectivity
            result = conn.execute(text("SELECT 1")).scalar()
            print(f"[OK] Basic Connectivity: OK (Result: {result})")

            # 2. pgvector verification
            # Verify the extension exists
            vector_check = conn.execute(text(
                "SELECT extname FROM pg_extension WHERE extname = 'vector'"
            )).fetchone()
            if vector_check:
                print("[OK] pgvector Extension: OK (Installed and Active)")
            else:
                print("[X] pgvector Extension: MISSING")
                
            # 3. Paper Trading Loop Table Access
            # We attempt to query the table just to ensure it exists and is accessible
            # by the SQLAlchemy ORM connection
            try:
                # Limit 1 just to see if table is accessible
                from sqlalchemy.orm import Session
                with Session(engine) as session:
                    session.query(PaperPortfolio).limit(1).all()
                print("[OK] Paper Trading DB Access: OK")
            except Exception as e:
                print(f"[X] Paper Trading DB Access Failed: {e}")
                
            print("\n[OK] All database connection tests completed!")

    except Exception as e:
        print(f"\n[X] Database connection failed!\nError Details: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_all()
