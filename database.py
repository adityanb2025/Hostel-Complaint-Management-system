import sqlite3

def get_db_connection():
    conn = sqlite3.connect('hostel.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            register_number TEXT NOT NULL,
            email TEXT NOT NULL,
            room_number TEXT NOT NULL,
            category TEXT NOT NULL,
            urgency INTEGER NOT NULL,
            description TEXT,
            age_weeks INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Pending'
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized with Email support.")