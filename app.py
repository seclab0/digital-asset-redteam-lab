import json
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for

DB_PATH = "database.db"

app = Flask(__name__)
app.secret_key = "dev-only-insecure-secret-key"
app.config.update(SESSION_COOKIE_HTTPONLY=True)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            krw_balance INTEGER NOT NULL,
            btc_balance REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            revoked INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS lab_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            detail TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    row = db.execute("SELECT id FROM users WHERE username='user'").fetchone()
    if not row:
        db.execute(
            "INSERT INTO users(id, username, password, krw_balance, btc_balance) VALUES (1, 'user', 'pass', 10000000, 1.2345)"
        )
    db.commit()


def login_required(page=False):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                if page:
                    return redirect(url_for("login_get"))
                return jsonify({"status": "error", "message": "Authentication required"}), 401
            return fn(*args, **kwargs)
        return wrapper
    return deco


def process_withdraw(user_id, amount, auth_method):
    try:
        amt = int(amount)
    except (TypeError, ValueError):
        return {"status": "error", "message": "amount must be numeric", "auth_method": auth_method}, 400
    if amt <= 0:
        return {"status": "error", "message": "amount must be greater than 0", "auth_method": auth_method}, 400
    db = get_db()
    user = db.execute("SELECT krw_balance FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        return {"status": "error", "message": "user not found", "auth_method": auth_method}, 404
    if amt > user["krw_balance"]:
        return {"status": "error", "message": "insufficient KRW balance", "auth_method": auth_method}, 400
    new_balance = user["krw_balance"] - amt
    db.execute("UPDATE users SET krw_balance=? WHERE id=?", (new_balance, user_id))
    db.commit()
    return {
        "status": "success",
        "message": "API withdrawal requested" if auth_method == "api_key_only" else "Withdrawal requested",
        "amount": amt,
        "auth_method": auth_method,
        "remaining_krw_balance": new_balance,
    }, 200


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET"])
def login_get():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_post():
    if request.form.get("username") == "user" and request.form.get("password") == "pass":
        session["user_id"] = 1
        return redirect(url_for("dashboard"))
    return jsonify({"status": "error", "message": "invalid credentials"}), 401


@app.route("/dashboard")
@login_required(page=True)
def dashboard():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    key = db.execute("SELECT api_key FROM api_keys WHERE user_id=? AND revoked=0", (session["user_id"],)).fetchone()
    return render_template("dashboard.html", user=user, api_key=(key["api_key"] if key else "Not issued"))


@app.route("/withdraw", methods=["POST"])
@login_required()
def withdraw():
    payload, code = process_withdraw(session["user_id"], request.form.get("amount"), "session")
    return jsonify(payload), code


@app.route("/api/key", methods=["POST"])
@login_required()
def api_key():
    db = get_db()
    user_id = session["user_id"]
    row = db.execute("SELECT api_key FROM api_keys WHERE user_id=? AND revoked=0", (user_id,)).fetchone()
    if row:
        key = row["api_key"]
    else:
        key = "API-user-1234"
        db.execute("INSERT INTO api_keys(user_id, api_key, created_at, revoked) VALUES (?, ?, ?, 0)", (user_id, key, datetime.utcnow().isoformat()))
        db.commit()
    return jsonify({"status": "success", "api_key": key, "warning": "This is an intentionally vulnerable lab key with no expiry, no scope, and no IP restriction."})


@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    key = request.headers.get("X-API-KEY")
    if not key:
        return jsonify({"status": "error", "message": "missing X-API-KEY"}), 401
    db = get_db()
    row = db.execute("SELECT user_id FROM api_keys WHERE api_key=? AND revoked=0", (key,)).fetchone()
    if not row:
        return jsonify({"status": "error", "message": "invalid api key"}), 401
    amount = request.form.get("amount")
    if amount is None and request.is_json:
        body = request.get_json(silent=True) or {}
        amount = body.get("amount")
    payload, code = process_withdraw(row["user_id"], amount, "api_key_only")
    return jsonify(payload), code


@app.route('/openapi.json')
def openapi():
    return jsonify({"openapi": "3.0.0", "paths": {"/login": {}, "/withdraw": {}, "/api/key": {}, "/api/withdraw": {}, "/support": {}, "/lab/events": {}}})


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/support', methods=['GET'])
@login_required(page=True)
def support_get():
    tickets = get_db().execute("SELECT * FROM support_tickets ORDER BY id DESC").fetchall()
    return render_template('support.html', tickets=tickets)


@app.route('/support', methods=['POST'])
@login_required(page=True)
def support_post():
    db = get_db()
    db.execute("INSERT INTO support_tickets(user_id,title,message,created_at) VALUES (?,?,?,?)", (session['user_id'], request.form.get('title',''), request.form.get('message',''), datetime.utcnow().isoformat()))
    db.commit()
    return redirect(url_for('support_get'))


@app.route('/support/view/<int:ticket_id>')
@login_required(page=True)
def support_view(ticket_id):
    ticket = get_db().execute("SELECT * FROM support_tickets WHERE id=?", (ticket_id,)).fetchone()
    return render_template('support_view.html', ticket=ticket)


@app.route('/lab/events', methods=['POST'])
def lab_events_post():
    data = request.get_json(silent=True) or {}
    event_type = data.get('event_type', 'unknown')
    detail = data.get('detail', '')
    db = get_db()
    db.execute("INSERT INTO lab_events(event_type,detail,created_at) VALUES (?,?,?)", (event_type, str(detail), datetime.utcnow().isoformat()))
    db.commit()
    return jsonify({"status": "success"})


@app.route('/lab/events', methods=['GET'])
@login_required(page=True)
def lab_events_get():
    events = get_db().execute("SELECT * FROM lab_events ORDER BY id DESC").fetchall()
    return render_template('lab_events.html', events=events)


@app.route('/lab/reset', methods=['POST'])
@login_required()
def lab_reset():
    db = get_db()
    db.execute("UPDATE users SET krw_balance=10000000, btc_balance=1.2345 WHERE id=1")
    db.execute("DELETE FROM api_keys")
    db.execute("DELETE FROM support_tickets")
    db.execute("DELETE FROM lab_events")
    db.commit()
    return jsonify({"status": "success", "message": "lab reset completed"})


if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='127.0.0.1', port=5000, debug=True)
