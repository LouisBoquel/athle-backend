import os
import json
from flask import Flask, request, jsonify, session
from flask_cors import CORS

# --- CONFIG ---
JSON_PATH = "json/competitions_full_2025.json"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "ton_mot_de_passe_fort"  # CHANGE MOI
SECRET_KEY = "ta_secret_key_admin"        # CHANGE MOI AUSSI

app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app, supports_credentials=True, origins=['https://thegreenpadel.fr'])

# --- UTILS JSON ---
def load_competitions():
    if not os.path.exists(JSON_PATH):
        return []
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_competitions(comps):
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(comps, f, ensure_ascii=False, indent=2)

# --- AUTH (simple session cookie) ---
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    if not data or data.get('username') != ADMIN_USER or data.get('password') != ADMIN_PASSWORD:
        return jsonify({'success': False, 'error': 'Identifiants invalides'}), 401
    session['admin'] = True
    return jsonify({'success': True})

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin', None)
    return jsonify({'success': True})

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get('admin'):
            return jsonify({'success': False, 'error': 'Non autorisé'}), 403
        return f(*args, **kwargs)
    return wrap

# --- ROUTES PUBLIQUES (compétitions validées) ---
@app.route('/api/competitions', methods=['GET'])
def get_competitions():
    comps = load_competitions()
    return jsonify([c for c in comps if c.get("validated", 0)])

@app.route('/api/competitions', methods=['POST'])
def add_competition():
    data = request.json
    required = ['nom', 'famille', 'date', 'lieu', 'lat', 'lon']
    if not all(k in data for k in required):
        return jsonify({"error": "Champs manquants"}), 400
    comps = load_competitions()
    # Attribue un nouvel ID unique (max + 1)
    existing_ids = [int(c['id']) for c in comps if str(c.get('id')).isdigit()]
    new_id = str(max(existing_ids) + 1 if existing_ids else 1)
    comp = {
        "id": new_id,
        "famille": data['famille'],
        "date": data['date'],
        "nom": data['nom'],
        "lieu": data['lieu'],
        "lat": data['lat'],
        "lon": data['lon'],
        "validated": 0
    }
    comps.append(comp)
    save_competitions(comps)
    return jsonify({"success": True, "id": new_id}), 201

# --- ROUTES ADMIN (modération) ---
@app.route('/api/admin/competitions', methods=['GET'])
@admin_required
def admin_list():
    return jsonify(load_competitions())

@app.route('/api/admin/validate/<comp_id>', methods=['POST'])
@admin_required
def admin_validate(comp_id):
    comps = load_competitions()
    count = 0
    for c in comps:
        if str(c['id']) == str(comp_id):
            c['validated'] = 1
            count += 1
    save_competitions(comps)
    return jsonify({"success": True, "validated": count})

@app.route('/api/admin/delete/<comp_id>', methods=['POST'])
@admin_required
def admin_delete(comp_id):
    comps = load_competitions()
    before = len(comps)
    comps = [c for c in comps if str(c['id']) != str(comp_id)]
    save_competitions(comps)
    return jsonify({"success": True, "removed": before - len(comps)})

# --- RUN ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)
