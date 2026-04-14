from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import subprocess
import math
import json
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = "super_secret_hostel_key" 

# --- INTELLIGENT URGENCY DETECTOR ---
def analyze_urgency(description, category):
    desc = description.lower()
    
    # Keyword banks
    critical = ['fire', 'spark', 'short circuit', 'blood', 'flood', 'smoke', 'emergency', 'current', 'blast']
    high = ['broken', 'not working', 'urgent', 'stuck', 'smell', 'leak', 'overflow', 'power cut']
    medium = ['slow', 'noise', 'dirty', 'insects', 'fan', 'light', 'dust', 'heat']

    if any(word in desc for word in critical): return 5
    if any(word in desc for word in high): return 4
    if any(word in desc for word in medium): return 3
    
    # Fallback based on category
    if category in ['Electricity', 'Water']: return 3
    return 1 

# --- STUDENT ROUTES ---
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        session['register_number'] = request.form['register_number']
        return redirect(url_for('portal'))
    return render_template('student_login.html')

@app.route('/portal')
def portal():
    if not session.get('register_number'):
        return redirect(url_for('student_login'))
    return render_template('portal.html')

@app.route('/submit', methods=['POST'])
def submit():
    if not session.get('register_number'):
        return redirect(url_for('student_login'))
        
    reg_no = session.get('register_number')
    room = request.form['room']
    cat = request.form['category']
    desc = request.form['description']
    
    auto_urgency = analyze_urgency(desc, cat)
    
    conn = get_db_connection()
    conn.execute('INSERT INTO complaints (register_number, room_number, category, urgency, description) VALUES (?, ?, ?, ?, ?)',
                 (reg_no, room, cat, auto_urgency, desc))
    conn.commit()
    conn.close()
    
    flash("Complaint submitted successfully! Urgency auto-assigned.", "success")
    return redirect(url_for('portal'))

# --- ADMIN ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == 'admin123': 
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash("Incorrect Password!", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

# --- BATCH RESOLVE COMPLAINTS ROUTE ---
@app.route('/batch_close', methods=['POST'])
def batch_close():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Get the array of IDs sent by our Javascript
    closed_ids_json = request.form.get('closed_ids', '[]')
    try:
        closed_ids = json.loads(closed_ids_json)
    except:
        closed_ids = []

    if closed_ids:
        conn = get_db_connection()
        # SQL trick to update multiple rows at once safely
        placeholders = ','.join('?' for _ in closed_ids)
        query = f'UPDATE complaints SET status="Closed" WHERE id IN ({placeholders})'
        conn.execute(query, closed_ids)
        conn.commit()
        conn.close()
        
        flash(f"Successfully resolved {len(closed_ids)} ticket(s).", "success")

    # Redirect back to whatever page they were on
    return redirect(request.referrer or url_for('admin'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Pagination Settings from URL
    try:
        page = int(request.args.get('page', 1))
        per_page_str = request.args.get('per_page', '10')
        per_page = None if per_page_str == 'all' else int(per_page_str)
    except ValueError:
        page, per_page = 1, 10
        per_page_str = '10'

    conn = get_db_connection()
    rows = conn.execute('SELECT id, room_number, category, urgency, age_weeks FROM complaints WHERE status="Pending"').fetchall()
    conn.close()

    input_data = "\n".join([f"{r['id']} {r['room_number']} {r['category']} {r['urgency']} {r['age_weeks']}" for r in rows])
    
    # Run the C++ engine
    process = subprocess.Popen(['./dsa/priority_engine'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    stdout, _ = process.communicate(input=input_data)

    sorted_complaints = []
    for line in stdout.strip().split('\n'):
        if line:
            parts = line.split('|')
            score = int(parts[3])
            
            # Convert numeric score to visual labels
            if score >= 40:
                label, color = "Very High", "danger"
            elif score >= 20:
                label, color = "High", "warning text-dark"
            elif score >= 10:
                label, color = "Medium", "info text-dark"
            else:
                label, color = "Low", "secondary"

            sorted_complaints.append({'id': parts[0], 'room': parts[1], 'category': parts[2], 'label': label, 'color': color})

    total_items = len(sorted_complaints)
    
    # Python List Slicing for Pagination
    if per_page is None:
        display_complaints = sorted_complaints
        total_pages = 1
    else:
        start = (page - 1) * per_page
        end = start + per_page
        display_complaints = sorted_complaints[start:end]
        total_pages = math.ceil(total_items / per_page) if per_page > 0 else 1

    return render_template('admin.html', 
                           complaints=display_complaints, 
                           total=total_items, 
                           page=page, 
                           per_page=per_page_str, 
                           total_pages=total_pages)

if __name__ == '__main__':
    # No need to run init_db() here every time if your database is already set up, 
    # but it is safe to keep it if you want.
    app.run(debug=True)