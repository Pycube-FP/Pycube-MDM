from services.db_service import DBService

def migrate():
    """Add EOL fields to devices table"""
    db_service = DBService()
    connection = db_service.get_connection()
    cursor = connection.cursor()
    
    try:
        # Add EOL fields to devices table
        cursor.execute("""
            ALTER TABLE devices
            ADD COLUMN eol_date DATE AFTER purchase_date,
            ADD COLUMN eol_status ENUM('Active', 'Warning', 'Critical', 'Expired') 
                DEFAULT 'Active' AFTER eol_date,
            ADD COLUMN eol_notes TEXT AFTER eol_status
        """)
        
        connection.commit()
        print("Successfully added EOL fields to devices table")
    except Exception as e:
        print(f"Error adding EOL fields: {e}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    migrate() 