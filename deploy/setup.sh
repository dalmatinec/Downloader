#!/usr/bin/env bash
# Ставит nginx и выкладывает сайт. Запускать на сервере из папки репозитория:
#   sudo bash deploy/setup.sh
set -e
cd "$(dirname "$0")/.."

apt-get update -y
apt-get install -y nginx

mkdir -p /var/www/slavyanochka
cp -r site/. /var/www/slavyanochka/

rm -f /etc/nginx/sites-enabled/default
cp deploy/nginx.conf /etc/nginx/sites-available/slavyanochka
ln -sf /etc/nginx/sites-available/slavyanochka /etc/nginx/sites-enabled/slavyanochka

if command -v ufw >/dev/null && ufw status | grep -q active; then
  ufw allow 80/tcp
fi

nginx -t
systemctl restart nginx
systemctl enable nginx

IP=$(curl -s -4 ifconfig.me || hostname -I | awk '{print $1}')
echo
echo "Готово! Сайт открывается тут: http://$IP"
