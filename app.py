from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import mysql.connector
from mysql.connector import Error
import bcrypt
import csv
import io
from io import BytesIO
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'group4_secret_key'

def get_connection():
    try:
        return mysql.connector.connect(
            host='localhost',
            user='root',
            password='srvc2016',
            database='bank_management'
        )
    except Error as e:
        print("Database error:", e)
        return None

@app.before_request
def clear_old_sessions():
    if 'user' in session and 'id' not in session['user']:
        session.pop('user', None)
        flash("Session expired. Please log in again.", "warning")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        is_staff = request.form.get('loginType') == 'on'
        user_id = request.form['userId']
        password = request.form['password'].encode()
        conn = get_connection()
        if conn:
            cur = conn.cursor(dictionary=True)
            if is_staff:
                cur.execute("SELECT * FROM staff_users WHERE staff_id=%s", (user_id,))
                user = cur.fetchone()
                if user and bcrypt.checkpw(password, user['password'].encode()):
                    session['user'] = {
                        'id': user['staff_id'],
                        'name': user['full_name'],
                        'role': user['role'],
                        'type': 'staff'
                    }
                    flash(f"Welcome, {user['full_name']}!", "success")
                    return redirect(url_for('dashboard'))
            else:
                cur.execute("SELECT * FROM customer_users WHERE user_id=%s", (user_id,))
                user = cur.fetchone()
                if user and bcrypt.checkpw(password, user['password'].encode()):
                    session['user'] = {
                        'id': user['user_id'],
                        'name': user['full_name'],
                        'type': 'customer',
                        'email': user['email']  
                    }
                    flash(f"Welcome, {user['full_name']}!", "success")
                    return redirect(url_for('dashboard'))
            cur.close()
            conn.close()
        flash("Invalid credentials.", "danger")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        is_staff = request.form.get('signupType') == 'on'
        user_id = request.form['userId']
        password = bcrypt.hashpw(request.form['password'].encode(), bcrypt.gensalt()).decode()
        full_name = request.form['fullName']
        email = request.form['email']
        conn = get_connection()
        if conn:
            cur = conn.cursor()
            if is_staff:
                role = request.form['role']
                cur.execute("INSERT INTO staff_users (staff_id, password, full_name, email, role) VALUES (%s, %s, %s, %s, %s)",
                            (user_id, password, full_name, email, role))
                flash("Staff registered!", "success")
            else:
                cur.execute("INSERT INTO customer_users (user_id, password, full_name, email) VALUES (%s, %s, %s, %s)",
                            (user_id, password, full_name, email))
                flash("Customer registered!", "success")
            conn.commit()
            cur.close()
            conn.close()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out!", "info")
    return redirect(url_for('home'))

@app.route('/clear_session')
def clear_session():
    session.clear()
    flash("Session cleared. Log in again.", "info")
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']
    if 'id' not in user:
        return redirect(url_for('login'))

    conn = get_connection()
    if not conn:
        flash("Database error.", "danger")
        return redirect(url_for('home'))

    cur = conn.cursor(dictionary=True)
    data = {}
    active_form = request.args.get('form')

    if request.method == 'POST':
        if user['type'] == 'customer':
            if 'open_account' in request.form:
                cur.execute("SELECT COUNT(*) AS cnt FROM accounts WHERE user_id=%s", (user['id'],))
                if cur.fetchone()['cnt'] > 0:
                    flash("You already have an account!", "danger")
                else:
                    account_type = request.form['account_type']
                    initial_deposit = float(request.form['initial_deposit'])
                    aadhaar = request.form['aadhaar']
                    pan = request.form['pan']
                    address = request.form['address']

                    if not (aadhaar.isdigit() and len(aadhaar) == 12):
                        flash("Invalid Aadhaar number.", "danger")
                    elif not (len(pan) == 10 and pan[:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()):
                        flash("Invalid PAN format.", "danger")
                    elif not address.strip():
                        flash("Address is required.", "danger")
                    else:
                        cur.execute("SELECT IFNULL(MAX(account_no), 0) + 1 AS next_no FROM accounts")
                        next_no = cur.fetchone()['next_no']
                        cur.execute(
                            "INSERT INTO accounts (account_no, user_id, account_type, balance, aadhaar, pan, address, status) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active')",
                            (next_no, user['id'], account_type, initial_deposit, aadhaar, pan, address)
                        )
                        if initial_deposit > 0:
                            cur.execute(
                                "INSERT INTO transactions (account_no, txn_type, amount, balance_after, remarks) "
                                "VALUES (%s, 'Deposit', %s, %s, 'Account Opening')",
                                (next_no, initial_deposit, initial_deposit)
                            )
                        conn.commit()
                        flash(f"Account {next_no} opened successfully!", "success")

            elif 'deposit' in request.form:
                amount = float(request.form['amount'])
                cur.execute("SELECT account_no, balance FROM accounts WHERE user_id=%s", (user['id'],))
                acct = cur.fetchone()
                new_bal = float(acct['balance']) + amount
                cur.execute("UPDATE accounts SET balance=%s WHERE account_no=%s", (new_bal, acct['account_no']))
                cur.execute(
                    "INSERT INTO transactions (account_no, txn_type, amount, balance_after, remarks) "
                    "VALUES (%s, 'Deposit', %s, %s, 'Cash Deposit')",
                    (acct['account_no'], amount, new_bal)
                )
                conn.commit()
                flash(f"₹{amount} deposited!", "success")

            elif 'withdraw' in request.form:
                amount = float(request.form['amount'])
                cur.execute("SELECT account_no, balance FROM accounts WHERE user_id=%s", (user['id'],))
                acct = cur.fetchone()
                current_bal = float(acct['balance'])
                if current_bal < amount:
                    flash("Insufficient balance!", "danger")
                else:
                    new_bal = current_bal - amount
                    cur.execute("UPDATE accounts SET balance=%s WHERE account_no=%s", (new_bal, acct['account_no']))
                    cur.execute(
                        "INSERT INTO transactions (account_no, txn_type, amount, balance_after, remarks) "
                        "VALUES (%s, 'Withdrawal', %s, %s, 'Cash Withdrawal')",
                        (acct['account_no'], amount, new_bal)
                    )
                    conn.commit()
                    flash(f"₹{amount} withdrawn!", "success")

            elif 'fixed_deposit' in request.form:
                principal = float(request.form['principal'])
                tenure = int(request.form['tenure'])
                cur.execute("SELECT account_no, balance FROM accounts WHERE user_id=%s", (user['id'],))
                acct = cur.fetchone()
                current_bal = float(acct['balance'])
                if current_bal < principal:
                    flash("Insufficient balance for FD!", "danger")
                else:
                    maturity = datetime.now() + timedelta(days=tenure * 30)
                    interest = principal * 0.06 * tenure / 12
                    maturity_amt = principal + interest
                    cur.execute(
                        "INSERT INTO fixed_deposits (account_no, principal, tenure_months, interest_rate, maturity_date, maturity_amount) "
                        "VALUES (%s, %s, %s, 6.0, %s, %s)",
                        (acct['account_no'], principal, tenure, maturity.date(), maturity_amt)
                    )
                    new_bal = current_bal - principal
                    cur.execute("UPDATE accounts SET balance=%s WHERE account_no=%s", (new_bal, acct['account_no']))
                    conn.commit()
                    flash(f"FD created! Maturity: ₹{maturity_amt:.2f}", "success")

            elif 'apply_loan' in request.form:
                loan_type = request.form['loan_type']
                principal = float(request.form['principal'])
                tenure = int(request.form['tenure'])
                rates = {'Home Loan': 8.0, 'Car Loan': 9.5, 'Education Loan': 7.5, 'Personal Loan': 12.0}
                interest_rate = rates.get(loan_type, 8.0)
                cur.execute(
                    "INSERT INTO loan_requests (user_id, loan_type, principal_amount, tenure_months, interest_rate) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (user['id'], loan_type, principal, tenure, interest_rate)
                )
                conn.commit()
                flash("Loan request submitted!", "success")

            elif 'transfer_money' in request.form:
                try:
                    from_acc = int(request.form['from_account'])
                    to_acc = int(request.form['to_account_no'])
                    amount = float(request.form['amount'])

                    if from_acc == to_acc:
                        flash("Cannot transfer to your own account.", "danger")
                        return redirect(url_for('dashboard', form='transfer'))

                    if amount <= 0:
                        flash("Amount must be positive.", "danger")
                        return redirect(url_for('dashboard', form='transfer'))

                    cur.execute("SELECT balance, user_id FROM accounts WHERE account_no=%s", (from_acc,))
                    sender = cur.fetchone()
                    if not sender or sender['user_id'] != user['id']:
                        flash("Invalid sender account.", "danger")
                        return redirect(url_for('dashboard', form='transfer'))

                    if float(sender['balance']) < amount:
                        flash("Insufficient balance!", "danger")
                        return redirect(url_for('dashboard', form='transfer'))

                    cur.execute("SELECT balance FROM accounts WHERE account_no=%s", (to_acc,))
                    receiver = cur.fetchone()
                    if not receiver:
                        flash("Receiver account not found.", "danger")
                        return redirect(url_for('dashboard', form='transfer'))

                    new_sender_bal = float(sender['balance']) - amount
                    cur.execute("UPDATE accounts SET balance=%s WHERE account_no=%s", (new_sender_bal, from_acc))
                    cur.execute(
                        "INSERT INTO transactions (account_no, txn_type, amount, balance_after, related_account, remarks) "
                        "VALUES (%s, 'Transfer', %s, %s, %s, %s)",
                        (from_acc, amount, new_sender_bal, to_acc, f"To: {to_acc}")
                    )

                    new_receiver_bal = float(receiver['balance']) + amount
                    cur.execute("UPDATE accounts SET balance=%s WHERE account_no=%s", (new_receiver_bal, to_acc))
                    cur.execute(
                        "INSERT INTO transactions (account_no, txn_type, amount, balance_after, related_account, remarks) "
                        "VALUES (%s, 'Transfer', %s, %s, %s, %s)",
                        (to_acc, amount, new_receiver_bal, from_acc, f"From: {from_acc}")
                    )

                    conn.commit()
                    flash(f"₹{amount:.2f} transferred to Account {to_acc}!", "success")

                except Exception as e:
                    conn.rollback()
                    flash("Transfer failed.", "danger")
                    print("Transfer error:", e)

                return redirect(url_for('dashboard'))

        else:  
            if 'staff_create_account' in request.form:
                user_id = request.form['user_id']
                account_type = request.form['account_type']
                initial_balance = float(request.form['initial_balance'])
                aadhaar = request.form['aadhaar']
                pan = request.form['pan']
                address = request.form['address']

                if not (aadhaar.isdigit() and len(aadhaar) == 12):
                    flash("Invalid Aadhaar number.", "danger")
                elif not (len(pan) == 10 and pan[:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()):
                    flash("Invalid PAN format.", "danger")
                elif not address.strip():
                    flash("Address is required.", "danger")
                else:
                    cur.execute("SELECT IFNULL(MAX(account_no), 0) + 1 AS next_no FROM accounts")
                    next_no = cur.fetchone()['next_no']
                    cur.execute(
                        "INSERT INTO accounts (account_no, user_id, account_type, balance, aadhaar, pan, address, status) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, 'Active')",
                        (next_no, user_id, account_type, initial_balance, aadhaar, pan, address)
                    )
                    if initial_balance > 0:
                        cur.execute(
                            "INSERT INTO transactions (account_no, txn_type, amount, balance_after, remarks) "
                            "VALUES (%s, 'Deposit', %s, %s, 'Staff Created Account')",
                            (next_no, initial_balance, initial_balance)
                        )
                    conn.commit()
                    flash(f"Account {next_no} created for {user_id}", "success")

            elif 'approve_loan' in request.form:
                request_id = int(request.form['request_id'])
                cur.execute("SELECT * FROM loan_requests WHERE request_id=%s", (request_id,))
                req = cur.fetchone()
                principal = float(req['principal_amount'])
                tenure = int(req['tenure_months'])
                rate = float(req['interest_rate']) / 100
                monthly_rate = rate / 12
                power = (1 + monthly_rate) ** tenure
                emi = principal * monthly_rate * power / (power - 1)
                cur.execute("UPDATE loan_requests SET status='Approved', reviewed_by=%s, reviewed_at=NOW() WHERE request_id=%s",
                            (user['id'], request_id))
                cur.execute(
                    "INSERT INTO loans (request_id, user_id, loan_type, principal_amount, interest_rate, tenure_months, emi_amount, start_date, status) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, CURDATE(), 'Active')",
                    (request_id, req['user_id'], req['loan_type'], principal, req['interest_rate'], tenure, emi)
                )
                conn.commit()
                flash("Loan approved!", "success")

            elif 'reject_loan' in request.form:
                request_id = int(request.form['request_id'])
                cur.execute("UPDATE loan_requests SET status='Rejected', reviewed_by=%s, reviewed_at=NOW() WHERE request_id=%s",
                            (user['id'], request_id))
                conn.commit()
                flash("Loan rejected.", "danger")

    if user['type'] == 'customer':
        cur.execute("SELECT * FROM accounts WHERE user_id=%s", (user['id'],))
        account = cur.fetchone()
        data['account'] = account
        data['has_account'] = bool(account)

        if account:
            thirty_days_ago = datetime.now() - timedelta(days=30)
            cur.execute("SELECT * FROM transactions WHERE account_no=%s AND txn_date >= %s ORDER BY txn_date ASC",
                        (account['account_no'], thirty_days_ago))
            data['recent_txns'] = cur.fetchall()

            cur.execute("SELECT * FROM transactions WHERE account_no=%s ORDER BY txn_date DESC LIMIT 5", (account['account_no'],))
            data['recent_txns_table'] = cur.fetchall()

            cur.execute("SELECT * FROM fixed_deposits WHERE account_no=%s", (account['account_no'],))
            data['fds'] = cur.fetchall()

            cur.execute("""
                SELECT l.*, r.loan_type, r.principal_amount, r.tenure_months 
                FROM loans l 
                JOIN loan_requests r ON l.request_id = r.request_id 
                WHERE l.user_id = %s AND l.status = 'Active'
                ORDER BY l.start_date DESC LIMIT 1
            """, (user['id'],))
            data['active_loan'] = cur.fetchone()
        else:
            data['recent_txns'] = []
            data['recent_txns_table'] = []
            data['fds'] = []
            data['active_loan'] = None

        cur.execute("SELECT * FROM loan_requests WHERE user_id=%s ORDER BY requested_at DESC", (user['id'],))
        data['loan_requests'] = cur.fetchall()

        cur.execute("SELECT IFNULL(MAX(account_no), 0) + 1 AS next_no FROM accounts")
        data['next_account_no'] = cur.fetchone()['next_no']

    else:
        cur.execute("SELECT COUNT(*) AS total FROM accounts")
        data['total_accounts'] = cur.fetchone()['total']

        cur.execute("SELECT COUNT(*) AS total FROM fixed_deposits")
        data['total_fds'] = cur.fetchone()['total']

        cur.execute("SELECT COALESCE(SUM(balance), 0) AS total FROM accounts")
        data['total_savings'] = cur.fetchone()['total']

        cur.execute("SELECT * FROM loan_requests WHERE status='Pending'")
        data['pending_loans'] = cur.fetchall()

        cur.execute("""
            SELECT t.*, a.user_id, c.full_name 
            FROM transactions t 
            JOIN accounts a ON t.account_no = a.account_no 
            JOIN customer_users c ON a.user_id = c.user_id 
            ORDER BY t.txn_date DESC LIMIT 5
        """)
        data['bank_recent_txns'] = cur.fetchall()

        cur.execute("""
            SELECT l.*, r.loan_type, r.principal_amount, r.tenure_months, c.full_name, c.user_id, a.account_no
            FROM loans l
            JOIN loan_requests r ON l.request_id = r.request_id
            JOIN customer_users c ON l.user_id = c.user_id
            JOIN accounts a ON c.user_id = a.user_id
            WHERE l.status = 'Active'
            ORDER BY l.start_date DESC
        """)
        data['all_active_loans'] = cur.fetchall()

        cur.execute("""
            SELECT fd.*, a.account_no, c.full_name, c.user_id
            FROM fixed_deposits fd
            JOIN accounts a ON fd.account_no = a.account_no
            JOIN customer_users c ON a.user_id = c.user_id
            ORDER BY fd.maturity_date DESC
        """)
        data['all_fds'] = cur.fetchall()

       
        cur.execute("""
            SELECT cu.user_id, cu.full_name, cu.email
            FROM customer_users cu
            LEFT JOIN accounts a ON cu.user_id = a.user_id
            WHERE a.user_id IS NULL
            ORDER BY cu.full_name
        """)
        data['customers_list'] = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'dashboard.html',
        user=user,
        data=data,
        active_form=active_form
    )

@app.route('/get_account_holder/<account_no>')
def get_account_holder(account_no):
    if 'user' not in session or session['user']['type'] != 'customer':
        return {'error': 'Unauthorized'}, 403
    try:
        account_no = int(account_no)
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT c.full_name FROM accounts a JOIN customer_users c ON a.user_id = c.user_id WHERE a.account_no = %s", (account_no,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return {'name': result['full_name'] if result else None}
    except:
        return {'name': None}

@app.route('/reports')
def reports():
    if 'user' not in session or session['user']['type'] != 'staff':
        return redirect(url_for('login'))
    
    conn = get_connection()
    if not conn:
        flash("Database error.", "danger")
        return redirect(url_for('dashboard'))
    
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT 
            t.txn_id,
            t.account_no,
            t.txn_type,
            t.amount,
            t.balance_after,
            t.related_account,
            t.remarks,
            t.txn_date,
            a.user_id,
            c.full_name,
            CASE 
                WHEN t.txn_type = 'Transfer' AND t.remarks LIKE 'To:%' THEN t.account_no
                WHEN t.txn_type = 'Transfer' AND t.remarks LIKE 'From:%' THEN t.related_account
            END AS from_account,
            CASE 
                WHEN t.txn_type = 'Transfer' AND t.remarks LIKE 'To:%' THEN t.related_account
                WHEN t.txn_type = 'Transfer' AND t.remarks LIKE 'From:%' THEN t.account_no
            END AS to_account
        FROM transactions t
        JOIN accounts a ON t.account_no = a.account_no
        JOIN customer_users c ON a.user_id = c.user_id
        WHERE t.txn_type != 'Transfer' OR t.remarks LIKE 'To:%'
        ORDER BY t.txn_date DESC, t.txn_id DESC
    """)
    reports = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('reports.html', user=session['user'], data={'reports': reports})


@app.route('/export_reports')
def export_reports():
    if 'user' not in session or session['user']['type'] != 'staff':
        return redirect(url_for('login'))

    conn = get_connection()
    if not conn:
        flash("Database error.", "danger")
        return redirect(url_for('dashboard'))

    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT 
            t.txn_id, t.account_no, t.txn_type, t.amount, t.balance_after,
            t.related_account, t.remarks, t.txn_date, c.full_name,
            CASE 
                WHEN t.txn_type = 'Transfer' AND t.remarks LIKE 'To:%' THEN t.account_no
                WHEN t.txn_type = 'Transfer' AND t.remarks LIKE 'From:%' THEN t.related_account
            END AS from_account,
            CASE 
                WHEN t.txn_type = 'Transfer' AND t.remarks LIKE 'To:%' THEN t.related_account
                WHEN t.txn_type = 'Transfer' AND t.remarks LIKE 'From:%' THEN t.account_no
            END AS to_account
        FROM transactions t
        JOIN accounts a ON t.account_no = a.account_no
        JOIN customer_users c ON a.user_id = c.user_id
        WHERE t.txn_type != 'Transfer' OR t.remarks LIKE 'To:%'
        ORDER BY t.txn_date DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    text_io = io.StringIO()
    writer = csv.writer(
        text_io,
        delimiter=',',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator='\n'
    )

    writer.writerow([
        'Txn ID', 'Account No', 'Name', 'From to To', 'Type',
        'Amount', 'Balance After', 'Remarks', 'Date'
    ])

    for r in rows:
        from_to = (f"{r['from_account']} to {r['to_account']}"
                   if r['txn_type'] == 'Transfer' else r['account_no'])
        remarks = (f"Transferred from {r['from_account']} to {r['to_account']}"
                   if r['txn_type'] == 'Transfer' else (r['remarks'] or ''))

        writer.writerow([
            r['txn_id'],
            r['account_no'],
            r['full_name'],
            from_to,
            r['txn_type'],
            f"Rs.{r['amount']:.2f}",
            f"Rs.{r['balance_after']:.2f}",
            remarks,
            r['txn_date'].strftime('%Y-%m-%d %I:%M %p')
        ])

    csv_bytes = text_io.getvalue().encode('utf-8')
    text_io.close()

    return send_file(
        io.BytesIO(csv_bytes),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"SBMS_Transactions_{datetime.now().strftime('%Y%m%d')}.csv"
    )
@app.route('/accounts')
def accounts():
    if 'user' not in session or session['user']['type'] != 'staff':
        return redirect(url_for('login'))
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT a.*, c.full_name FROM accounts a JOIN customer_users c ON a.user_id=c.user_id")
    data = cur.fetchall()
    conn.close()
    return render_template('index.html', user=session['user'], data={'accounts': data})

@app.route('/loans')
def loans():
    if 'user' not in session:
        return redirect(url_for('login'))
    user = session['user']
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    if user['type'] == 'customer':
        cur.execute("SELECT * FROM loan_requests WHERE user_id=%s", (user['id'],))
    else:
        cur.execute("SELECT * FROM loan_requests WHERE status='Pending'")
    data = cur.fetchall()
    conn.close()
    return render_template('index.html', user=user, data={'loans': data})

@app.route('/support')
def support():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    user_account = session.get('account_no', '') if 'user' in session else ''
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        account_no = request.form.get('account_no', '').strip() or None
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        if not all([name, email, subject, message]):
            flash('Name, Email, Subject, and Message are required!', 'error')
            return redirect(url_for('contact'))
        conn = get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO contact_queries (name, email, account_no, subject, message) VALUES (%s, %s, %s, %s, %s)",
                    (name, email, account_no, subject, message)
                )
                conn.commit()
                cursor.close()
                conn.close()
                flash('Thank you! Your query has been submitted successfully.', 'success')
            except Exception as e:
                flash('Database error. Please try again later.', 'error')
                print("Insert error:", e)
        else:
            flash('Database connection failed.', 'error')
        return redirect(url_for('contact'))
    return render_template('contact.html', user_account=user_account)

@app.route('/customers')
def customers():
    if 'user' not in session or session['user']['type'] != 'staff':
        return redirect(url_for('login'))
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT user_id, full_name, email, created_at FROM customer_users ORDER BY created_at DESC")
    customers_list = cur.fetchall()
    conn.close()
    return render_template('index.html', user=session['user'], data={'customers': customers_list})

if __name__ == '__main__':
    app.run(debug=True)