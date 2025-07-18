import os
import json
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from functools import wraps

# ---- CONFIGURATION ----
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "cac"      # Change-moi en prod !
SECRET_KEY = "13457689"     # Change-moi en prod !
JSON_PATH = "json/competitions_full_2025.json"

app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app, supports_credentials=True, origins=["https://thegreenpadel.fr"])

# ---- UTILITAIRES ----
def load_comps():
    if not os.path.exists(JSON_PATH):
        return []
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_comps(comps):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(comps, f, ensure_ascii=False, indent=2)

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged"):
            return jsonify({"success": False, "error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    return wrapper

# ---- ROUTES PUBLIQUES ----
@app.route("/api/competitions", methods=["GET"])
def get_competitions():
    # Seules les compétitions validées (validated==1)
    comps = [c for c in load_comps() if c.get("validated", 0) == 1]
    return jsonify(comps)

@app.route("/api/competitions", methods=["POST"])
def add_competition():
    data = request.json
    required = ["nom", "famille", "date", "lieu", "lat", "lon"]
    if not data or not all(field in data for field in required):
        return jsonify({"success": False, "error": "Champs manquants"}), 400

    comps = load_comps()
    new_id = str(max([int(c["id"]) for c in comps] + [0]) + 1)
    comp = {
        "id": new_id,
        "famille": data["famille"],
        "date": data["date"],
        "nom": data["nom"],
        "lieu": data["lieu"],
        "lat": data["lat"],
        "lon": data["lon"],
        "vent_deg": data.get("vent_deg"),
        "validated": 0
    }
    comps.append(comp)
    save_comps(comps)
    return jsonify({"success": True, "id": new_id}), 201

# ---- ADMIN AUTH ----
@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.json
    if data and data.get("username") == ADMIN_USERNAME and data.get("password") == ADMIN_PASSWORD:
        session["admin_logged"] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Identifiants invalides"}), 401

@app.route("/api/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    session.pop("admin_logged", None)
    return jsonify({"success": True})

# ---- ROUTES ADMIN : voir, valider, supprimer ----
@app.route("/api/admin/competitions", methods=["GET"])
@admin_required
def admin_get_all():
    comps = load_comps()
    return jsonify(comps)

@app.route("/api/admin/validate/<comp_id>", methods=["POST"])
@admin_required
def admin_validate(comp_id):
    comps = load_comps()
    found = False
    for c in comps:
        if str(c["id"]) == str(comp_id):
            c["validated"] = 1
            found = True
            break
    if found:
        save_comps(comps)
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Compétition non trouvée"}), 404

@app.route("/api/admin/delete/<comp_id>", methods=["POST"])
@admin_required
def admin_delete(comp_id):
    comps = load_comps()
    new_comps = [c for c in comps if str(c["id"]) != str(comp_id)]
    if len(new_comps) == len(comps):
        return jsonify({"success": False, "error": "Compétition non trouvée"}), 404
    save_comps(new_comps)
    return jsonify({"success": True})

# ---- SERVER ----
if __name__ == "__main__":
    app.run(debug=True, port=5000)
