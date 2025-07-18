import os
import json
from flask import Flask, request, jsonify, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS

# --- CONFIG ---
ADMIN_USER = "admin"
ADMIN_PASSWORD = "ton_mot_de_passe"   # Mets ton vrai mot de passe ici
SECRET_KEY = "une_cle_ultra_secrete"  # Mets une vraie clé

JSON_PATH = "json/competitions_full_2025.json"  # Chemin du fichier JSON

app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app, supports_credentials=True, origins=['https://thegreenpadel.fr'])

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "admin_login"

# --- CLASSE ADMIN ---
class AdminUser(UserMixin):
    id = 1
    username = ADMIN_USER

@login_manager.user_loader
def load_user(user_id):
    if str(user_id) == "1":
        return AdminUser()
    return None

# --- UTILS JSON ---
def load_compets():
    if not os.path.exists(JSON_PATH):
        return []
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_compets(data):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- PUBLIC : liste compétitions validées ---
@app.route('/api/competitions', methods=['GET'])
def get_competitions():
    comps = load_compets()
    comps_validated = [c for c in comps if c.get("validated", 1) == 1]
    return jsonify(comps_validated)

# --- PUBLIC : ajout compétition (toujours non validée) ---
@app.route('/api/competitions', methods=['POST'])
def add_competition():
    data = request.json
    required_fields = ['nom', 'famille', 'date', 'lieu', 'lat', 'lon']
    if not all(f in data for f in required_fields):
        return jsonify({"error": "Champs manquants"}), 400
    comps = load_compets()
    next_id = max([int(c["id"]) for c in comps] + [0]) + 1
    comp = {
        "id": str(next_id),
        "famille": data['famille'],
        "date": data['date'],
        "nom": data['nom'],
        "lieu": data['lieu'],
        "lat": data['lat'],
        "lon": data['lon'],
        "vent_deg": data.get('vent_deg'),
        "validated": 0
    }
    comps.append(comp)
    save_compets(comps)
    return jsonify({"success": True, "id": next_id}), 201

# --- ADMIN : login/logout ---
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

# --- ADMIN : liste toutes les compés (validées ou non) ---
@app.route('/api/admin/competitions', methods=['GET'])
@login_required
def admin_get_all():
    comps = load_compets()
    # Tri : non validées d'abord, puis par date
    comps = sorted(comps, key=lambda c: (c.get("validated", 1), c["date"]))
    return jsonify(comps)

# --- ADMIN : valider une compétition ---
@app.route('/api/admin/validate/<int:comp_id>', methods=['POST'])
@login_required
def admin_validate(comp_id):
    comps = load_compets()
    for c in comps:
        if int(c["id"]) == comp_id:
            c["validated"] = 1
    save_compets(comps)
    return jsonify({"success": True})

# --- ADMIN : supprimer une compétition ---
@app.route('/api/admin/delete/<int:comp_id>', methods=['POST'])
@login_required
def admin_delete(comp_id):
    comps = load_compets()
    comps = [c for c in comps if int(c["id"]) != comp_id]
    save_compets(comps)
    return jsonify({"success": True})

# --- OPTIONNEL : éditer une compétition (admin) ---
@app.route('/api/admin/edit/<int:comp_id>', methods=['POST'])
@login_required
def admin_edit(comp_id):
    data = request.json
    comps = load_compets()
    found = False
    for c in comps:
        if int(c["id"]) == comp_id:
            for k in ['famille', 'date', 'nom', 'lieu', 'lat', 'lon', 'vent_deg']:
                if k in data:
                    c[k] = data[k]
            found = True
    if found:
        save_compets(comps)
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
