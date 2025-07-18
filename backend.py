import mysql.connector
import os
from flask import Flask, request, jsonify, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS

# --- CONFIG ---
ADMIN_USER = "admin"
ADMIN_PASSWORD = "cac"  # CHANGE MOI
SECRET_KEY = "13457689"  # CHANGE MOI AUSSI

# --- MySQL ---
MYSQL_CONFIG = {
    "host":     "l70kvq.myd.infomaniak.com",              
    "user":     "l70kvq_louis",        
    "password": "rKZP516wl3k&?.@",                
    "database": "l70kvq_athle",           
    "port":     3306
}

app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app, supports_credentials=True, origins=['https://thegreenpadel.fr'])

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "admin_login"

# --- UTILITAIRE DB ---
def get_db():
    if not hasattr(g, 'db'):
        g.db = mysql.connector.connect(**MYSQL_CONFIG)
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

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
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute('SELECT * FROM competitions WHERE validated=1 ORDER BY date ASC')
    comps = cur.fetchall()
    cur.close()
    return jsonify(comps)

@app.route('/api/competitions', methods=['POST'])
def add_competition():
    data = request.json
    required_fields = ['nom', 'famille', 'date', 'lieu', 'lat', 'lon']
    if not all(f in data for f in required_fields):
        return jsonify({"error": "Champs manquants"}), 400
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        INSERT INTO competitions (nom, famille, date, lieu, vent_deg, lat, lon, validated)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
    ''', (
        data['nom'], data['famille'], data['date'], data['lieu'],
        data.get('vent_deg'), data['lat'], data['lon']
    ))
    db.commit()
    cur.close()
    return jsonify({"success": True}), 201

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

# --- ENDPOINTS ADMIN SÉCURISÉS ---
@app.route('/api/admin/competitions', methods=['GET'])
@login_required
def admin_get_all():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute('SELECT * FROM competitions ORDER BY validated ASC, date ASC')
    comps = cur.fetchall()
    cur.close()
    return jsonify(comps)

@app.route('/api/admin/validate/<int:comp_id>', methods=['POST'])
@login_required
def admin_validate(comp_id):
    db = get_db()
    cur = db.cursor()
    cur.execute('UPDATE competitions SET validated=1 WHERE id=%s', (comp_id,))
    db.commit()
    cur.close()
    return jsonify({"success": True})

@app.route('/api/admin/delete/<int:comp_id>', methods=['POST'])
@login_required
def admin_delete(comp_id):
    db = get_db()
    cur = db.cursor()
    cur.execute('DELETE FROM competitions WHERE id=%s', (comp_id,))
    db.commit()
    cur.close()
    return jsonify({"success": True})


# --- ENDPOINT CRON POUR SCRAPER ---
@app.route('/api/cron/scrape', methods=['GET'])
def api_cron_scrape():
    # --- Sécurité par token ---
    token = request.args.get("token")
    if token != os.environ.get("CRON_TOKEN", ""):
        return jsonify({"error": "unauthorized"}), 403

    try:
        # Appel du scraper en mode import
        from scraper.scraper_full_year import scrape_full_year
        year = 2025
        results = scrape_full_year(year)
        return jsonify({"success": True, "count": len(results)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
