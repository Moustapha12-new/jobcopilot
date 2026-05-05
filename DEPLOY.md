# 🚀 Déploiement JobCopilot — Guide Complet

## 📋 Résumé des solutions

| Plateforme | Prix | Difficulté | Scan auto | URL perso |
|-----------|------|-----------|-----------|-----------|
| **Render.com** | Gratuit | ⭐ Facile | ✅ Cron job | ❌ URL Render |
| **Railway.app** | ~5€/mois | ⭐ Facile | ✅ | ❌ |
| **Fly.io** | Gratuit (crédits) | ⭐⭐ Moyen | ✅ | ✅ Domaine |
| **VPS (OVH/Scaleway)** | ~3-5€/mois | ⭐⭐⭐ Avancé | ✅ Cron/systemd | ✅ Domaine |
| **Heroku** | ~7€/mois | ⭐ Facile | ✅ | ❌ |

---

## 🥇 Option 1 : Render.com (RECOMMANDÉ — Gratuit)

### Étape 1 : Crée un compte
→ [render.com](https://render.com) (GitHub login)

### Étape 2 : Push ton code sur GitHub
```bash
git init
git add .
git commit -m "Initial JobCopilot"
git remote add origin https://github.com/TON_USER/jobcopilot.git
git push -u origin main
```

### Étape 3 : Déploie le Blueprint
1. Dashboard Render → **Blueprints** → **New Blueprint**
2. Connecte ton repo GitHub
3. Render lit automatiquement `render.yaml`
4. Configure `GEMINI_API_KEY` dans **Environment**

### Étape 4 : Terminé ! 🎉
- Web : `https://jobcopilot-web.onrender.com`
- Scan auto : toutes les 2h via le service cron

---

## 🥈 Option 2 : VPS Ubuntu (Contrôle total)

### Fournisseurs recommandés (étudiants)
- **OVH Cloud** : VPS Starter ~3,50€/mois
- **Scaleway** : Stardust ~4€/mois
- **Contabo** : VPS S ~4,50€/mois (8GB RAM !)

### Installation (1 commande)
```bash
# Sur ton VPS Ubuntu 22.04
wget https://raw.githubusercontent.com/TON_USER/jobcopilot/main/install_vps.sh
chmod +x install_vps.sh
./install_vps.sh ton-domaine.com
```

Ou manuellement :
```bash
# 1. Copie les fichiers
scp -r . root@TON_VPS:/opt/jobcopilot

# 2. SSH sur le VPS
ssh root@TON_VPS
cd /opt/jobcopilot

# 3. Lance l'install
./install_vps.sh
```

---

## 🥉 Option 3 : Railway.app (Simple, payant)

1. Crée compte sur [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo
3. Ajoute les variables d'env `GEMINI_API_KEY`
4. Railway détecte automatiquement `railway.json`

---

## 🔧 Configuration clé API

### IMPORTANT : Ne jamais commit `.env` !

**Render / Railway / Fly :** 
→ Dashboard → Environment Variables → `GEMINI_API_KEY=ta_clé`

**VPS :**
```bash
echo "GEMINI_API_KEY=AIzaSy..." > /opt/jobcopilot/.env
```

---

## 📁 Structure du projet déployé

```
jobcopilot/
├── server.py              ← API Flask (web service)
├── main.py                ← Pipeline (cron/scheduler)
├── scanner.py             ← Scraping offres
├── ai_engine.py           ← Scoring IA + CV/LM
├── database.py            ← SQLite
├── requirements.txt       ← Dépendances
├── render.yaml            ← Config Render (Option 1)
├── Dockerfile             ← Container (Option 2/3)
├── docker-compose.yml     ← Docker Compose (Option 2)
├── fly.toml               ← Config Fly.io (Option 3)
├── railway.json           ← Config Railway
├── install_vps.sh         ← Script install auto VPS
├── .github/workflows/      ← CI/CD GitHub Actions
│   └── deploy.yml
├── profiles/
│   ├── profile.yml        ← ⭐ TON PROFIL
│   └── cv.md              ← ⭐ TON CV
└── web/
    └── index.html         ← Dashboard
```

---

## 🔄 Fréquence des scans

| Plateforme | Fréquence | Config |
|-----------|-----------|--------|
| Render Cron | 2h | `schedule: "0 */2 * * *"` dans render.yaml |
| VPS systemd | 2h | `OnCalendar=*:0/2` dans .timer |
| VPS cron | 2h | `0 */2 * * * cd /opt/jobcopilot && python main.py --scan-only` |
| Daemon local | 7h30 | `python main.py --daemon` |

---

## 🛠️ Dépannage

### "Clé API manquante"
→ Vérifie la variable d'environnement `GEMINI_API_KEY`

### "Aucune offre trouvée"
→ Normal, les sites changent. Vérifie les logs : `docker logs jobcopilot-web`

### "Database locked"
→ SQLite ne supporte pas les accès simultanés. Sur VPS, utilise un seul process.

### "Memory exceeded" sur Render Free
→ Réduis `limit=50` à `limit=20` dans server.py ligne 158

---

## 💰 Coûts estimés (Gemini API)

- **Scan** : ~50 offres/jour
- **Scoring** : 50 appels API ≈ **0,02 €/jour** (Gemini Flash est quasi gratuit)
- **Génération CV/LM** : ~10-15 docs/jour ≈ **0,01 €/jour**
- **Total** : ~**1 €/mois** de crédits API

---

## 📞 Support

- Logs Render : Dashboard → Logs
- Logs VPS : `sudo journalctl -u jobcopilot -f`
- Logs Docker : `docker-compose logs -f`
