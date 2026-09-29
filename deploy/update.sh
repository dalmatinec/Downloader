#!/usr/bin/env bash
# Обновить сайт после изменений на GitHub:
#   sudo bash deploy/update.sh
set -e
cd "$(dirname "$0")/.."

git pull
rsync -a --delete site/ /var/www/slavyanochka/
cp deploy/nginx.conf /etc/nginx/sites-available/slavyanochka
nginx -t && systemctl reload nginx

echo "Сайт обновлён"
