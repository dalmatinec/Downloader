#!/usr/bin/env bash
# Включает https по IP с бесплатным сертификатом Let's Encrypt.
# Сертификат живёт 6 дней и продлевается сам. Запускать после setup.sh:
#   bash deploy/https.sh
set -e
cd "$(dirname "$0")/.."

IP=$(curl -s -4 --max-time 5 ifconfig.me || hostname -I | awk '{print $1}')
echo "IP сервера: $IP"

# Нужен свежий certbot (5.4+), в apt он старый, поэтому ставим через snap
if ! command -v snap >/dev/null; then
  apt-get update -y && apt-get install -y snapd
fi
apt-get remove -y certbot >/dev/null 2>&1 || true
snap install core >/dev/null 2>&1 || true
snap install --classic certbot 2>/dev/null || snap refresh certbot
ln -sf /snap/bin/certbot /usr/bin/certbot
certbot --version

# Открываем 443 порт
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow 443/tcp
fi
iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || iptables -I INPUT -p tcp --dport 443 -j ACCEPT

certbot certonly --non-interactive --agree-tos --register-unsafely-without-email \
  --preferred-profile shortlived \
  --webroot --webroot-path /var/www/slavyanochka \
  --ip-address "$IP" \
  --deploy-hook "systemctl reload nginx"

sed "s/SERVER_IP/$IP/g" deploy/nginx-https.conf > /etc/nginx/sites-available/slavyanochka
nginx -t
systemctl reload nginx

echo
echo "Готово! Теперь сайт открывается тут: https://$IP"
