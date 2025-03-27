import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.db_service import DBService

def main():
    print("Initializing database...")
    db = DBService()
    db.initialize_db()
    print("Database initialization complete!")

if __name__ == "__main__":
    main() 