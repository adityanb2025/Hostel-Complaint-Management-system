from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import subprocess
import math
import json
import smtplib
from email.mime.text import MIMEText
import threading
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = "super_secret_hostel_key" 

# --- EMAIL CONFIGURATION ---
SENDER_EMAIL = "YOUR_NEW_GMAIL_ADDRESS@gmail.com" # <--- REPLACE WITH YOUR PROJECT GMAIL
APP_PASSWORD = "ofpwpkibanrsrwyt" 

def send_registration_email(recipient_email, ticket_id, room):
    try:
        msg = MIMEText(f"Hello,\n\nYour hostel room complaint for Room {room} (Ticket #{ticket_id}) has been successfully registered.\n\nOur admin team will review the issue and work to resolve it as soon as possible.\n\nThank you,\nHostel Management")
        msg['Subject'] = f"Registered: Hostel Complaint #{ticket_id}"
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        print(f"✅ REGISTRATION EMAIL SENT TO: {recipient_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}. Error: {e}")

def send_verification_email(recipient_email, ticket_id, room, host_url):
    try:
        html = f"""
        <html><body>
        <p>Hello,</p>
        <p>The admin team has marked your hostel complaint <b>#{ticket_id} (Room {room})</b> as resolved.</p>
        <p>Please confirm if the issue is actually fixed:</p>
        <br>
        <a href="{host_url}verify/{ticket_id}/yes" style="padding: 10px 20px; background: #198754; color: white; text-decoration: none; border-radius: 5px; font-family: sans-serif; font-weight: bold;">✓ Yes, it is fixed</a>
        <br><br><br>
        <a href="{host_url}verify/{ticket_id}/no" style="padding: 10px 20px; background: #dc3545; color: white; text-decoration: none; border-radius: 5px; font-family: sans-serif; font-weight: bold;">✕ No, I still need help</a>
        <br><br>
        <p>Thank you,<br>Hostel Management</p>
        </body></html>
        """
        msg = MIMEText(html, 'html')
        msg['Subject'] = f"Action Required: Is Complaint #{ticket_id} fixed?"
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        print(f"✅ VERIFICATION EMAIL SENT TO: {recipient_email}")
    except Exception as e:
        print(f"❌ Failed to send verification to {recipient_email}. Error: {e}")

# --- INTELLIGENT URGENCY DETECTOR ---
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
    email = request.form['email'] 
    room = request.form['room']
    cat = request.form['category']
    desc = request.form['description']
    
    auto_urgency = analyze_urgency(desc, cat)
    
    conn = get_db_connection()
    cursor = conn.execute('INSERT INTO complaints (register_number, email, room_number, category, urgency, description) VALUES (?, ?, ?, ?, ?, ?)',
                 (reg_no, email, room, cat, auto_urgency, desc))
    ticket_id = cursor.lastrowid 
    conn.commit()
    conn.close()
    
    # Send email in the background to prevent 502 Bad Gateway timeouts
    email_thread = threading.Thread(target=send_registration_email, args=(email, ticket_id, room))
    email_thread.start()
    
    flash("Complaint submitted successfully! Confirmation email sent.", "success")
    return redirect(url_for('portal'))

@app.route('/verify/<int:ticket_id>/<action>')
def verify_ticket(ticket_id, action):
    conn = get_db_connection()
    if action == 'yes':
        conn.execute('UPDATE complaints SET status="Closed" WHERE id=?', (ticket_id,))
        msg = "Ticket Closed. Thank you for confirming!"
        color = "success"
    elif action == 'no':
        conn.execute('UPDATE complaints SET status="Reopened" WHERE id=?', (ticket_id,))
        msg = "Ticket Reopened. The admin has been notified and it is back at the top of their queue."
        color = "danger"
    conn.commit()
    conn.close()
    
    html = f"""
    <html><head><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"></head>
    <body class="bg-dark text-white d-flex align-items-center justify-content-center" style="height: 100vh;">
        <div class="text-center p-5 rounded-4 shadow" style="background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
            <h2 class="text-{color} fw-bold mb-3">{msg}</h2>
            <p class="opacity-75">You can safely close this browser tab.</p>
        </div>
    </body></html>
    """
    return html

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

@app.route('/batch_close', methods=['POST'])
def batch_close():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    closed_ids_json = request.form.get('closed_ids', '[]')
    try:
        closed_ids = json.loads(closed_ids_json)
    except:
        closed_ids = []

    if closed_ids:
        conn = get_db_connection()
        placeholders = ','.join('?' for _ in closed_ids)
        
        cursor = conn.execute(f'SELECT id, email, room_number FROM complaints WHERE id IN ({placeholders})', closed_ids)
        resolved_tickets = cursor.fetchall()
        
        query = f'UPDATE complaints SET status="Pending Student Confirmation" WHERE id IN ({placeholders})'
        conn.execute(query, closed_ids)
        conn.commit()
        conn.close()

        host_url = request.host_url
        print("\n" + "="*50)
        for ticket in resolved_tickets:
            # Send verification emails in the background to prevent 502 timeouts
            email_thread = threading.Thread(target=send_verification_email, args=(ticket['email'], ticket['id'], ticket['room_number'], host_url))
            email_thread.start()
        print("="*50 + "\n")
        
        flash(f"Tickets updated. Verification emails sent to {len(closed_ids)} student(s).", "success")

    return redirect(request.referrer or url_for('admin'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        page = int(request.args.get('page', 1))
        per_page_str = request.args.get('per_page', '10')
        per_page = None if per_page_str == 'all' else int(per_page_str)
    except ValueError:
        page, per_page = 1, 10
        per_page_str = '10'

    filter_category = request.args.get('category', '')
    filter_urgency = request.args.get('urgency', '')
    search_id = request.args.get('ticket_id', '').strip()
    
    search_id_clean = search_id.replace('#', '')

    query = 'SELECT id, room_number, category, urgency, age_weeks, status FROM complaints WHERE status IN ("Pending", "Reopened")'
    params = []

    if search_id_clean.isdigit():
        query += ' AND id = ?'
        params.append(int(search_id_clean))
    if filter_category:
        query += ' AND category = ?'
        params.append(filter_category)

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    status_map = {str(r['id']): r['status'] for r in rows}

    input_data = []
    for r in rows:
        effective_urgency = r['urgency'] + 10 if r['status'] == 'Reopened' else r['urgency']
        input_data.append(f"{r['id']} {r['room_number']} {r['category']} {effective_urgency} {r['age_weeks']}")
    
    input_text = "\n".join(input_data)
    
    sorted_complaints = []
    
    if input_text:
        process = subprocess.Popen(['./dsa/priority_engine'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        stdout, _ = process.communicate(input=input_text)

        for line in stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                ticket_id = parts[0]
                score = int(parts[3])
                
                if score >= 40:
                    label, color = "Very High", "danger"
                elif score >= 20:
                    label, color = "High", "warning text-dark"
                elif score >= 10:
                    label, color = "Medium", "info text-dark"
                else:
                    label, color = "Low", "secondary"

                if filter_urgency and label != filter_urgency:
                    continue

                actual_status = status_map.get(ticket_id, "Pending")
                sorted_complaints.append({'id': ticket_id, 'room': parts[1], 'category': parts[2], 'label': label, 'color': color, 'status': actual_status})

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
                           search_id=search_id)

if __name__ == '__main__':
    app.run(debug=True)