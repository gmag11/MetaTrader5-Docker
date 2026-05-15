#!/bin/bash
# Deploy CopyTrader Dashboard to Server
# Usage: ./deploy.sh [user@server]

SERVER=${1:-"root@copy.tradeoptix.app"}

echo "Building dashboard..."
npm run build

echo "Deploying to $SERVER..."

# Create directory on server
ssh $SERVER "mkdir -p /opt/copytrader/dashboard"

# Copy dist folder
scp -r dist/* $SERVER:/opt/copytrader/dashboard/

echo "Updating Nginx configuration..."
ssh $SERVER 'cat > /etc/nginx/sites-available/copytrader << EOF
server {
    listen 80;
    server_name copy.tradeoptix.app;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name copy.tradeoptix.app;

    ssl_certificate /etc/letsencrypt/live/copy.tradeoptix.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/copy.tradeoptix.app/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Dashboard (static files)
    location / {
        root /opt/copytrader/dashboard;
        try_files \$uri \$uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://localhost:8180/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF'

echo "Enabling site and reloading Nginx..."
ssh $SERVER "ln -sf /etc/nginx/sites-available/copytrader /etc/nginx/sites-enabled/ && nginx -t && systemctl reload nginx"

echo "Dashboard deployed successfully!"
echo "Visit: https://copy.tradeoptix.app"
