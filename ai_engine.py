"""
ai_engine.py — Matching IA + génération CV/LM via Gemini API
VERSION CORRIGÉE — Mai 2026
"""
import os
import json
import logging
from pathlib import Path

from google import genai

logger = logging.getLogger("jobcopilot.ai")


# Clé API lue depuis variable d'environnement ou fichier .env
def get_client():
    """
    Client Gemini basé sur la variable d'environnement GEMINI_API_KEY
    ou un fichier .env (clé GEMINI_API_KEY=...).
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")

    if not api_key:
        # Lecture éventuelle depuis .env à côté de ce fichier
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding='utf-8').splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"')

    if not api_key:
        raise ValueError(
            "[ERREUR] Clé API Gemini manquante.\n"
            "→ Crée un fichier .env dans le dossier jobcopilot/\n"
            "→ Ajoute : GEMINI_API_KEY=ta_cle_api (clé Google AI Studio)\n"
            "→ Ou définis la variable d'environnement GEMINI_API_KEY\n"
            "→ Obtiens une clé gratuite sur : https://aistudio.google.com/app/apikey"
        )

    # Le client lit la clé via GEMINI_API_KEY
    os.environ["GEMINI_API_KEY"] = api_key
    return genai.Client(api_key=api_key)


# ─────────────────────────────────────────────
# SCORING IA
# ─────────────────────────────────────────────

PROMPT_SCORING = """
Tu es un assistant de recherche d'emploi étudiant expert.

Voici le profil du candidat :
{profil}

Voici l'offre d'emploi :
Titre : {titre}
Entreprise : {entreprise}
Lieu : {lieu}
Type de contrat : {contrat}
Description : {description}

Évalue la compatibilité entre ce profil et cette offre.

Réponds UNIQUEMENT en JSON valide, sans aucun autre texte, avec exactement cette structure :
{{
  "score_global": <float entre 0 et 10>,
  "note_lettre": "<A/B/C/D/F>",
  "recommandation": "<POSTULER/PEUT-ETRE/IGNORER>",
  "profil_match": "<terrain/remote/alternance>",
  "dimensions": {{
    "competences": <0-10>,
    "lieu": <0-10>,
    "horaires": <0-10>,
    "salaire": <0-10>,
    "interet": <0-10>
  }},
  "points_forts": ["<point 1>", "<point 2>"],
  "points_faibles": ["<point 1>"],
  "explication": "<2-3 phrases courtes>"
}}

Règles de scoring :
- POSTULER si score >= 7
- PEUT-ETRE si score entre 5 et 7
- IGNORER si score < 5
- Sois réaliste : un étudiant ingénieur ne convient pas à un poste de DRH senior
"""


def scorer_offre(offre: dict, profil_yaml: str) -> dict:
    """Score une offre avec l'IA. Retourne un dict avec score et recommandation."""
    client = get_client()

    prompt = PROMPT_SCORING.format(
        profil=profil_yaml[:2000],
        titre=offre.get("titre", ""),
        entreprise=offre.get("entreprise", ""),
        lieu=offre.get("lieu", ""),
        contrat=offre.get("type_contrat", ""),
        description=offre.get("description", "")[:1000],
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        texte = response.text.strip()

        # Nettoyer le JSON si besoin
        if "```" in texte:
            texte = texte.split("```")[1].lstrip("json").strip()

        return json.loads(texte)

    except json.JSONDecodeError as e:
        logger.warning(f"JSON invalide pour {offre.get('titre')}: {e}")
        return {
            "score_global": 0,
            "note_lettre": "F",
            "recommandation": "IGNORER",
            "profil_match": "inconnu",
            "dimensions": {},
            "points_forts": [],
            "points_faibles": [],
            "explication": "Erreur de parsing IA",
        }

    except Exception as e:
        logger.error(f"Erreur scoring IA: {e}")
        raise


# ─────────────────────────────────────────────
# GÉNÉRATION CV ADAPTÉ
# ─────────────────────────────────────────────

PROMPT_CV = """
Tu es un expert en recrutement et optimisation ATS.

Voici le CV de base du candidat (en markdown) :
{cv_base}

Voici l'offre d'emploi cible :
Titre : {titre}
Entreprise : {entreprise}
Description : {description}

Adapte le CV pour maximiser le matching ATS avec cette offre spécifique.
- Réordonne les sections selon les priorités de l'offre
- Mets en avant les compétences et expériences les plus pertinentes
- Intègre naturellement les mots-clés importants de l'offre
- Garde un ton professionnel et factuel
- Ne mens jamais sur les compétences ou expériences
- Conserve le format markdown

Réponds UNIQUEMENT avec le CV adapté en markdown, sans aucun commentaire.
"""


PROMPT_LM = """
Tu es un expert en rédaction de lettres de motivation pour étudiants ingénieurs.

Profil du candidat :
{profil_court}

Offre :
Titre : {titre}
Entreprise : {entreprise}
Description : {description}

Rédige une lettre de motivation courte (250-300 mots max) et percutante.
Structure : accroche forte → valeur ajoutée pour l'entreprise → motivation pour ce poste → conclusion avec appel à l'action.
Ton : professionnel mais dynamique, adapté à un étudiant ingénieur.
Ne mets pas de formule de politesse longue.

Réponds UNIQUEMENT avec la lettre, sans commentaire.
"""


PROMPT_REPONSES = """
Tu es un coach de recrutement.
Pour ce poste : {titre} chez {entreprise}

Génère des réponses courtes et percutantes aux 3 questions classiques :
1. "Pourquoi ce poste ?"
2. "Pourquoi cette entreprise ?"
3. "Quelle est votre disponibilité ?"

Profil candidat : {profil_court}

Réponds en JSON :
{{"pourquoi_poste": "...", "pourquoi_entreprise": "...", "disponibilite": "..."}}
"""


def generer_cv_adapte(offre: dict, cv_base: str) -> str:
    """Génère un CV adapté à l'offre."""
    client = get_client()
    prompt = PROMPT_CV.format(
        cv_base=cv_base[:3000],
        titre=offre.get("titre", ""),
        entreprise=offre.get("entreprise", ""),
        description=offre.get("description", "")[:1500],
    )
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Erreur génération CV: {e}")
        return cv_base


def generer_lettre_motivation(offre: dict, profil_yaml: str) -> str:
    """Génère une lettre de motivation adaptée."""
    client = get_client()

    # Extrait le résumé du profil
    profil_court = profil_yaml[:800]

    prompt = PROMPT_LM.format(
        profil_court=profil_court,
        titre=offre.get("titre", ""),
        entreprise=offre.get("entreprise", ""),
        description=offre.get("description", "")[:1000],
    )
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Erreur génération LM: {e}")
        return ""


def generer_reponses_questions(offre: dict, profil_yaml: str) -> dict:
    """Génère les réponses aux questions classiques de formulaire."""
    client = get_client()
    prompt = PROMPT_REPONSES.format(
        titre=offre.get("titre", ""),
        entreprise=offre.get("entreprise", ""),
        profil_court=profil_yaml[:500],
    )
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        texte = response.text.strip()
        if "```" in texte:
            texte = texte.split("```")[1].lstrip("json").strip()
        return json.loads(texte)
    except Exception as e:
        logger.warning(f"Erreur génération réponses: {e}")
        return {
            "pourquoi_poste": "Ce poste correspond à mes compétences et objectifs.",
            "pourquoi_entreprise": "Cette entreprise est reconnue dans son secteur.",
            "disponibilite": "Disponible immédiatement selon vos besoins.",
        }


# ─────────────────────────────────────────────
# TRAITEMENT BATCH
# ─────────────────────────────────────────────


def traiter_offres_batch(
    offres: list[dict],
    profil_yaml: str,
    cv_md: str,
    generer_docs: bool = True,
    callback=None,
) -> list[dict]:
    """
    Score toutes les offres et génère CV/LM pour celles qui valent la peine.
    callback(i, total, offre) appelé à chaque offre pour afficher la progression.
    """
    resultats = []

    for i, offre in enumerate(offres):
        if callback:
            callback(i + 1, len(offres), offre)

        # Scoring
        try:
            score_data = scorer_offre(offre, profil_yaml)
        except Exception as e:
            logger.error(f"Scoring échoué pour '{offre.get('titre')}': {e}")
            continue

        offre["score"] = score_data.get("score_global", 0)
        offre["score_detail"] = json.dumps(score_data, ensure_ascii=False)
        offre["recommandation"] = score_data.get("recommandation", "IGNORER")
        offre["profil_match"] = score_data.get("profil_match", "")

        # Génération CV/LM uniquement si score suffisant
        if generer_docs and score_data.get("recommandation") in ("POSTULER", "PEUT-ETRE"):
            try:
                offre["cv_genere"] = generer_cv_adapte(offre, cv_md)
                offre["lm_generee"] = generer_lettre_motivation(offre, profil_yaml)
            except Exception as e:
                logger.warning(f"Génération docs échouée: {e}")
                offre["cv_genere"] = cv_md
                offre["lm_generee"] = ""

        resultats.append(offre)

    return resultats
