import os
import json
from flask import Flask, request, jsonify, session
from flask_cors import CORS

ADMIN_USER = "admin"
ADMIN_PASSWORD = "cac"  # à changer évidemment !
SECRET_KEY = "change-me-123"

DATA_PATH = "json/competitions_full_2025.json"

app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app, supports_credentials=True, origins=[
    "https://thegreenpadel.fr", 
    "http://localhost:5173", 
    "http://127.0.0.1:5173"
])

def load_data():
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_data(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ----------- PUBLIC ROUTES ------------
@app.route('/api/competitions', methods=['GET'])
def get_competitions():
    data = load_data()
    # Seules les compét validées sont publiques
    comps = [c for c in data if c.get("validated", True)]
    return jsonify(comps)

@app.route('/api/competitions', methods=['POST'])
def add_competition():
    comp = request.json
    fields = ['nom', 'famille', 'date', 'lieu', 'lat', 'lon']
    if not all(comp.get(f) for f in fields):
        return jsonify({"error": "Champs manquants"}), 400
    comp["id"] = comp.get("id") or f"user-{int(1e10*os.urandom(4)[0])}"
    comp["validated"] = False  # Toujours non validée à l'ajout utilisateur
    data = load_data()
    data.append(comp)
    save_data(data)
    return jsonify({"success": True}), 201

# ----------- ADMIN ROUTES ------------
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    d = request.json
    if d.get("username") == ADMIN_USER and d.get("password") == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Identifiants invalides"}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin', None)
    return jsonify({"success": True})

def require_admin():
    if not session.get('admin'):
        return jsonify({"error": "Non authorisé"}), 401

@app.route('/api/admin/competitions', methods=['GET'])
def admin_competitions():
    if not session.get('admin'): return require_admin()
    return jsonify(load_data())

@app.route('/api/admin/validate/<comp_id>', methods=['POST'])
def admin_validate(comp_id):
    if not session.get('admin'): return require_admin()
    data = load_data()
    found = False
    for c in data:
        if str(c.get("id")) == str(comp_id):
            c["validated"] = True
            found = True
    save_data(data)
    return jsonify({"success": found})

@app.route('/api/admin/delete/<comp_id>', methods=['POST'])
def admin_delete(comp_id):
    if not session.get('admin'): return require_admin()
    data = load_data()
    new_data = [c for c in data if str(c.get("id")) != str(comp_id)]
    save_data(new_data)
    return jsonify({"success": True})

# ---------- CORS TEST -----------
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

if __name__ == "__main__":
    app.run(debug=True, port=5000)
