"""
scanner.py — Scraping des offres d'emploi
Sources : StudentJob, Hellowork, pages carrières EDF/Engie/Enedis/RTE, France Travail, Indeed
VERSION CORRIGÉE — Mai 2026 (URLs fournies par l'utilisateur)
"""
import re
import time
import random
import logging
import os
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("jobcopilot.scanner")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

TIMEOUT = 20


def _get(url: str, extra_headers=None) -> BeautifulSoup | None:
    """Requête HTTP avec gestion d'erreur et délai poli."""
    try:
        time.sleep(random.uniform(2.0, 4.0))  # respecte les serveurs
        headers = HEADERS.copy()
        if extra_headers:
            headers.update(extra_headers)

        session = requests.Session()
        # D'abord visiter la page d'accueil pour obtenir les cookies
        if "hellowork" in url:
            session.get("https://www.hellowork.com/fr-fr/", headers=headers, timeout=TIMEOUT)
        elif "studentjob" in url:
            session.get("https://www.studentjob.fr/", headers=headers, timeout=TIMEOUT)
        elif "jooble" in url:
            session.get("https://fr.jooble.org/", headers=headers, timeout=TIMEOUT)

        r = session.get(url, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        logger.warning(f"Erreur GET {url}: {e}")
        return None


def _clean(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


# ─────────────────────────────────────────────
# STUDENTJOB — CORRIGÉ (URLs fournies)
# ─────────────────────────────────────────────


def scan_studentjob(keywords: list[str], teletravail=False) -> list[dict]:
    """
    StudentJob France — URLs correctes :
    https://www.studentjob.fr/offre?search%5Bkeywords_scope%5D=MOT_CLE&search%5Bzipcode_eq%5D=
    """
    offres = []
    seen_links = set()

    for kw in keywords:
        kw_url = kw.replace(" ", "+")
        url = f"https://www.studentjob.fr/offre?search%5Bkeywords_scope%5D={kw_url}&search%5Bzipcode_eq%5D="

        soup = _get(url)
        if not soup:
            continue

        # Sélecteurs pour la structure actuelle de StudentJob
        cards = soup.select("article.job-card, div.job-card, .vacancy-item, li[data-vacancy-id], .offer-card")
        if not cards:
            # fallback générique
        # Structure réelle StudentJob: liens dans des éléments <a> avec href contenant /offre/
                job_links = soup.select('a[href*="/offre/"]')
        fo        
        for job_link in job_links[:15]:
            # Extraire le titre depuis le heading dans le lien
                titre_el = job_link.select_one('h2, h3, h4, [class*="title"], [class*="job-title"]')            titre = _clean(titre_el.get_text()) if titre_el else _clean(job_link.get_text())
            
                            titre = _clean(titre_el.get_text(strip=True)) if titre_el else ""
            
            if not titre or len(titre) < 5 or 'filtre' in titre.lower():
                
                    continue
            # Extraire le lien href
            lien_el = job_link.get('href')
            lien = lien_el if lien_el and lien_el.startswith('http') else f"https://www.studentjob.fr{lien_el}" if lien_el else ""            lien = lien_el["href"] if lien_el else ""
            if lien and not lien.startswith("http"):
                lien = "https://www.studentjob.fr" + lien

            # Éviter les doublons
            if lien in seen_links            
            # Éviter les doublons
            if lien in seen_links:
                continue
            seen_links.add(lien)
            
            # Extraire entreprise, lieu, etc depuis les generics dans le lien
            entreprise_el = job_link.select_one('.company-name, .employer, .job-company')
            entreprise = _clean(entreprise_el.get_text()) if entreprise_el else "N/A"

            entreprise_            
            lieu_el = job_link.select_one('.location, .city, .place, [class*="location"]')
            lieu = _clean(lieu_el.get_text()) if lieu_el else "France"
            
            contrat_el = job_link.select_one('.contract-type, .type, [class*="contract"]')
            contrat = _clean(contrat_el.get_text()) if contrat_el else "job étudiant"
            
            # Créer l'offre
            offres.append({
                "titre": titre,
                "entreprise": entreprise,
                "lieu": lieu,
                "type_contrat": contrat,
                "teletravail": teletravail,
                "salaire": "",
                "description": f"Offre StudentJob pour : {kw}. {titre} chez {entreprise}.",
                "lien": lien,
                "source": "studentjob",
            }) lieu    
    logger.info(f"StudentJob: {len(offres)} offres trouvées")
    return offres


# ─────────────────────────────────────────────
# HELLOWORK — CORRIGÉ (URLs fournies)
# ─────────────────────────────────────────────


def scan_hellowork(keywords: list[str], teletravail=False) -> list[dict]:
    """
    Hellowork — URL correcte :
    https://www.hellowork.com/fr-fr/emploi/recherche.html?k=MOT_CLE&l=LIEU
    """
    offres = []
    seen_links = set()

    for kw in keywords:
        kw_url = kw.replace(" ", "+")

        url = f"https://www.hellowork.com/fr-fr/emploi/recherche.html?k={kw_url}&l="

        soup = _get(url)
        if not soup:
            continue

        # Sélecteurs pour la structure actuelle de Hellowork
        cards = soup.select("article, [data-testid='job-card'], .job-item, .tk-card, .result-card, .card")
        for card in cards[:12]:
            titre_el = card.select_one("h2 a, h3 a, [data-testid='job-title'], .title, h2, h3")
            titre = _clean(titre_el.get_text()) if titre_el else ""
            if not titre or len(titre) < 3:
                continue

            lien_el = card.select_one("a[href]")
            lien = lien_el["href"] if lien_el else ""
            if lien and not lien.startswith("http"):
                lien = "https://www.hellowork.com" + lien

            if lien in seen_links:
                continue
            seen_links.add(lien)

            entreprise_el = card.select_one(".company, .employer-name, [data-testid='company'], [class*='company']")
            entreprise = _clean(entreprise_el.get_text()) if entreprise_el else "N/A"

            lieu_el = card.select_one(".location, [data-testid='location'], .city, [class*='location']")
            lieu = _clean(lieu_el.get_text()) if lieu_el else "France"

            contrat_el = card.select_one(".contract, [class*='contract'], .type")
            contrat = _clean(contrat_el.get_text()) if contrat_el else "CDI/CDD"

            offres.append({
                "titre": titre,
                "entreprise": entreprise,
                "lieu": lieu,
                "type_contrat": contrat,
                "teletravail": teletravail,
                "salaire": "",
                "description": f"Offre Hellowork : {titre} chez {entreprise} à {lieu}.",
                "lien": lien,
                "source": "hellowork",
            })

    logger.info(f"Hellowork: {len(offres)} offres trouvées")
    return offres


# ─────────────────────────────────────────────
# JOOBLE — DÉSACTIVÉ (pas de clé API)
# ─────────────────────────────────────────────


def scan_jooble(keywords: list[str], lieux: list[str]) -> list[dict]:
    """
    Jooble nécessite une clé API. Sans clé, on retourne une liste vide.
    Pour obtenir une clé : https://fr.jooble.org/api
    """
    logger.info("Jooble: désactivé (pas de clé API)")
    return []


# ─────────────────────────────────────────────
# PAGES CARRIÈRES ENTREPRISES ÉNERGIE — CORRIGÉES
# ─────────────────────────────────────────────


def scan_edf() -> list[dict]:
    """
    EDF — URL correcte :
    https://www.edf.fr/edf-recrute/rejoignez-nous/voir-les-offres/nos-offres
    """
    url = "https://www.edf.fr/edf-recrute/rejoignez-nous/voir-les-offres/nos-offres"

    offres = []
    soup = _get(url)
    if not soup:
        return offres

    # EDF charge les offres dynamiquement, essayons plusieurs sélecteurs
    cards = soup.select("article, .offer, .job-item, [class*='offer'], [class*='job'], .card, li.offer")
    seen_links = set()
    for card in cards[:15]:
        titre_el = card.select_one("h2, h3, a, .title, [class*='title']")
        titre = _clean(titre_el.get_text()) if titre_el else ""
        if not titre or len(titre) < 5:
            continue
        lien_el = card.select_one("a[href]")
        lien = lien_el["href"] if lien_el else ""
        if lien and not lien.startswith("http"):
            lien = "https://www.edf.fr" + lien
        if lien in seen_links:
            continue
        seen_links.add(lien)
        lieu_el = card.select_one(".location, .city, .lieu, [class*='location']")
        lieu = _clean(lieu_el.get_text()) if lieu_el else "France"
        offres.append({
            "titre": titre, "entreprise": "EDF", "lieu": lieu,
            "type_contrat": "alternance/CDI", "teletravail": False,
            "salaire": "", "description": f"EDF Recrutement : {titre}",
            "lien": lien, "source": "carrieres_edf",
        })

    logger.info(f"EDF: {len(offres)} offres trouvées")
    return offres


def scan_engie() -> list[dict]:
    """Engie — URL correcte : https://jobs.engie.com/?locale=fr_FR"""
    url = "https://jobs.engie.com/?locale=fr_FR"
    soup = _get(url)
    if not soup:
        return []
    offres = []
    seen_links = set()
    cards = soup.select("li[data-id], article, .job-item, .career-item, [class*='job'], [class*='offer']")
    for card in cards[:15]:
        titre_el = card.select_one("h2, h3, .title, a, [class*='title']")
        titre = _clean(titre_el.get_text()) if titre_el else ""
        if not titre or len(titre) < 5:
            continue
        lien_el = card.select_one("a[href]")
        lien = lien_el["href"] if lien_el else ""
        if lien and not lien.startswith("http"):
            lien = "https://jobs.engie.com" + lien
        if lien in seen_links:
            continue
        seen_links.add(lien)
        lieu_el = card.select_one(".location, .city, [class*='location']")
        lieu = _clean(lieu_el.get_text()) if lieu_el else "France"
        offres.append({
            "titre": titre, "entreprise": "Engie", "lieu": lieu,
            "type_contrat": "alternance", "teletravail": False,
            "salaire": "", "description": f"Engie Jobs : {titre}",
            "lien": lien, "source": "carrieres_engie",
        })
    logger.info(f"Engie: {len(offres)} offres trouvées")
    return offres


def scan_enedis() -> list[dict]:
    """Enedis — URL correcte : https://www.enedis.fr/hub-carriere"""
    url = "https://www.enedis.fr/hub-carriere"
    soup = _get(url)
    if not soup:
        return []
    offres = []
    seen_links = set()
    cards = soup.select("article, .offer-card, li.vacancy, .job-item, [class*='offer'], [class*='job']")
    for card in cards[:15]:
        titre_el = card.select_one("h2, h3, .title, a, [class*='title']")
        titre = _clean(titre_el.get_text()) if titre_el else ""
        if not titre or len(titre) < 5:
            continue
        lien_el = card.select_one("a[href]")
        lien = lien_el["href"] if lien_el else ""
        if lien and not lien.startswith("http"):
            lien = "https://www.enedis.fr" + lien
        if lien in seen_links:
            continue
        seen_links.add(lien)
        lieu_el = card.select_one(".location, .city, .lieu, [class*='location']")
        lieu = _clean(lieu_el.get_text()) if lieu_el else "France"
        offres.append({
            "titre": titre, "entreprise": "Enedis", "lieu": lieu,
            "type_contrat": "alternance/CDI", "teletravail": False,
            "salaire": "", "description": f"Enedis Recrutement : {titre}",
            "lien": lien, "source": "carrieres_enedis",
        })
    logger.info(f"Enedis: {len(offres)} offres trouvées")
    return offres


def scan_rte() -> list[dict]:
    """
    RTE — URL correcte :
    https://www.rte-france.com/carrieres/recrutement
    """
    url = "https://www.rte-france.com/carrieres/recrutement"

    offres = []
    soup = _get(url)
    if not soup:
        return offres

    seen_links = set()
    cards = soup.select("article, .offer, li.job, .card-job, [class*='job'], [class*='offer']")
    for card in cards[:15]:
        titre_el = card.select_one("h2, h3, .title, a, [class*='title']")
        titre = _clean(titre_el.get_text()) if titre_el else ""
        if not titre or len(titre) < 5:
            continue
        lien_el = card.select_one("a[href]")
        lien = lien_el["href"] if lien_el else ""
        if lien and not lien.startswith("http"):
            lien = "https://www.rte-france.com" + lien
        if lien in seen_links:
            continue
        seen_links.add(lien)
        lieu_el = card.select_one(".location, .city, [class*='location']")
        lieu = _clean(lieu_el.get_text()) if lieu_el else "France"
        offres.append({
            "titre": titre, "entreprise": "RTE", "lieu": lieu,
            "type_contrat": "alternance/CDI", "teletravail": False,
            "salaire": "", "description": f"RTE Recrutement : {titre}",
            "lien": lien, "source": "carrieres_rte",
        })

    logger.info(f"RTE: {len(offres)} offres trouvées")
    return offres


# ─────────────────────────────────────────────
# FRANCE TRAVAIL — NOUVELLE SOURCE
# ─────────────────────────────────────────────


def scan_france_travail(keywords: list[str], lieux: list[str]) -> list[dict]:
    """
    France Travail (ex-Pôle Emploi) :
    https://candidat.francetravail.fr/offres/recherche?motsCles=MOT_CLE
    """
    offres = []
    seen_links = set()

    for kw in keywords[:3]:
        kw_param = kw.replace(" ", "%20")
        url = f"https://candidat.francetravail.fr/offres/recherche?motsCles={kw_param}"

        soup = _get(url)
        if not soup:
            continue

        cards = soup.select(".result-card, article, [class*='offer'], [class*='job']")
        for card in cards[:8]:
            titre_el = card.select_one("h2, h3, .title, a, [class*='title']")
            titre = _clean(titre_el.get_text()) if titre_el else ""
            if not titre or len(titre) < 3:
                continue
            lien_el = card.select_one("a[href]")
            lien = lien_el["href"] if lien_el else ""
            if lien and not lien.startswith("http"):
                lien = "https://candidat.francetravail.fr" + lien
            if lien in seen_links:
                continue
            seen_links.add(lien)
            entreprise_el = card.select_one(".company, [class*='company']")
            entreprise = _clean(entreprise_el.get_text()) if entreprise_el else "N/A"
            lieu_el = card.select_one(".location, [class*='location']")
            lieu_final = _clean(lieu_el.get_text()) if lieu_el else "France"

            offres.append({
                "titre": titre,
                "entreprise": entreprise,
                "lieu": lieu_final,
                "type_contrat": "divers",
                "teletravail": False,
                "salaire": "",
                "description": f"France Travail : {titre} chez {entreprise}.",
                "lien": lien,
                "source": "france_travail",
            })

    logger.info(f"France Travail: {len(offres)} offres trouvées")
    return offres


# ─────────────────────────────────────────────
# INDEED — NOUVELLE SOURCE
# ─────────────────────────────────────────────


def scan_indeed(keywords: list[str], lieux: list[str]) -> list[dict]:
    """
    Indeed France :
    https://fr.indeed.com/jobs?q=MOT_CLE&l=LIEU
    """
    offres = []
    seen_links = set()

    for kw in keywords[:3]:
        for lieu in lieux[:1]:
            kw_param = kw.replace(" ", "+")
            lieu_param = lieu.replace(" ", "+")
            url = f"https://fr.indeed.com/jobs?q={kw_param}&l={lieu_param}"

            extra_headers = {
                "Referer": "https://fr.indeed.com/",
            }
            soup = _get(url, extra_headers=extra_headers)
            if not soup:
                continue

            cards = soup.select(".job_seen_beacon, [data-testid='jobTitle'], .slider_container, .result")
            for card in cards[:10]:
                titre_el = card.select_one("h2 a, .jobTitle, [class*='title']")
                titre = _clean(titre_el.get_text()) if titre_el else ""
                if not titre or len(titre) < 3:
                    continue
                lien_el = card.select_one("a[href]")
                lien = lien_el["href"] if lien_el else ""
                if lien and not lien.startswith("http"):
                    lien = "https://fr.indeed.com" + lien
                if lien in seen_links:
                    continue
                seen_links.add(lien)
                entreprise_el = card.select_one(".companyName, [class*='company']")
                entreprise = _clean(entreprise_el.get_text()) if entreprise_el else "N/A"
                lieu_el = card.select_one(".companyLocation, [class*='location']")
                lieu_final = _clean(lieu_el.get_text()) if lieu_el else lieu

                offres.append({
                    "titre": titre,
                    "entreprise": entreprise,
                    "lieu": lieu_final,
                    "type_contrat": "divers",
                    "teletravail": False,
                    "salaire": "",
                    "description": f"Indeed : {titre} chez {entreprise}.",
                    "lien": lien,
                    "source": "indeed",
                })

    logger.info(f"Indeed: {len(offres)} offres trouvées")
    return offres


# ─────────────────────────────────────────────
# FILTRE ANTI-ARNAQUES
# ─────────────────────────────────────────────

MOTS_ARNAQUE = [
    "gagner 5000€ par mois", "travail depuis chez vous sans expérience",
    "investissement requis", "recrutement immédiat sans entretien",
    "multi-level", "mlm", "commission uniquement", "sans diplôme garanti",
    "réseau de vente", "cryptomonnaie", "trading facile",
]

SOURCES_FIABLES = {
    "studentjob", "hellowork", "jooble",
    "carrieres_edf", "carrieres_engie", "carrieres_enedis", "carrieres_rte",
    "france_travail", "indeed",
}


def est_arnaque(offre: dict) -> bool:
    texte = (offre.get("titre", "") + " " + offre.get("description", "")).lower()
    for mot in MOTS_ARNAQUE:
        if mot in texte:
            return True
    if offre.get("source", "") not in SOURCES_FIABLES:
        if not offre.get("lien", "").startswith("http"):
            return True
    return False


# ─────────────────────────────────────────────
# ORCHESTRATEUR DU SCAN — CORRIGÉ
# ─────────────────────────────────────────────


def lancer_scan(config: dict) -> list[dict]:
    """Lance tous les scanners actifs selon la config du profil."""
    toutes_offres = []
    sources = config.get("sources", {})

    logger.info("=== Démarrage du scan ===")

    # Jobs terrain
    terrain = config.get("profil_terrain", {})
    if terrain.get("actif"):
        kws_terrain = terrain.get("titres_cibles", [])[:4]
        if sources.get("studentjob"):
            toutes_offres += scan_studentjob(kws_terrain, teletravail=False)
        if sources.get("hellowork"):
            toutes_offres += scan_hellowork(kws_terrain, teletravail=False)
        if sources.get("jooble"):
            toutes_offres += scan_jooble(kws_terrain, terrain.get("lieux_acceptes", ["Paris"])[:2])
        if sources.get("france_travail"):
            toutes_offres += scan_france_travail(kws_terrain, terrain.get("lieux_acceptes", ["Paris"])[:2])
        if sources.get("indeed"):
            toutes_offres += scan_indeed(kws_terrain, terrain.get("lieux_acceptes", ["Paris"])[:2])

    # Jobs remote
    remote = config.get("profil_remote", {})
    if remote.get("actif"):
        kws_remote = remote.get("titres_cibles", [])[:4]
        if sources.get("studentjob"):
            toutes_offres += scan_studentjob(kws_remote, teletravail=True)
        if sources.get("hellowork"):
            toutes_offres += scan_hellowork(kws_remote, teletravail=True)
        if sources.get("jooble"):
            toutes_offres += scan_jooble(
                [k + " télétravail" for k in kws_remote[:2]],
                ["France"]
            )
        if sources.get("france_travail"):
            toutes_offres += scan_france_travail(kws_remote, ["France"])
        if sources.get("indeed"):
            toutes_offres += scan_indeed(kws_remote, ["France"])

    # Alternance énergie
    alternance = config.get("profil_alternance", {})
    if alternance.get("actif"):
        kws_alt = alternance.get("titres_cibles", [])[:3]
        if sources.get("jooble"):
            toutes_offres += scan_jooble(kws_alt, ["Paris", "Île-de-France"])
        if sources.get("hellowork"):
            toutes_offres += scan_hellowork(kws_alt, teletravail=False)
        if sources.get("edf_carrieres"):
            toutes_offres += scan_edf()
        if sources.get("engie_carrieres"):
            toutes_offres += scan_engie()
        if sources.get("enedis_carrieres"):
            toutes_offres += scan_enedis()
        if sources.get("rte_carrieres"):
            toutes_offres += scan_rte()
        if sources.get("france_travail"):
            toutes_offres += scan_france_travail(kws_alt, ["Paris", "Île-de-France"])
        if sources.get("indeed"):
            toutes_offres += scan_indeed(kws_alt, ["Paris", "Île-de-France"])

    # Filtrage anti-arnaques
    avant = len(toutes_offres)
    toutes_offres = [o for o in toutes_offres if not est_arnaque(o)]
    apres = len(toutes_offres)
    if avant != apres:
        logger.info(f"Anti-arnaque: {avant - apres} offres filtrées")

    # Suppression des doublons par lien
    vu = set()
    uniques = []
    for o in toutes_offres:
        lien = o.get("lien", "")
        if lien and lien not in vu:
            vu.add(lien)
            uniques.append(o)
        elif not lien:
            # Pas de lien = on garde quand même si titre+entreprise unique
            cle = o.get("titre", "") + "|" + o.get("entreprise", "")
            if cle not in vu:
                vu.add(cle)
                uniques.append(o)

    logger.info(f"=== Scan terminé : {len(uniques)} offres valides (sans doublons) ===")
    return uniques
