"""
Cabinet Médical — Serveur API SQLite
ADLSoft v2.1 — Remplace api.php + MariaDB
Base de données : cabinet.db (dans le même dossier que l'exe)
"""

import sqlite3
import json
import os
import sys
import hashlib
import threading
import webbrowser
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ── Chemin de la base de données ───────────────────────────────
if getattr(sys, 'frozen', False):
    # Mode .exe (PyInstaller)
    BASE_DIR = os.path.dirname(sys.executable)
    SRC_DIR  = os.path.join(sys._MEIPASS, 'src')
else:
    # Mode développement
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SRC_DIR  = os.path.join(BASE_DIR, 'src')

DB_PATH = os.path.join(BASE_DIR, 'cabinet.db')

# ── Tables autorisées (sécurité) ───────────────────────────────
TABLES_ALLOWED = [
    'patients', 'consultations', 'ordonnances',
    'salle_attente', 'rendez_vous', 'certificats',
    'paiements_accueil', 'factures', 'utilisateurs', 'audit_logs'
]

ORDER_MAP = {
    'patients':          'nom, prenom',
    'consultations':     'date_consultation DESC',
    'ordonnances':       'date_ordonnance DESC',
    'salle_attente':     'heure_arrivee ASC',
    'rendez_vous':       'date_rdv ASC, heure_rdv ASC',
    'certificats':       'date_certificat DESC',
    'paiements_accueil': 'date_paiement DESC',
    'factures':          'date_facture DESC',
    'utilisateurs':      'nom',
    'audit_logs':        'date_action DESC',
}

# ── Flask app ──────────────────────────────────────────────────
app = Flask(__name__, static_folder=SRC_DIR)
CORS(app)

# ── Connexion SQLite ───────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

# ── Créer les tables SQLite ────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    ddn TEXT NOT NULL,
    sexe TEXT NOT NULL,
    telephone TEXT,
    email TEXT,
    adresse TEXT,
    ville TEXT,
    codepostal TEXT,
    nss TEXT UNIQUE,
    groupe_sanguin TEXT,
    profession TEXT,
    mutuelle TEXT,
    medecin_traitant TEXT,
    observations TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS consultations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    date_consultation TEXT NOT NULL,
    heure_consultation TEXT,
    motif TEXT,
    diagnostic TEXT,
    traitement TEXT,
    montant REAL DEFAULT 0,
    mode_paiement TEXT DEFAULT 'Espèces',
    docteur TEXT,
    statut TEXT DEFAULT 'Terminée',
    observations TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ordonnances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    consultation_id INTEGER,
    date_ordonnance TEXT NOT NULL,
    medecin TEXT,
    medicaments TEXT,
    duree_traitement TEXT,
    observations TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (consultation_id) REFERENCES consultations(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS salle_attente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    heure_arrivee TEXT NOT NULL,
    statut TEXT DEFAULT 'En attente',
    raison TEXT,
    date_visite TEXT NOT NULL,
    observations TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rendez_vous (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    date_rdv TEXT NOT NULL,
    heure_rdv TEXT NOT NULL,
    type_rdv TEXT,
    docteur TEXT,
    statut TEXT DEFAULT 'Confirmé',
    observations TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS certificats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    type_certificat TEXT,
    date_certificat TEXT NOT NULL,
    validite_debut TEXT,
    validite_fin TEXT,
    remarques TEXT,
    contenu TEXT,
    medecin TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS paiements_accueil (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    date_paiement TEXT NOT NULL,
    montant REAL NOT NULL DEFAULT 0,
    mode_paiement TEXT DEFAULT 'Espèces',
    reference_transaction TEXT,
    observations TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS factures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    date_facture TEXT NOT NULL,
    montant_total REAL NOT NULL DEFAULT 0,
    montant_paye REAL DEFAULT 0,
    statut TEXT DEFAULT 'Brouillon',
    type_facture TEXT,
    description TEXT,
    reference TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS utilisateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    role TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    mot_de_passe TEXT NOT NULL,
    telephone TEXT,
    actif INTEGER DEFAULT 1,
    date_creation TEXT DEFAULT (datetime('now')),
    last_login TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    utilisateur_id INTEGER,
    action TEXT NOT NULL,
    table_modifiee TEXT,
    enregistrement_id INTEGER,
    ancienne_valeur TEXT,
    nouvelle_valeur TEXT,
    date_action TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id) ON DELETE SET NULL
);
"""

DEMO_DATA_SQL = """
INSERT OR IGNORE INTO utilisateurs (nom, prenom, role, email, mot_de_passe, telephone, actif) VALUES
('Admin', 'Système', 'Admin', 'admin@cabinet.local', '{sha_admin}', '0123456789', 1),
('Dupont', 'Dr Jean', 'Docteur', 'dr.dupont@cabinet.local', '{sha_doc}', '0612345678', 1),
('Martin', 'Secrétaire', 'Secrétaire', 'martin@cabinet.local', '{sha_sec}', '0712345678', 1);

INSERT OR IGNORE INTO patients (nom, prenom, ddn, sexe, telephone, email, ville, nss, groupe_sanguin, profession, mutuelle, observations) VALUES
('Dupuis', 'Marie', '1990-05-15', 'F', '0612345678', 'marie.dupuis@email.com', 'Tunis', '123456789012345', 'A+', 'Professeur', 'CNRPS', 'Consultation régulière'),
('Bernard', 'Pierre', '1985-03-22', 'M', '0723456789', 'pierre.bernard@email.com', 'Sousse', '123456789012346', 'B+', 'Ingénieur', 'CNSS', 'Patient diabétique'),
('Laurent', 'Sophie', '1995-11-08', 'F', '0634567890', 'sophie.laurent@email.com', 'Sfax', '123456789012347', 'O+', 'Comptable', 'CNRPS', ''),
('Moreau', 'Luc', '1978-07-30', 'M', '0745678901', 'luc.moreau@email.com', 'Bizerte', '123456789012348', 'AB-', 'Retraité', 'Privé', 'Suivi cardiaque');
"""

def init_db():
    """Crée les tables et insère les données de démo si c'est la 1ère fois."""
    conn = get_db()
    conn.executescript(SCHEMA_SQL)

    # Données de démo seulement si la table est vide
    cur = conn.execute("SELECT COUNT(*) FROM utilisateurs")
    if cur.fetchone()[0] == 0:
        sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
        sql = DEMO_DATA_SQL.format(
            sha_admin=sha('admin123'),
            sha_doc=sha('doc456'),
            sha_sec=sha('sec789')
        )
        conn.executescript(sql)

    conn.commit()
    conn.close()

# ── Helper: convertir Row en dict ──────────────────────────────
def row_to_dict(row):
    return dict(row) if row else {}

# ── Servir l'application HTML ──────────────────────────────────
@app.route('/')
def index():
    return send_from_directory(SRC_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(SRC_DIR, filename)

# ── API CRUD principale ────────────────────────────────────────
@app.route('/api', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def api():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    table = request.args.get('table', '')
    row_id = request.args.get('id', None)
    method = request.method

    # Validation table
    if table not in TABLES_ALLOWED:
        return jsonify({'success': False, 'error': f'Table non autorisée : {table}'}), 400

    try:
        conn = get_db()

        # ── GET ──────────────────────────────────────────────
        if method == 'GET':
            if row_id is not None:
                cur = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,))
                row = cur.fetchone()
                return jsonify({'success': True, 'data': row_to_dict(row)})
            else:
                order = ORDER_MAP.get(table, 'id DESC')
                cur = conn.execute(f"SELECT * FROM {table} ORDER BY {order}")
                rows = [row_to_dict(r) for r in cur.fetchall()]
                return jsonify({'success': True, 'data': rows})

        # ── POST ─────────────────────────────────────────────
        elif method == 'POST':
            body = request.get_json() or {}
            if not body:
                return jsonify({'success': False, 'error': 'Corps de requête vide'}), 400

            # Sérialiser les objets JSON en texte
            for k, v in body.items():
                if isinstance(v, (dict, list)):
                    body[k] = json.dumps(v, ensure_ascii=False)

            cols = list(body.keys())
            placeholders = ','.join(['?' for _ in cols])
            col_names = ','.join(cols)
            values = [body[c] for c in cols]

            cur = conn.execute(
                f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})",
                values
            )
            conn.commit()
            new_id = cur.lastrowid
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (new_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'data': row_to_dict(row)})

        # ── PUT ──────────────────────────────────────────────
        elif method == 'PUT':
            if not row_id:
                return jsonify({'success': False, 'error': 'id requis'}), 400
            body = request.get_json() or {}
            if not body:
                return jsonify({'success': False, 'error': 'Corps de requête vide'}), 400

            for k, v in body.items():
                if isinstance(v, (dict, list)):
                    body[k] = json.dumps(v, ensure_ascii=False)

            # Ajouter updated_at automatiquement
            body['updated_at'] = "datetime('now')"
            sets = ', '.join([
                f"{k} = datetime('now')" if v == "datetime('now')" else f"{k} = ?"
                for k, v in body.items()
            ])
            values = [v for v in body.values() if v != "datetime('now')"]
            values.append(row_id)

            conn.execute(f"UPDATE {table} SET {sets} WHERE id = ?", values)
            conn.commit()
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
            conn.close()
            return jsonify({'success': True, 'data': row_to_dict(row)})

        # ── DELETE ───────────────────────────────────────────
        elif method == 'DELETE':
            if not row_id:
                return jsonify({'success': False, 'error': 'id requis'}), 400
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'data': {'deleted': int(row_id)}})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── Démarrage ──────────────────────────────────────────────────
def open_browser():
    """Ouvre le navigateur après 1.5 secondes."""
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    print("🏥 Cabinet Médical — Démarrage...")
    print(f"📁 Base de données : {DB_PATH}")

    init_db()
    print("✅ Base de données prête")

    # Ouvrir le navigateur automatiquement
    threading.Thread(target=open_browser, daemon=True).start()

    print("🌐 Serveur sur http://localhost:5000")
    print("   Fermez cette fenêtre pour quitter.\n")

    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
