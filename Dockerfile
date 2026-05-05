# Dockerfile — JobCopilot Étudiant ISE
FROM python:3.11-slim

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends     gcc     libxml2-dev     libxslt1-dev     && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY . .

# Crée les dossiers nécessaires
RUN mkdir -p data logs profiles web

# Copie les fichiers profils
COPY profiles/ profiles/
COPY web/ web/

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Port
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/stats || exit 1

# Commande par défaut : lance le serveur web
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "server:app"]
