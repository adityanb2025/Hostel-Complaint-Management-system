import sqlite3
import random
from datetime import datetime, timedelta

def seed_database():
    conn = sqlite3.connect('hostel.db')
    cursor = conn.cursor()

    categories = ['Electricity', 'Water', 'WiFi', 'Room', 'Food']
    urgencies = [1, 2, 3, 4, 5]
    
    worker_map = {
        'Electricity': (1, 25),
        'WiFi': (1, 25),
        'Water': (26, 50),
        'Food': (51, 75),
        'Room': (76, 100)
    }

    complaints = []
    print("Generating exactly 10,000 PENDING complaints for maximum wow factor...")
    
    for i in range(10000):
        reg_no = f"23BCE{random.randint(1000, 9999)}"
        email = f"student{i}@vitstudent.ac.in"
        room = f"{random.choice(['A', 'B', 'C', 'D'])}{random.randint(100, 500)}"
        cat = random.choice(categories)
        urg = random.choice(urgencies)
        desc = f"Dummy description for {cat} issue."
        
        # NEW: Forcing every single ticket to be 'Pending' so the Admin sees exactly 10,000
        status = 'Pending' 
        
        # Pick a worker based on category
        worker_id = random.randint(worker_map[cat][0], worker_map[cat][1])
        
        # Generate a random past date (0 to 30 days ago) for automatic age calculation
        past_date = datetime.now() - timedelta(days=random.randint(0, 30))
        created_at = past_date.strftime('%Y-%m-%d %H:%M:%S')

        complaints.append((reg_no, email, room, cat, urg, desc, status, worker_id, created_at))

    cursor.executemany('''
        INSERT INTO complaints (register_number, email, room_number, category, urgency, description, status, worker_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', complaints)

    conn.commit()
    conn.close()
    print("✅ Successfully seeded exactly 10,000 PENDING complaints distributed among 100 workers!")

if __name__ == "__main__":
    seed_database()