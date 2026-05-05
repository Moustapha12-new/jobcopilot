"""
server.py — Serveur web Flask pour JobCopilot
Lance avec : python server.py
Accès : http://localhost:5000
VERSION CORRIGÉE — Encodage Windows + Gemini
"""
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import yaml
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Ajoute le dossier courant au path pour importer les modules
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

import database as db
import scanner as sc
import ai_engine as ai

app = Flask(__name__, static_folder="web", static_url_path="")
CORS(app)

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# CORRECTION: Encodage UTF-8 explicite pour Windows
# Sur Windows, le terminal utilise cp1252 par défaut, ce qui cause des erreurs
# avec les emojis et caractères spéciaux.
import io

# Forcer l'encodage UTF-8 pour stdout/stderr sur Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"server_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("jobcopilot.server")

# État global du pipeline
pipeline_state = {
    "running": False,
    "step": "",
    "progress": 0,
    "total": 0,
    "last_run": None,
    "last_result": None,
    "log": [],
    "scheduler_active": False,
    "next_run": None,
}


def load_config():
    profile_path = BASE_DIR / "profiles" / "profile.yml"
    cv_path = BASE_DIR / "profiles" / "cv.md"
    with open(profile_path, "r", encoding="utf-8") as f:
        yaml_str = f.read()
        config = yaml.safe_load(yaml_str)
    cv_md = cv_path.read_text(encoding="utf-8") if cv_path.exists() else ""
    return config, yaml_str, cv_md


def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    pipeline_state["log"].append(f"[{ts}] {msg}")
    if len(pipeline_state["log"]) > 200:
        pipeline_state["log"] = pipeline_state["log"][-200:]
    logger.info(msg)


def run_pipeline_thread(scan=True, score=True, generer_docs=True):
    if pipeline_state["running"]:
        return {"error": "Pipeline déjà en cours"}

    def worker():
        pipeline_state["running"] = True
        pipeline_state["log"] = []
        pipeline_state["step"] = "Démarrage..."
        pipeline_state["progress"] = 0
        pipeline_state["total"] = 0

        try:
            db.init_db()
            config, profil_yaml, cv_md = load_config()
            add_log(f"Profil chargé : {config.get('nom', '?')}")

            nouvelles = 0
            scorees = 0
            docs = 0

            # SCAN
            if scan:
                pipeline_state["step"] = "Scan des offres en cours..."
                add_log("Démarrage du scan...")
                offres = sc.lancer_scan(config)
                add_log(f"Scan terminé : {len(offres)} offres trouvées")

                for o in offres:
                    oid = db.insert_offre(o)
                    if oid:
                        nouvelles += 1
                add_log(f"{nouvelles} nouvelles offres enregistrées")

            # SCORING
            if score:
                pipeline_state["step"] = "Scoring IA..."
                offres_a_scorer = db.get_offres(statut="nouveau", limit=50)
                pipeline_state["total"] = len(offres_a_scorer)

                if offres_a_scorer:
                    # Vérifie clé API
                    try:
                        ai.get_client()
                    except ValueError as e:
                        # CORRECTION: Messages sans emojis pour éviter UnicodeEncodeError
                        add_log(f"[ATTENTION] Clé API manquante : {e}")
                        pipeline_state["step"] = "Terminé (sans scoring — clé API manquante)"
                        pipeline_state["running"] = False
                        pipeline_state["last_run"] = datetime.now().isoformat()
                        return

                    add_log(f"{len(offres_a_scorer)} offres à scorer...")
                    for i, offre in enumerate(offres_a_scorer):
                        pipeline_state["progress"] = i + 1
                        pipeline_state["step"] = f"Score de : {offre['titre'][:45]}..."
                        try:
                            score_data = ai.scorer_offre(offre, profil_yaml)
                            db.update_score(
                                offre["id"],
                                score_data.get("score_global", 0),
                                json.dumps(score_data, ensure_ascii=False),
                                score_data.get("recommandation", "IGNORER"),
                                score_data.get("profil_match", ""),
                            )
                            scorees += 1

                            reco = score_data.get("recommandation", "")
                            if generer_docs and reco in ("POSTULER", "PEUT-ETRE") and cv_md:
                                cv_a = ai.generer_cv_adapte(offre, cv_md)
                                lm = ai.generer_lettre_motivation(offre, profil_yaml)
                                db.update_cv_lm(offre["id"], cv_a, lm)
                                docs += 1
                        except Exception as e:
                            add_log(f"Erreur scoring #{offre['id']}: {e}")
                        time.sleep(0.2)

                    add_log(f"Scoring terminé : {scorees} scorées, {docs} CV/LM générés")

            result = {
                "nouvelles": nouvelles, "scorees": scorees,
                "docs": docs, "date": datetime.now().isoformat()
            }
            pipeline_state["last_result"] = result
            pipeline_state["last_run"] = datetime.now().isoformat()
            pipeline_state["step"] = f"Terminé OK ({nouvelles} nouvelles, {scorees} scorées)"
            add_log(f"Pipeline terminé : {nouvelles} nouvelles, {scorees} scorées, {docs} docs")

        except Exception as e:
            pipeline_state["step"] = f"Erreur : {e}"
            add_log(f"ERREUR pipeline : {e}")
            logger.exception("Erreur pipeline")
        finally:
            pipeline_state["running"] = False

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return {"started": True}


# ─── Scheduler automatique ───
scheduler_thread = None
scheduler_stop = threading.Event()


def scheduler_worker():
    add_log("Scheduler démarré — scan quotidien à 07:30")
    while not scheduler_stop.is_set():
        now = datetime.now()
        if now.hour == 7 and now.minute == 30 and not pipeline_state["running"]:
            add_log("Lancement automatique du pipeline quotidien")
            run_pipeline_thread()
        # Calcule prochaine exécution
        from datetime import timedelta
        next_run = now.replace(hour=7, minute=30, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        pipeline_state["next_run"] = next_run.strftime("%d/%m à %H:%M")
        time.sleep(60)


# ─────────────────────────────────────────────
# API ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/api/stats")
def api_stats():
    db.init_db()
    return jsonify(db.get_stats())


@app.route("/api/offres")
def api_offres():
    db.init_db()
    score_min = request.args.get("score_min", type=float)
    statut = request.args.get("statut")
    limit = request.args.get("limit", 100, type=int)
    offres = db.get_offres(statut=statut, score_min=score_min, limit=limit)
    return jsonify(offres)


@app.route("/api/offre/<int:offre_id>")
def api_offre_detail(offre_id):
    db.init_db()
    offres = db.get_offres(limit=9999)
    offre = next((o for o in offres if o["id"] == offre_id), None)
    if not offre:
        return jsonify({"error": "Offre introuvable"}), 404
    if offre.get("score_detail"):
        try:
            offre["score_detail_parsed"] = json.loads(offre["score_detail"])
        except Exception:
            pass
    return jsonify(offre)


@app.route("/api/postuler/<int:offre_id>", methods=["POST"])
def api_postuler(offre_id):
    db.init_db()
    db.marquer_postule(offre_id)
    return jsonify({"ok": True})


@app.route("/api/pipeline/start", methods=["POST"])
def api_pipeline_start():
    data = request.json or {}
    result = run_pipeline_thread(
        scan=data.get("scan", True),
        score=data.get("score", True),
        generer_docs=data.get("generer_docs", True),
    )
    return jsonify(result)


@app.route("/api/pipeline/status")
def api_pipeline_status():
    return jsonify(pipeline_state)


@app.route("/api/scheduler/start", methods=["POST"])
def api_scheduler_start():
    global scheduler_thread
    if not pipeline_state["scheduler_active"]:
        scheduler_stop.clear()
        scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
        scheduler_thread.start()
        pipeline_state["scheduler_active"] = True
        add_log("Scheduler activé — scan quotidien à 07:30")
    return jsonify({"active": True})


@app.route("/api/scheduler/stop", methods=["POST"])
def api_scheduler_stop():
    scheduler_stop.set()
    pipeline_state["scheduler_active"] = False
    pipeline_state["next_run"] = None
    add_log("Scheduler désactivé")
    return jsonify({"active": False})


@app.route("/api/profile")
def api_profile():
    try:
        config, _, _ = load_config()
        return jsonify({
            "nom": config.get("nom", ""),
            "email": config.get("email", ""),
            "ecole": config.get("ecole", ""),
            "niveau": config.get("niveau_etude", ""),
            "domaines": config.get("domaines", []),
            "profil_terrain_actif": config.get("profil_terrain", {}).get("actif", False),
            "profil_remote_actif": config.get("profil_remote", {}).get("actif", False),
            "profil_alternance_actif": config.get("profil_alternance", {}).get("actif", False),
            "sources": config.get("sources", {}),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/logs")
def api_logs():
    return jsonify({"logs": pipeline_state["log"][-100:]})


if __name__ == "__main__":
    db.init_db()
    print("\n" + "="*50)
    print("  JobCopilot Etudiant ISE — Serveur Web")
    print("="*50)
    print(f"  -> Ouvre http://localhost:5000 dans ton navigateur")
    print(f"  -> Ctrl+C pour arrêter")
    print("="*50 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
