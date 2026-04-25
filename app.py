from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import subprocess
import math
import json
import smtplib
import re
from datetime import datetime
from email.mime.text import MIMEText
import threading
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = "super_secret_hostel_key" 

SENDER_EMAIL = "VIT.hostelcomplaints@gmail.com"
APP_PASSWORD = "ofpwpkibanrsrwyt" 

def send_registration_email(recipient_email, ticket_id, room):
    try:
        msg = MIMEText(f"Hello,\n\nYour hostel room complaint for Room {room} (Ticket #{ticket_id}) has been successfully registered.\n\nOur system has assigned it to a specialized worker. We will work to resolve it as soon as possible.\n\nThank you,\nHostel Management")
        msg['Subject'] = f"Registered: Hostel Complaint #{ticket_id}"
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def send_verification_email(recipient_email, ticket_id, room, host_url):
    try:
        html = f"""
        <html><body>
        <p>Hello,</p>
        <p>Our maintenance worker has marked your hostel complaint <b>#{ticket_id} (Room {room})</b> as resolved.</p>
        <p>Please confirm if the issue is actually fixed:</p>
        <br><a href="{host_url}verify/{ticket_id}/yes" style="padding: 10px 20px; background: #198754; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">✓ Yes, it is fixed</a>
        <br><br><br><a href="{host_url}verify/{ticket_id}/no" style="padding: 10px 20px; background: #dc3545; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">✕ No, I still need help</a>
        </body></html>
        """
        msg = MIMEText(html, 'html')
        msg['Subject'] = f"Action Required: Is Complaint #{ticket_id} fixed?"
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"❌ Failed to send verification: {e}")

def analyze_urgency(description, category):
    desc = description.lower()
    critical = ['fire', 'spark', 'short circuit', 'blood', 'flood', 'smoke', 'emergency', 'blast']
    high = ['broken', 'not working', 'urgent', 'stuck', 'smell', 'leak', 'overflow', 'power cut']
    medium = ['slow', 'noise', 'dirty', 'insects', 'fan', 'light', 'dust', 'heat']
    if any(word in desc for word in critical): return 5
    if any(word in desc for word in high): return 4
    if any(word in desc for word in medium): return 3
    if category in ['Electricity', 'Water']: return 3
    return 1 

def get_best_worker(category):
    worker_map = {'Electricity': (1,25), 'WiFi': (1,25), 'Water': (26,50), 'Food': (51,75), 'Room': (76,100), 'Other': (76,100)}
    start_id, end_id = worker_map[category]
    conn = get_db_connection()
    query = '''
        SELECT w.id, COUNT(c.id) as task_count 
        FROM workers w LEFT JOIN complaints c ON w.id = c.worker_id AND c.status IN ('Pending', 'Reopened')
        WHERE w.id BETWEEN ? AND ?
        GROUP BY w.id ORDER BY task_count ASC LIMIT 1
    '''
    worker_id = conn.execute(query, (start_id, end_id)).fetchone()['id']
    conn.close()
    return worker_id

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        reg_no = request.form['register_number'].strip().upper()
        
        pattern = r'^(\d{2})[A-Z]{3}\d{4}$'
        match = re.match(pattern, reg_no)
        
        if not match:
            flash("Invalid registration number", "danger")
            return redirect(url_for('student_login'))
            
        join_year = int(match.group(1))
        current_year = datetime.now().year % 100
        
        if not (current_year - 5 <= join_year <= current_year):
            flash("Invalid registration number", "danger")
            return redirect(url_for('student_login'))

        session['register_number'] = reg_no
        return redirect(url_for('portal'))
        
    return render_template('student_login.html')

@app.route('/portal')
def portal():
    if not session.get('register_number'): return redirect(url_for('student_login'))
    return render_template('portal.html')

@app.route('/submit', methods=['POST'])
def submit():
    if not session.get('register_number'): return redirect(url_for('student_login'))
    reg_no, email = session.get('register_number'), request.form['email']
    room, cat, desc = request.form['room'], request.form['category'], request.form['description']
    
    conn = get_db_connection()
    
    active_check = conn.execute("SELECT id FROM complaints WHERE register_number=? AND category=? AND status IN ('Pending', 'Reopened')", (reg_no, cat)).fetchone()
    if active_check:
        conn.close()
        flash(f"Strict Lockout: You already have an active complaint for '{cat}'. Please wait for it to be resolved before submitting another.", "danger")
        return redirect(url_for('portal'))

    auto_urgency = analyze_urgency(desc, cat)
    assigned_worker = get_best_worker(cat) 
    
    cursor = conn.execute('INSERT INTO complaints (register_number, email, room_number, category, urgency, description, worker_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (reg_no, email, room, cat, auto_urgency, desc, assigned_worker))
    ticket_id = cursor.lastrowid 
    conn.commit()
    conn.close()
    
    threading.Thread(target=send_registration_email, args=(email, ticket_id, room)).start()
    
    flash("Complaint submitted!", "success")
    return redirect(url_for('portal'))

@app.route('/verify/<int:ticket_id>/<action>')
def verify_ticket(ticket_id, action):
    conn = get_db_connection()
    if action == 'yes':
        conn.execute('UPDATE complaints SET status="Closed" WHERE id=?', (ticket_id,))
        msg, color = "Ticket Closed. Thank you!", "success"
    else:
        conn.execute('UPDATE complaints SET status="Reopened" WHERE id=?', (ticket_id,))
        msg, color = "Ticket Reopened. Esculated to top priority.", "danger"
    conn.commit()
    conn.close()
    return f"<html><body style='background:#121212;color:white;text-align:center;padding:50px;'><h2>{msg}</h2><p>You can close this tab.</p></body></html>"

@app.route('/worker_login', methods=['GET', 'POST'])
def worker_login():
    if request.method == 'POST':
        worker_id = request.form.get('worker_id')
        if worker_id.isdigit() and 1 <= int(worker_id) <= 100:
            session['worker_id'] = int(worker_id)
            return redirect(url_for('worker_dashboard'))
        flash("Invalid Worker ID. Must be 1-100.", "danger")
    return render_template('worker_login.html')

@app.route('/worker')
def worker_dashboard():
    if not session.get('worker_id'): return redirect(url_for('worker_login'))
    wid = session['worker_id']
    
    try:
        page = int(request.args.get('page', 1))
        per_page_str = request.args.get('per_page', '10')
        per_page = None if per_page_str == 'all' else int(per_page_str)
    except ValueError:
        page, per_page = 1, 10
        per_page_str = '10'

    conn = get_db_connection()
    query = '''SELECT id, room_number, category, urgency, status, worker_id, 
               CAST((julianday('now') - julianday(created_at)) / 7 AS INTEGER) as age_weeks 
               FROM complaints WHERE status IN ("Pending", "Reopened") AND worker_id = ?'''
    rows = conn.execute(query, (wid,)).fetchall()
    conn.close()

    input_data = [f"{r['id']} {r['room_number']} {r['category']} {r['urgency'] + 10 if r['status'] == 'Reopened' else r['urgency']} {r['age_weeks']}" for r in rows]
    sorted_complaints = []
    
    if input_data:
        process = subprocess.Popen(['./dsa/priority_engine'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        stdout, _ = process.communicate(input="\n".join(input_data))
        for line in stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                sorted_complaints.append({'id': parts[0], 'room': parts[1], 'category': parts[2]})

    total_items = len(sorted_complaints)
    if per_page is None:
        display_complaints = sorted_complaints
        total_pages = 1
    else:
        start = (page - 1) * per_page
        end = start + per_page
        display_complaints = sorted_complaints[start:end]
        total_pages = math.ceil(total_items / per_page) if per_page > 0 else 1

    return render_template('worker.html', complaints=display_complaints, wid=wid, 
                           page=page, per_page=per_page_str, total_pages=total_pages, total_items=total_items)

@app.route('/worker_batch_complete', methods=['POST'])
def worker_batch_complete():
    if not session.get('worker_id'): return redirect(url_for('worker_login'))
    
    completed_ids_json = request.form.get('completed_ids', '[]')
    try:
        completed_ids = json.loads(completed_ids_json)
    except:
        completed_ids = []

    if completed_ids:
        conn = get_db_connection()
        placeholders = ','.join('?' for _ in completed_ids)
        
        cursor = conn.execute(f'SELECT id, email, room_number FROM complaints WHERE id IN ({placeholders})', completed_ids)
        completed_tickets = cursor.fetchall()
        
        query = f'UPDATE complaints SET status="Pending Student Confirmation" WHERE id IN ({placeholders})'
        conn.execute(query, completed_ids)
        conn.commit()
        conn.close()

        host_url = request.host_url
        for ticket in completed_tickets:
            threading.Thread(target=send_verification_email, args=(ticket['email'], ticket['id'], ticket['room_number'], host_url)).start()
        
        flash(f"{len(completed_ids)} ticket(s) marked complete. Verification emails sent.", "success")

    return redirect(request.referrer or url_for('worker_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == 'admin123': 
            session['logged_in'] = True
            return redirect(url_for('admin'))
        flash("Incorrect Password!", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

@app.route('/reassign_worker', methods=['POST'])
def reassign_worker():
    ticket_id = request.form['ticket_id']
    new_worker = request.form['new_worker']
    conn = get_db_connection()
    conn.execute('UPDATE complaints SET worker_id=?, status="Pending" WHERE id=?', (new_worker, ticket_id))
    conn.commit()
    conn.close()
    flash(f"Ticket #{ticket_id} reassigned to Worker #{new_worker} and marked as Pending.", "success")
    return redirect(url_for('admin'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    try:
        page = int(request.args.get('page', 1))
        per_page_str = request.args.get('per_page', '10')
        per_page = None if per_page_str == 'all' else int(per_page_str)
    except ValueError:
        page, per_page = 1, 10
        per_page_str = '10'

    filter_category = request.args.get('category', '')
    filter_urgency = request.args.get('urgency', '')
    filter_worker = request.args.get('worker_id', '')
    search_id = request.args.get('ticket_id', '').strip()
    search_id_clean = search_id.replace('#', '')

    query = '''SELECT id, room_number, category, urgency, status, worker_id, 
               CAST((julianday('now') - julianday(created_at)) / 7 AS INTEGER) as age_weeks 
               FROM complaints WHERE status IN ("Pending", "Reopened")'''
    params = []

    if search_id_clean.isdigit():
        query += ' AND id = ?'
        params.append(int(search_id_clean))
    if filter_category:
        query += ' AND category = ?'
        params.append(filter_category)
    if filter_worker:
        query += ' AND worker_id = ?'
        params.append(int(filter_worker))

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    status_map = {str(r['id']): (r['status'], r['worker_id']) for r in rows}
    input_data = [f"{r['id']} {r['room_number']} {r['category']} {r['urgency'] + 10 if r['status'] == 'Reopened' else r['urgency']} {r['age_weeks']}" for r in rows]
    
    sorted_complaints = []
    if input_data:
        process = subprocess.Popen(['./dsa/priority_engine'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        stdout, _ = process.communicate(input="\n".join(input_data))
        for line in stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                tid = parts[0]
                score = int(parts[3])
                
                # NEW ADJUSTED CURVE
                if score >= 45: label, color = "Very High", "danger"
                elif score >= 30: label, color = "High", "warning text-dark"
                elif score >= 15: label, color = "Medium", "info text-dark"
                else: label, color = "Low", "secondary"

                if filter_urgency and label != filter_urgency:
                    continue

                actual_status, wid = status_map.get(tid, ("Pending", "Unknown"))
                sorted_complaints.append({'id': tid, 'room': parts[1], 'category': parts[2], 'label': label, 'color': color, 'status': actual_status, 'worker_id': wid})

    total_items = len(sorted_complaints)
    
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
                           total_pages=total_pages,
                           filter_category=filter_category,
                           filter_urgency=filter_urgency,
                           filter_worker=filter_worker,
                           search_id=search_id)

@app.route('/admin/analysis')
def admin_analysis():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    conn = get_db_connection()
    cat_data = conn.execute('SELECT category, COUNT(*) as c FROM complaints WHERE status IN ("Pending", "Reopened") GROUP BY category').fetchall()
    urg_data = conn.execute('SELECT urgency, COUNT(*) as c FROM complaints WHERE status IN ("Pending", "Reopened") GROUP BY urgency').fetchall()
    conn.close()
    
    chart_data = {
        'cats': [row['category'] for row in cat_data], 'cat_counts': [row['c'] for row in cat_data],
        'urgs': [f"Level {row['urgency']}" for row in urg_data], 'urg_counts': [row['c'] for row in urg_data]
    }
    return render_template('analysis.html', chart_data=chart_data)

if __name__ == '__main__':
    app.run(debug=True)