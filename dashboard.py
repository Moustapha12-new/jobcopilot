"""
dashboard.py — Interface terminal interactive (Rich TUI)
"""
import json
import sys
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich import box
from rich.rule import Rule
from rich.layout import Layout
from rich.align import Align

import database as db

console = Console()

COULEURS = {
    "POSTULER": "bold green",
    "PEUT-ETRE": "bold yellow",
    "IGNORER": "dim red",
    "A": "bold green",
    "B": "green",
    "C": "yellow",
    "D": "orange3",
    "F": "red",
    "nouveau": "cyan",
    "scoré": "blue",
    "postulé": "green",
    "refusé": "red",
    "entretien": "bold magenta",
}


def afficher_banniere():
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🎓 JobCopilot Étudiant ISE[/]\n"
        "[dim]Scanner automatique · Matching IA · Générateur CV/LM[/]",
        border_style="cyan"
    ))
    console.print()


def afficher_stats():
    stats = db.get_stats()
    cards = [
        Panel(f"[bold cyan]{stats['total_offres']}[/]\n[dim]offres scannées[/]",
              border_style="cyan", padding=(0, 2)),
        Panel(f"[bold green]{stats['a_postuler']}[/]\n[dim]à postuler[/]",
              border_style="green", padding=(0, 2)),
        Panel(f"[bold yellow]{stats['postulees']}[/]\n[dim]candidatures envoyées[/]",
              border_style="yellow", padding=(0, 2)),
        Panel(f"[bold magenta]{stats['reponses']}[/]\n[dim]réponses reçues[/]",
              border_style="magenta", padding=(0, 2)),
    ]
    console.print(Columns(cards, equal=True))
    console.print()


def afficher_offres(offres: list[dict], titre="Offres"):
    if not offres:
        console.print("[dim]Aucune offre à afficher.[/]\n")
        return

    table = Table(
        title=titre,
        box=box.ROUNDED,
        show_header=True,
        header_style="bold blue",
        show_lines=False,
        expand=True,
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Titre", min_width=25, max_width=40)
    table.add_column("Entreprise", min_width=12, max_width=18)
    table.add_column("Lieu", min_width=12, max_width=16)
    table.add_column("Score", width=7, justify="center")
    table.add_column("Reco", width=12, justify="center")
    table.add_column("Profil", width=11, justify="center")
    table.add_column("Statut", width=10, justify="center")

    for o in offres:
        score = o.get("score", 0)
        reco = o.get("recommandation", "?")
        note = ""
        if o.get("score_detail"):
            try:
                d = json.loads(o["score_detail"])
                note = d.get("note_lettre", "")
            except Exception:
                pass

        score_str = f"{score:.1f}/10" if score else "—"
        note_str = f"[{COULEURS.get(note, 'white')}]{note}[/]" if note else "—"
        reco_str = f"[{COULEURS.get(reco, 'white')}]{reco}[/]"
        statut_str = f"[{COULEURS.get(o.get('statut',''), 'white')}]{o.get('statut','?')}[/]"
        profil = o.get("profil_match", "")[:10] or "—"

        table.add_row(
            str(o.get("id", "")),
            o.get("titre", "")[:40],
            o.get("entreprise", "")[:18],
            o.get("lieu", "")[:16],
            score_str,
            reco_str,
            profil,
            statut_str,
        )

    console.print(table)
    console.print()


def afficher_detail_offre(offre_id: int):
    offres = db.get_offres(limit=1000)
    offre = next((o for o in offres if o["id"] == offre_id), None)
    if not offre:
        console.print(f"[red]Offre #{offre_id} introuvable.[/]")
        return

    console.print()
    console.print(Panel(
        f"[bold]{offre['titre']}[/]\n"
        f"[cyan]{offre['entreprise']}[/] · {offre['lieu']} · {offre['type_contrat']}\n"
        f"[link={offre['lien']}]{offre['lien']}[/link]",
        title=f"Offre #{offre_id}",
        border_style="blue"
    ))

    if offre.get("score_detail"):
        try:
            d = json.loads(offre["score_detail"])
            console.print(Panel(
                f"[bold]Score : {d.get('score_global', 0):.1f}/10  ({d.get('note_lettre', '?')})[/]\n"
                f"[green]Recommandation : {d.get('recommandation', '?')}[/]\n\n"
                f"[bold]Points forts :[/]\n" +
                "\n".join(f"  ✓ {p}" for p in d.get("points_forts", [])) +
                f"\n\n[bold]Points faibles :[/]\n" +
                "\n".join(f"  ✗ {p}" for p in d.get("points_faibles", [])) +
                f"\n\n[italic]{d.get('explication', '')}[/]",
                title="Analyse IA",
                border_style="green" if d.get("recommandation") == "POSTULER" else "yellow"
            ))
        except Exception:
            pass

    if offre.get("lm_generee"):
        if Confirm.ask("Afficher la lettre de motivation générée ?"):
            console.print(Panel(offre["lm_generee"], title="Lettre de motivation", border_style="purple"))

    if offre.get("cv_genere"):
        if Confirm.ask("Afficher le CV adapté ?"):
            console.print(Panel(offre["cv_genere"], title="CV adapté (ATS)", border_style="blue"))

    console.print()


def menu_principal():
    afficher_banniere()
    afficher_stats()

    while True:
        console.print(Rule("[bold]Menu principal[/]"))
        console.print("""
  [bold cyan]1[/]  Voir toutes les offres à postuler (score ≥ 7)
  [bold cyan]2[/]  Voir toutes les offres (peut-être, score ≥ 5)
  [bold cyan]3[/]  Voir le détail d'une offre
  [bold cyan]4[/]  Marquer une offre comme postulée
  [bold cyan]5[/]  Voir les candidatures envoyées
  [bold cyan]6[/]  Rafraîchir les stats
  [bold cyan]0[/]  Quitter
""")
        choix = Prompt.ask("[bold]Choix[/]", default="1")

        if choix == "1":
            offres = db.get_offres(score_min=7.0)
            afficher_offres(offres, titre=f"À postuler ({len(offres)} offres, score ≥ 7)")

        elif choix == "2":
            offres = db.get_offres(score_min=5.0)
            afficher_offres(offres, titre=f"Pertinentes ({len(offres)} offres, score ≥ 5)")

        elif choix == "3":
            oid = Prompt.ask("Numéro de l'offre")
            try:
                afficher_detail_offre(int(oid))
            except ValueError:
                console.print("[red]Numéro invalide.[/]")

        elif choix == "4":
            oid = Prompt.ask("Numéro de l'offre à marquer 'postulée'")
            try:
                db.marquer_postule(int(oid))
                console.print(f"[green]✓ Offre #{oid} marquée comme postulée.[/]")
            except ValueError:
                console.print("[red]Numéro invalide.[/]")

        elif choix == "5":
            offres = db.get_offres(statut="postulé")
            afficher_offres(offres, titre=f"Candidatures envoyées ({len(offres)})")

        elif choix == "6":
            afficher_stats()

        elif choix == "0":
            console.print("[dim]À bientôt ![/]")
            sys.exit(0)


if __name__ == "__main__":
    db.init_db()
    menu_principal()
