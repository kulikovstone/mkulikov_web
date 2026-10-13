#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run as root' >&2; exit 1; }
test -s /var/www/mkulikov/current/index.html
test -L /etc/nginx/sites-enabled/mkulikov

# Не запрашиваем сертификат, пока DNS ещё ведёт на прежний хостинг.
python3 - <<'PY'
import socket
records = socket.getaddrinfo('mkulikov.com', 80)
addresses = {item[4][0] for item in records if item[0] == socket.AF_INET}
if addresses != {'136.234.5.71'}:
    raise SystemExit(f'DNS is not ready: {sorted(addresses)}')
ipv6 = {item[4][0] for item in records if item[0] == socket.AF_INET6}
if ipv6:
    raise SystemExit(f'Check the domain AAAA records before issuing HTTPS: {sorted(ipv6)}')
PY

# Используем существующий ACME-аккаунт этого сервера, сертификат выпускаем отдельный.
account=$(sed -n 's/^account = //p' /etc/letsencrypt/renewal/curators.mkulikov.com.conf)
[[ $account =~ ^[a-f0-9]+$ ]] || { echo 'Existing ACME account not found' >&2; exit 1; }
certbot certonly --non-interactive --webroot --webroot-path /var/www/letsencrypt \
  --account "$account" --cert-name mkulikov.com -d mkulikov.com \
  --deploy-hook 'systemctl reload nginx'

backup="/etc/nginx/sites-available/mkulikov.before-https-$(date -u +%Y%m%dT%H%M%SZ)"
cp -p /etc/nginx/sites-available/mkulikov "$backup"
install -o root -g root -m 0644 /usr/local/share/mkulikov-web/nginx-https.conf /etc/nginx/sites-available/mkulikov
if ! nginx -t; then
  cp -p "$backup" /etc/nginx/sites-available/mkulikov
  echo 'Previous Nginx configuration restored' >&2
  exit 1
fi
systemctl reload nginx
systemctl enable --now certbot.timer
curl --fail --silent --show-error --retry 5 --retry-connrefused --max-time 15 \
  --resolve mkulikov.com:443:127.0.0.1 https://mkulikov.com/ > /dev/null
echo 'HTTPS enabled: https://mkulikov.com/'
