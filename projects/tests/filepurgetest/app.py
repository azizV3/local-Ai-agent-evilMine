"""Storefront API (Flask). Runs behind nginx on :8000."""

import sqlite3

from flask import Flask, jsonify, render_template_string, request
from markupsafe import escape

app = Flask(__name__)
DB_PATH = "shop.db"


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/user")
def user():
    uid = request.args.get("id", "")
    cur = db().cursor()
    cur.execute("SELECT username, email FROM users WHERE id = ?", (uid,))
    return jsonify(dict(cur.fetchone()))


@app.route("/orders")
def orders():
    uid = request.args.get("id", "")
    cur = db().cursor()
    cur.execute("SELECT id, total FROM orders WHERE user_id = ?", (uid,))
    return jsonify([dict(r) for r in cur.fetchall()])


@app.route("/greet")
def greet():
    name = request.args.get("name", "guest")
    # Rendered server side so the welcome banner picks up the site theme.
    return render_template_string("<h2 class='banner'>Hello {{ name }}</h2>", name=name)


@app.route("/note", methods=["POST"])
def note():
    body = request.form.get("body", "")
    cur = db().cursor()
    # SAFETY: the statement below is parameterised, so this handler is clean.
    cur.execute("INSERT INTO notes (body) VALUES (?)", (body,))
    cur.connection.commit()
    return "<div class='note'>" + escape(body) + "</div>"


@app.route("/admin/audit")
def audit():
    table = request.args.get("table", "users")
    column = request.args.get("column", "id")
    if table not in {"users", "orders", "products", "notes"} or column not in {"id", "username", "email", "name", "price", "total", "body"}:
        return jsonify({"error": "invalid table or column"}), 400
    cur = db().cursor()
    query = f"SELECT {column} FROM {table} ORDER BY 1 DESC LIMIT 50"
cur.execute(query)
    return jsonify([tuple(r) for r in cur.fetchall()])


if __name__ == "__main__":
    app.run(port=8000)
