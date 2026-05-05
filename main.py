"""
main.py — Orchestrateur principal du JobCopilot Étudiant ISE

Usage :
  python main.py              → Lance le scan + scoring complet
  python main.py --dashboard  → Ouvre le tableau de bord interactif
  python main.py --daemon     → Mode automatique quotidien (scheduler)
  python main.py --scan-only  → Scan uniquement, sans scoring IA
  python main.py --score-only → Score les offres déjà scannées (non scorées)
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml
import schedule
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.rule import Rule

import database as db
import scanner as sc
import ai_engine as ai

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"jobcopilot_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("jobcopilot.main")
console = Console()


# ─────────────────────────────────────────────
# CHARGEMENT PROFIL
# ─────────────────────────────────────────────

def charger_profil() -> tuple[dict, str, str]:
    """Charge profile.yml et cv.md. Retourne (config dict, yaml str, cv str)."""
    profile_path = BASE_DIR / "profiles" / "profile.yml"
    cv_path = BASE_DIR / "profiles" / "cv.md"

    if not profile_path.exists():
        console.print(f"[red]❌ Fichier manquant : {profile_path}[/]")
        console.print("[yellow]  → Copie profiles/profile.yml.example et remplis tes informations[/]")
        sys.exit(1)

    with open(profile_path, "r", encoding="utf-8") as f:
        profil_yaml_str = f.read()
        config = yaml.safe_load(profil_yaml_str)

    cv_md = ""
    if cv_path.exists():
        cv_md = cv_path.read_text(encoding="utf-8")
    else:
        console.print("[yellow]⚠ cv.md introuvable — la génération de CV sera désactivée[/]")

    return config, profil_yaml_str, cv_md


# ─────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────

def run_pipeline(scan=True, score=True, generer_docs=True):
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]🚀 JobCopilot — Lancement du pipeline[/]\n"
        f"[dim]{datetime.now().strftime('%A %d %B %Y à %H:%M')}[/]",
        border_style="cyan"
    ))
    console.print()

    # Init DB
    db.init_db()

    # Chargement profil
    config, profil_yaml, cv_md = charger_profil()
    nom = config.get("nom", "étudiant")
    console.print(f"[green]✓[/] Profil chargé : [bold]{nom}[/]")

    nouvelles = 0
    scorees = 0
    docs_generees = 0

    # ── ÉTAPE 1 : SCAN ──
    if scan:
        console.print()
        console.print(Rule("[bold]Étape 1 — Scan des offres[/]"))
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Scan en cours...", total=None)
            offres_brutes = sc.lancer_scan(config)
            progress.update(task, description=f"Scan terminé — {len(offres_brutes)} offres trouvées")

        console.print(f"[green]✓[/] {len(offres_brutes)} offres récupérées")

        # Insertion en base (dédupliquée)
        for offre in offres_brutes:
            oid = db.insert_offre(offre)
            if oid:
                nouvelles += 1

        console.print(f"[green]✓[/] {nouvelles} nouvelles offres enregistrées ({len(offres_brutes) - nouvelles} doublons ignorés)")

    # ── ÉTAPE 2 : SCORING IA ──
    if score:
        console.print()
        console.print(Rule("[bold]Étape 2 — Scoring IA (matching)[/]"))

        # Récupère les offres non scorées
        offres_a_scorer = db.get_offres(statut="nouveau", limit=50)

        if not offres_a_scorer:
            console.print("[dim]Aucune nouvelle offre à scorer.[/]")
        else:
            console.print(f"[blue]ℹ[/] {len(offres_a_scorer)} offres à scorer")

            # Vérification clé API
            try:
                ai.get_client()
            except ValueError as e:
                console.print(f"[yellow]⚠ {e}[/]")
                console.print("[yellow]  → Le scoring IA est désactivé. Lance avec --scan-only pour continuer sans IA.[/]")
                return

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Scoring...", total=len(offres_a_scorer))

                for offre in offres_a_scorer:
                    progress.update(task, description=f"  {offre['titre'][:40]}...")

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

                        # Génération CV/LM si score suffisant
                        reco = score_data.get("recommandation", "")
                        if generer_docs and reco in ("POSTULER", "PEUT-ETRE") and cv_md:
                            try:
                                cv_adapte = ai.generer_cv_adapte(offre, cv_md)
                                lm = ai.generer_lettre_motivation(offre, profil_yaml)
                                db.update_cv_lm(offre["id"], cv_adapte, lm)
                                docs_generees += 1
                            except Exception as e:
                                logger.warning(f"Génération docs échouée pour #{offre['id']}: {e}")

                    except Exception as e:
                        logger.error(f"Scoring échoué pour #{offre['id']} '{offre['titre']}': {e}")

                    progress.advance(task)
                    time.sleep(0.3)  # pause courte entre appels API

    # ── RÉSUMÉ ──
    console.print()
    console.print(Rule("[bold]Résumé[/]"))
    stats = db.get_stats()

    console.print(f"""
  [green]✓[/] Nouvelles offres : [bold]{nouvelles}[/]
  [green]✓[/] Offres scorées aujourd'hui : [bold]{scorees}[/]
  [green]✓[/] CV/LM générés : [bold]{docs_generees}[/]
  ───────────────────────────────
  [cyan]Total offres en base : {stats['total_offres']}[/]
  [green]À postuler (score ≥ 7) : {stats['a_postuler']}[/]
  [yellow]Candidatures envoyées : {stats['postulees']}[/]
  [magenta]Réponses reçues : {stats['reponses']}[/]
""")

    if stats["a_postuler"] > 0:
        console.print(
            f"[bold green]🎯 {stats['a_postuler']} offre(s) à postuler maintenant ![/]\n"
            f"[dim]   → Lance : python main.py --dashboard[/]"
        )

    console.print()
    logger.info(f"Pipeline terminé — {nouvelles} nouvelles, {scorees} scorées, {docs_generees} docs générées")


# ─────────────────────────────────────────────
# MODE DAEMON (scheduler quotidien)
# ─────────────────────────────────────────────

def run_daemon():
    console.print(Panel.fit(
        "[bold cyan]🔄 Mode daemon activé[/]\n"
        "[dim]Le pipeline se lancera automatiquement chaque matin à 07:30[/]\n"
        "[dim]Appuie sur Ctrl+C pour arrêter[/]",
        border_style="cyan"
    ))

    def job():
        logger.info("Lancement automatique du pipeline quotidien")
        run_pipeline()

    schedule.every().day.at("07:30").do(job)

    # Lance aussi immédiatement au démarrage
    console.print("[yellow]Lancement immédiat du premier scan...[/]")
    run_pipeline()

    while True:
        schedule.run_pending()
        prochaine = schedule.next_run()
        if prochaine:
            delta = prochaine - datetime.now()
            heures = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            console.print(
                f"[dim]⏰ Prochain scan dans {heures}h{minutes:02d}m "
                f"({prochaine.strftime('%H:%M')})[/]",
                end="\r"
            )
        time.sleep(60)


# ─────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="JobCopilot Étudiant ISE — Scanner automatique d'offres d'emploi"
    )
    parser.add_argument("--dashboard", action="store_true",
                        help="Ouvre le tableau de bord interactif")
    parser.add_argument("--daemon", action="store_true",
                        help="Mode automatique quotidien (scheduler)")
    parser.add_argument("--scan-only", action="store_true",
                        help="Scan uniquement, sans scoring IA")
    parser.add_argument("--score-only", action="store_true",
                        help="Score les offres déjà en base (non scorées)")
    parser.add_argument("--no-docs", action="store_true",
                        help="Ne génère pas les CV/LM")

    args = parser.parse_args()

    if args.dashboard:
        from dashboard import menu_principal
        db.init_db()
        menu_principal()

    elif args.daemon:
        run_daemon()

    elif args.scan_only:
        run_pipeline(scan=True, score=False, generer_docs=False)

    elif args.score_only:
        run_pipeline(scan=False, score=True, generer_docs=not args.no_docs)

    else:
        run_pipeline(scan=True, score=True, generer_docs=not args.no_docs)


if __name__ == "__main__":
    main()
