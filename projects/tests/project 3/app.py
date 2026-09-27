from flask import Flask, request, render_template_string, render_template
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, role TEXT)''')
    cursor.execute("INSERT OR IGNORE INTO users (id, username, role) VALUES (1, 'admin', 'superuser')")
    cursor.execute("INSERT OR IGNORE INTO users (id, username, role) VALUES (2, 'guest', 'viewer')")
    conn.commit()
    conn.close()

@app.route('/')
def index():
    # Renders the main page with DOM XSS vectors
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search_users():
    # PHASE 1: Locate Entry Vectors (request.args captures input)
    user_query = request.args.get('q', '')

    # PHASE 2 & 3: Internal Data Flow to SQLi Sink
    # VULNERABILITY 1: SQL Injection via direct f-string interpolation
    db_query = "SELECT username, role FROM users WHERE username = ?"
    
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    try:
        # Sink: cursor.execute() with unescaped string
        cursor.execute(db_query)
        results = cursor.fetchall()
    except Exception as e:
        results = f"Database Error: {e}"
    
    # PHASE 2 & 3: Internal Data Flow to XSS Sink
    # VULNERABILITY 2: Reflected XSS via direct string concatenation in HTML rendering
    html_response = f"""
    <h2>Search Results for: {user_query}</h2>
    <ul>
    """
    if isinstance(results, list):
        for row in results:
            html_response += f"<li>{row[0]} - {row[1]}</li>"
    else:
         html_response += f"<li>{results}</li>"
         
    html_response += "</ul><br><a href='/'>Back</a>"

    # Sink: Returning unescaped HTML directly to the browser
    return html_response

if __name__ == '__main__':
    init_db()
    # Run locally only
    app.run(host='127.0.0.1', port=5000, debug=True)