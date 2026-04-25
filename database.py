import sqlite3

def get_db_connection():
    conn = sqlite3.connect('hostel.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    conn.execute('DROP TABLE IF EXISTS complaints')
    conn.execute('DROP TABLE IF EXISTS workers')
    
    # Create Workers Table
    conn.execute('''
        CREATE TABLE workers (
            id INTEGER PRIMARY KEY,
            role TEXT NOT NULL
        )
    ''')
    
    # Populate exactly 100 workers based on your roles
    for i in range(1, 101):
        if 1 <= i <= 25: role = 'Electrician'
        elif 26 <= i <= 50: role = 'Plumber'
        elif 51 <= i <= 75: role = 'Mess Staff'
        else: role = 'Carpenter'
        conn.execute('INSERT INTO workers (id, role) VALUES (?, ?)', (i, role))

    # Create Complaints Table (Replaced age_weeks with dynamic created_at timestamp)
    conn.execute('''
        CREATE TABLE complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            register_number TEXT NOT NULL,
            email TEXT NOT NULL,
            room_number TEXT NOT NULL,
            category TEXT NOT NULL,
            urgency INTEGER NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Pending',
            worker_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database wiped and initialized for Version 2.0 (Workers & Timestamps).")