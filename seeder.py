import sqlite3
import random

categories = ['Electricity', 'Water', 'Food', 'WiFi', 'Room']
urgencies = [1, 3, 4, 5]

def seed_data():
    conn = sqlite3.connect('hostel.db')
    cur = conn.cursor()
    
    print("Generating 10,000 complaints...")
    data = []
    for _ in range(10000):
        dummy_email = f"student{random.randint(1000, 9999)}@example.com"
        
        data.append((
            f"REG{random.randint(1000, 9999)}", 
            dummy_email,
            f"{random.randint(100, 500)}",      
            random.choice(categories),
            random.choice(urgencies),
            "Auto-generated issue for testing.",
            random.randint(0, 4) 
        ))
    
    cur.executemany('''
        INSERT INTO complaints (register_number, email, room_number, category, urgency, description, age_weeks) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', data)
    
    conn.commit()
    conn.close()
    print("Successfully seeded 10,000 records.")

if __name__ == "__main__":
    seed_data()