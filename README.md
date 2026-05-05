# 🎓 JobCopilot Étudiant ISE

Scanner automatique d'offres d'emploi avec matching IA et génération de CV/LM.  
Conçu pour les étudiants ingénieurs ISE en Île-de-France.

---

## 🚀 Installation rapide (5 minutes)

### Prérequis
- **Python 3.10+** — [python.org](https://python.org) (Windows : coche "Add to PATH")
- **Une clé API Claude** — [console.anthropic.com](https://console.anthropic.com) (gratuite au démarrage)

### Étapes

**1. Installe les dépendances**
```bash
pip install -r requirements.txt
```

**2. Configure ta clé API**

Crée un fichier `.env` dans le dossier `jobcopilot/` :
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
```

**3. Remplis ton profil**

Édite `profiles/profile.yml` avec tes informations :
- Nom, email, téléphone
- Localisation et préférences par type de poste
- Activates/désactives les 3 profils (terrain / remote / alternance)

**4. Mets à jour ton CV**

Édite `profiles/cv.md` avec ton vrai CV en markdown.

---

## 🖥️ Utilisation

### Windows
Double-clique sur `run.bat` → choisis une option dans le menu.

### Mac / Linux
```bash
chmod +x run.sh
./run.sh          # Pipeline complet
./run.sh dash     # Tableau de bord
./run.sh daemon   # Mode automatique
./run.sh scan     # Scan sans IA
```

### Directement Python
```bash
python main.py                    # Pipeline complet
python main.py --dashboard        # Tableau de bord interactif
python main.py --daemon           # Scan quotidien automatique (07:30)
python main.py --scan-only        # Scan sans IA (pas besoin de clé API)
python main.py --score-only       # Score les offres déjà en base
```

---

## ⚙️ Fonctionnement quotidien

1. **Scan** : le système récupère les nouvelles offres sur StudentJob, Jooble, Hellowork, et les pages carrières EDF/Engie/Enedis/RTE
2. **Filtre anti-arnaques** : offres douteuses supprimées automatiquement
3. **Scoring IA** : Claude analyse chaque offre vs ton profil sur 5 dimensions, donne un score /10 et une recommandation (POSTULER / PEUT-ETRE / IGNORER)
4. **Génération** : pour les offres POSTULER et PEUT-ETRE, génère un CV adapté ATS + une lettre de motivation personnalisée
5. **Dashboard** : tu consultes les résultats, lis les CV/LM générés, marques les candidatures envoyées

---

## 📂 Structure des fichiers

```
jobcopilot/
├── main.py            ← Point d'entrée principal
├── scanner.py         ← Scraping des job boards
├── ai_engine.py       ← Scoring et génération IA
├── database.py        ← Base de données SQLite
├── dashboard.py       ← Interface terminal interactive
├── profiles/
│   ├── profile.yml    ← ⭐ TON PROFIL (à éditer)
│   └── cv.md          ← ⭐ TON CV (à éditer)
├── data/
│   └── jobcopilot.db  ← Base de données (créée automatiquement)
├── logs/              ← Logs quotidiens
├── .env               ← ⭐ Ta clé API (à créer)
├── run.sh             ← Lanceur Mac/Linux
├── run.bat            ← Lanceur Windows
└── requirements.txt   ← Dépendances Python
```

---

## 📊 Le scoring IA

Chaque offre est notée sur 10 selon 5 dimensions :

| Dimension | Poids |
|-----------|-------|
| Match compétences | 30% |
| Lieu / transport | 20% |
| Intérêt personnel | 20% |
| Compatibilité horaires | 15% |
| Salaire | 15% |

**Recommandations :**
- 🟢 **POSTULER** (≥ 7/10) → CV + LM générés, offre prioritaire
- 🟡 **PEUT-ETRE** (5–7/10) → CV + LM générés, à vérifier manuellement
- 🔴 **IGNORER** (< 5/10) → Archivée mais pas mise en avant

---

## 🔄 Automatisation complète (optionnel)

### Mac/Linux — via cron
```bash
chmod +x setup_cron.sh
./setup_cron.sh
```
Scan automatique chaque matin à 07:30.

### Toutes plateformes — mode daemon
```bash
python main.py --daemon
```
Laisse ce terminal ouvert (ou lance au démarrage système).

---

## 💡 Conseils

- **Budget API** : le scoring utilise Claude Haiku (très économique). 50 offres/jour ≈ 0,05–0,10 € par scan.
- **Première utilisation** : lance `python main.py --scan-only` pour tester sans clé API.
- **Profils** : active/désactive les 3 profils dans `profile.yml` selon ta situation du moment.
- **Sources** : tu peux ajouter des sources dans `scanner.py` en suivant le même pattern.

---

## ❓ Problèmes courants

**"Clé API manquante"**  
→ Crée le fichier `.env` avec `ANTHROPIC_API_KEY=sk-ant-...`

**"Aucune offre trouvée"**  
→ Les sites changent parfois leur HTML. Vérifie la connexion internet et les logs dans `logs/`.

**"ModuleNotFoundError"**  
→ Lance `pip install -r requirements.txt`

**Offres vides ou titre manquant**  
→ Normal pour certains sites avec protection anti-bot. Les grandes pages carrières (EDF, Engie) sont plus stables.
