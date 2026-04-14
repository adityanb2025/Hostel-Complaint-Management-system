from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import subprocess
import math
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = "super_secret_hostel_key" 

def analyze_urgency(description, category):
    desc = description.lower()
    critical = ['fire', 'spark', 'short circuit', 'blood', 'flood', 'smoke', 'emergency', 'current', 'blast']
    high = ['broken', 'not working', 'urgent', 'stuck', 'smell', 'leak', 'overflow', 'power cut']
    medium = ['slow', 'noise', 'dirty', 'insects', 'fan', 'light', 'dust', 'heat']

    if any(word in desc for word in critical): return 5
    if any(word in desc for word in high): return 4
    if any(word in desc for word in medium): return 3
    if category in ['Electricity', 'Water']: return 3
    return 1 

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

# --- NEW RESOLVE COMPLAINT ROUTE ---
@app.route('/close/<int:id>', methods=['POST'])
def close_complaint(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('UPDATE complaints SET status="Closed" WHERE id=?', (id,))
    conn.commit()
    conn.close()

    flash(f"Ticket #{id} has been successfully resolved.", "success")
    return redirect(url_for('admin'))

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
    app.run(debug=True)