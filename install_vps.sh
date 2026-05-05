#!/bin/bash
# install_vps.sh — Installation automatique sur VPS Ubuntu 22.04+
# Usage : chmod +x install_vps.sh && ./install_vps.sh

set -e

APP_DIR="/opt/jobcopilot"
DOMAIN="${1:-ton-domaine.com}"

echo "🎓 JobCopilot — Installation VPS"
echo "================================"

# 1. Mise à jour
sudo apt update && sudo apt upgrade -y

# 2. Python
sudo apt install -y python3 python3-pip python3-venv python3-dev

# 3. Nginx + Certbot
sudo apt install -y nginx certbot python3-certbot-nginx

# 4. Création dossier
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# 5. Copie des fichiers (tu dois copier manuellement ou via git)
echo "📁 Copie les fichiers du projet dans $APP_DIR"
echo "   → server.py, main.py, scanner.py, ai_engine.py, database.py"
echo "   → requirements.txt, profiles/, web/"
read -p "Appuie sur Entrée quand c'est fait..."

# 6. Virtualenv
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 7. Création des dossiers
mkdir -p data logs profiles web

# 8. Configuration clé API
echo ""
echo "🔑 Configure ta clé API Gemini"
read -p "Colle ta clé API Gemini : " API_KEY
echo "GEMINI_API_KEY=$API_KEY" > .env

# 9. Systemd services
sudo tee /etc/systemd/system/jobcopilot.service > /dev/null <<EOF
[Unit]
Description=JobCopilot Web Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment=GEMINI_API_KEY=$API_KEY
Environment=FLASK_ENV=production
ExecStart=$APP_DIR/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 server:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/jobcopilot-scanner.service > /dev/null <<EOF
[Unit]
Description=JobCopilot Scanner
After=network.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$APP_DIR
Environment=GEMINI_API_KEY=$API_KEY
ExecStart=$APP_DIR/venv/bin/python main.py --scan-only
EOF

sudo tee /etc/systemd/system/jobcopilot-scanner.timer > /dev/null <<EOF
[Unit]
Description=Run JobCopilot scanner every 2 hours

[Timer]
OnCalendar=*:0/2
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jobcopilot
sudo systemctl enable jobcopilot-scanner.timer

# 10. Nginx
sudo tee /etc/nginx/sites-available/jobcopilot > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/jobcopilot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 11. SSL
echo "🔒 Configuration HTTPS avec Let's Encrypt..."
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

# 12. Démarrage
sudo systemctl start jobcopilot
sudo systemctl start jobcopilot-scanner.timer

echo ""
echo "✅ Installation terminée !"
echo "🌐 Ton site : https://$DOMAIN"
echo "📊 API : https://$DOMAIN/api/stats"
echo ""
echo "Commandes utiles :"
echo "  sudo systemctl status jobcopilot"
echo "  sudo systemctl status jobcopilot-scanner.timer"
echo "  sudo journalctl -u jobcopilot -f"
echo "  sudo systemctl restart jobcopilot"
