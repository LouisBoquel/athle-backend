import json
from flask import Flask, request, jsonify, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from flask_cors import CORS

ADMIN_USER = "admin"
ADMIN_PASSWORD = "ton_mot_de_passe_fort"
SECRET_KEY = "13457689"
JSON_PATH = "json/competitions_full_2025.json"

app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app, supports_credentials=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "admin_login"

# --- Chargement et sauvegarde JSON ---
def load_json():
    try:
        with open(JSON_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_json(data):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- SÉCURITÉ ADMIN ---
class AdminUser(UserMixin):
    id = 1
    username = ADMIN_USER

@login_manager.user_loader
def load_user(user_id):
    if str(user_id) == "1":
        return AdminUser()
    return None

# --- ROUTES PUBLIQUES ---
@app.route('/api/competitions', methods=['GET'])
def get_competitions():
    data = load_json()
    comps = [c for c in data if str(c.get("validated", 0)) == "1"]
    return jsonify(comps)

@app.route('/api/competitions', methods=['POST'])
def add_competition():
    data = request.json
    required_fields = ['nom', 'famille', 'date', 'lieu', 'lat', 'lon']
    if not all(f in data for f in required_fields):
        return jsonify({"error": "Champs manquants"}), 400
    comps = load_json()
    # id = max + 1 pour éviter doublon avec FFA (force int ou fallback 100000)
    try:
        last_id = max((int(str(c['id']).replace("user-", "")) for c in comps if str(c.get("id")).startswith("user-")), default=100000)
    except:
        last_id = 100000
    data['id'] = "user-" + str(last_id + 1)
    data['validated'] = 0
    comps.append(data)
    save_json(comps)
    return jsonify({"success": True, "id": data['id']}), 201

# --- AUTHENTIFICATION ADMIN ---
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    if not data or data.get('username') != ADMIN_USER or data.get('password') != ADMIN_PASSWORD:
        return jsonify({'success': False, 'error': 'Identifiants invalides'}), 401
    login_user(AdminUser())
    return jsonify({'success': True})

@app.route('/api/admin/logout', methods=['POST'])
@login_required
def admin_logout():
    logout_user()
    return jsonify({'success': True})

# --- ENDPOINTS ADMIN ---
@app.route('/api/admin/competitions', methods=['GET'])
@login_required
def admin_get_all():
    comps = load_json()
    return jsonify(comps)

@app.route('/api/admin/validate/<comp_id>', methods=['POST'])
@login_required
def admin_validate(comp_id):
    comps = load_json()
    modified = 0
    for c in comps:
        if str(c['id']) == str(comp_id):
            c['validated'] = 1
            modified += 1
    save_json(comps)
    return jsonify({"success": True, "validated": modified})

@app.route('/api/admin/delete/<comp_id>', methods=['POST'])
@login_required
def admin_delete(comp_id):
    comps = load_json()
    n_before = len(comps)
    comps = [c for c in comps if str(c['id']) != str(comp_id)]
    save_json(comps)
    return jsonify({"removed": n_before - len(comps), "success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
