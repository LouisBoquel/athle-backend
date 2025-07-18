#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scraper_full_year.py (FFA uniquement, toutes familles, robustifié pour MySQL + GitHub Actions)

Récupère toutes les compétitions FFA ("Stade", "Salle", "Cross", "Hors Stade", "Marche Route") à venir de 2025,
géocode les lieux via Nominatim (robuste aux erreurs),
récupère le sens du vent via OpenWeatherMap,
et écrit les compétitions dans la base MySQL ET dans competitions_full_2025.json.
"""

import requests
from bs4 import BeautifulSoup
import calendar
import json
import re
import time
import os
import mysql.connector
from datetime import date

BASE_URL = "https://bases.athle.fr/asp.net/accueil.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://bases.athle.fr/asp.net/accueil.aspx?frmbase=calendrier"
}
YEAR     = 2025
TODAY    = date.today()
FAMILLES = ["Stade", "Salle", "Cross", "Hors Stade", "Marche Route"]
GEO_CACHE = {}

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

# --- Récupère la config MySQL depuis l'environnement (voir GitHub Actions secrets) ---
MYSQL_CONFIG = {
    "host":     os.environ.get("MYSQL_HOST"),
    "user":     os.environ.get("MYSQL_USER"),
    "password": os.environ.get("MYSQL_PASSWORD"),
    "database": os.environ.get("MYSQL_DATABASE"),
    "port":     int(os.environ.get("MYSQL_PORT", "3306")),
}

def geocode(place):
    if place in GEO_CACHE:
        return GEO_CACHE[place]
    url = "https://nominatim.openstreetmap.org/search"
    params = {'q': f"{place}, France", 'format': 'json', 'limit': 1}
    try:
        response = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        data = response.json()
        if data:
            lat_lon = float(data[0]['lat']), float(data[0]['lon'])
            GEO_CACHE[place] = lat_lon
            time.sleep(1)
            return lat_lon
    except Exception as e:
        print(f"⚠️ Erreur géocodage '{place}': {e}")
    GEO_CACHE[place] = (None, None)
    return (None, None)

def get_wind_direction(lat, lon):
    if lat is None or lon is None:
        return None
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {'lat': lat, 'lon': lon, 'appid': OPENWEATHER_API_KEY, 'units': 'metric'}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('wind', {}).get('deg')
    except Exception as e:
        print(f"⚠️ Erreur récupération vent pour ({lat},{lon}): {e}")
        return None

def get_hidden_fields(session):
    r = session.get(
        BASE_URL,
        params={"frmbase": "calendrier", "frmmode": "1", "frmespace": "0"},
        headers=HEADERS,
        timeout=30
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form", id="bddForm1")
    if not form:
        raise RuntimeError("Formulaire introuvable")
    return {inp["name"]: inp.get("value", "") for inp in form.find_all("input", {"type": "hidden"})}

def scrape_month(session, hidden, year, month, famille):
    first_day = TODAY.day if (year == TODAY.year and month == TODAY.month) else 1
    last_day  = calendar.monthrange(year, month)[1]
    params = {**hidden}
    params.update({
        "frmbase": "calendrier",
        "frmmode": "1",
        "frmespace": "0",
        "frmsaisonffa": str(year),
        "frmtype1": famille,
        "frmdate_j1": str(first_day),
        "frmdate_m1": str(month),
        "frmdate_a1": str(year),
        "frmdate_j2": str(last_day),
        "frmdate_m2": str(month),
        "frmdate_a2": str(year),
    })

    r = session.get(BASE_URL, params=params, headers=HEADERS, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", id="ctnCalendrier")
    if not table:
        return []

    rows = table.find_all("tr")[2:]
    comps = []
    for tr in rows:
        a = tr.find("a", title=re.compile(r"Compétition numéro"))
        if not a: continue

        comp_id = re.search(r"(\d+)", a["title"]).group(1)
        tds = tr.find_all("td", class_=re.compile(r"datas\d"))
        if len(tds) < 4: continue

        date_txt, nom, lieu = (tds[0].text.strip(), tds[2].text.strip(), tds[3].text.strip())
        if re.search(r"\([A-Z]{2,3}\)$", lieu): continue

        lat, lon = geocode(lieu)
        wind_deg = None
        if lat and lon:
            wind_deg = get_wind_direction(lat, lon)

        comps.append({
            "id": comp_id, "famille": famille, "date": date_txt,
            "nom": nom, "lieu": lieu, "lat": lat, "lon": lon,
            "vent_deg": wind_deg
        })

    print(f"{famille} {month:02d}/{year} : {len(comps)} compétitions.")
    return comps

def insert_into_mysql(comps):
    """Insert/Update competitions into the MySQL database."""
    db = mysql.connector.connect(**MYSQL_CONFIG)
    cur = db.cursor()

    # Assure la colonne validated existe (si tu veux qu'elles arrivent en "validées" directement, mets validated=1)
    for c in comps:
        # On met à jour si déjà présent (id unique)
        cur.execute('''
            INSERT INTO competitions (id, famille, date, nom, lieu, lat, lon, vent_deg, validated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE
                famille=VALUES(famille), date=VALUES(date), nom=VALUES(nom), lieu=VALUES(lieu),
                lat=VALUES(lat), lon=VALUES(lon), vent_deg=VALUES(vent_deg)
        ''', (
            c['id'], c['famille'], c['date'], c['nom'], c['lieu'],
            c['lat'], c['lon'], c['vent_deg']
        ))
    db.commit()
    cur.close()
    db.close()
    print(f"💾 {len(comps)} compétitions insérées/MAJ en base MySQL.")

def scrape_full_year(year):
    session = requests.Session()
    hidden = get_hidden_fields(session)

    all_comps = {}
    for month in range(TODAY.month, 13):
        for famille in FAMILLES:
            for comp in scrape_month(session, hidden, year, month, famille):
                all_comps[comp["id"]] = comp

    out = list(all_comps.values())

    # 1. Ecrit le JSON pour debug/local
    fname = f"json/competitions_full_{year}.json"
    os.makedirs("json", exist_ok=True)
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nTerminé : {len(out)} compétitions sauvegardées dans {fname}.")

    # 2. Insert en base MySQL
    insert_into_mysql(out)
    return out

if __name__ == "__main__":
    scrape_full_year(YEAR)

