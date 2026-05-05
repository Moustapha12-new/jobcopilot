"""
database.py — Gestion SQLite des offres et candidatures
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "jobcopilot.db"


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS offres (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        titre       TEXT NOT NULL,
        entreprise  TEXT,
        lieu        TEXT,
        type_contrat TEXT,
        teletravail INTEGER DEFAULT 0,
        salaire     TEXT,
        description TEXT,
        lien        TEXT UNIQUE,
        source      TEXT,
        profil_match TEXT,
        score       REAL DEFAULT 0,
        score_detail TEXT,
        recommandation TEXT,
        date_scrape TEXT,
        date_postuler TEXT,
        statut      TEXT DEFAULT 'nouveau',
        cv_genere   TEXT,
        lm_generee  TEXT,
        notes       TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS candidatures (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        offre_id    INTEGER,
        date_envoi  TEXT,
        statut      TEXT DEFAULT 'envoyée',
        reponse     TEXT,
        date_reponse TEXT,
        notes       TEXT,
        FOREIGN KEY (offre_id) REFERENCES offres(id)
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        date     TEXT,
        offres_scannees INTEGER DEFAULT 0,
        offres_pertinentes INTEGER DEFAULT 0,
        candidatures_envoyees INTEGER DEFAULT 0,
        reponses INTEGER DEFAULT 0
    )""")

    conn.commit()
    conn.close()


def insert_offre(offre: dict) -> int | None:
    """Insère une offre, retourne l'id ou None si doublon."""
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO offres
            (titre, entreprise, lieu, type_contrat, teletravail, salaire,
             description, lien, source, date_scrape, statut)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            offre.get("titre", ""),
            offre.get("entreprise", ""),
            offre.get("lieu", ""),
            offre.get("type_contrat", ""),
            1 if offre.get("teletravail") else 0,
            offre.get("salaire", ""),
            offre.get("description", ""),
            offre.get("lien", ""),
            offre.get("source", ""),
            datetime.now().isoformat(),
            "nouveau"
        ))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None  # doublon
    finally:
        conn.close()


def update_score(offre_id: int, score: float, detail: str, recommandation: str, profil: str):
    conn = get_conn()
    conn.execute("""
        UPDATE offres SET score=?, score_detail=?, recommandation=?, profil_match=?, statut='scoré'
        WHERE id=?
    """, (score, detail, recommandation, profil, offre_id))
    conn.commit()
    conn.close()


def update_cv_lm(offre_id: int, cv: str, lm: str):
    conn = get_conn()
    conn.execute("UPDATE offres SET cv_genere=?, lm_generee=? WHERE id=?", (cv, lm, offre_id))
    conn.commit()
    conn.close()


def marquer_postule(offre_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE offres SET statut='postulé', date_postuler=? WHERE id=?",
        (datetime.now().isoformat(), offre_id)
    )
    conn.execute(
        "INSERT INTO candidatures (offre_id, date_envoi, statut) VALUES (?,?,?)",
        (offre_id, datetime.now().isoformat(), "envoyée")
    )
    conn.commit()
    conn.close()


def get_offres(statut=None, score_min=None, limit=100):
    conn = get_conn()
    q = "SELECT * FROM offres WHERE 1=1"
    params = []
    if statut:
        q += " AND statut=?"
        params.append(statut)
    if score_min is not None:
        q += " AND score >= ?"
        params.append(score_min)
    q += " ORDER BY score DESC, date_scrape DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM offres").fetchone()[0]
    a_postuler = conn.execute("SELECT COUNT(*) FROM offres WHERE recommandation='POSTULER'").fetchone()[0]
    postulees = conn.execute("SELECT COUNT(*) FROM offres WHERE statut='postulé'").fetchone()[0]
    reponses = conn.execute("SELECT COUNT(*) FROM candidatures WHERE statut != 'envoyée'").fetchone()[0]
    conn.close()
    return {
        "total_offres": total,
        "a_postuler": a_postuler,
        "postulees": postulees,
        "reponses": reponses,
    }
