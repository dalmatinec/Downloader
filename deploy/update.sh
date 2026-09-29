#!/usr/bin/env bash
# Обновить сайт после изменений на GitHub:
#   sudo bash deploy/update.sh
set -e
cd "$(dirname "$0")/.."

git pull
rsync -a --delete site/ /var/www/slavyanochka/
if [ -d /etc/letsencrypt/live ] && grep -q "listen 443" /etc/nginx/sites-available/slavyanochka; then
  IP=$(grep -m1 -o "live/[0-9.]*" /etc/nginx/sites-available/slavyanochka | cut -d/ -f2)
  sed "s/SERVER_IP/$IP/g" deploy/nginx-https.conf > /etc/nginx/sites-available/slavyanochka
else
  cp deploy/nginx.conf /etc/nginx/sites-available/slavyanochka
fi
nginx -t && systemctl reload nginx

echo "Сайт обновлён"
