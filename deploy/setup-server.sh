#!/usr/bin/env bash
# Однократная настройка существующего Ubuntu VDS с Nginx и Certbot.
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo 'Run as root' >&2; exit 1; }
[[ $# -eq 2 ]] || { echo 'Usage: setup-server.sh PUBLIC_KEY BUILD_DIRECTORY' >&2; exit 1; }
deploy_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
public_key=$(realpath -- "$1")
build_dir=$(realpath -- "$2")
deploy_user=mkulikov-web-deploy
deploy_home=/var/lib/mkulikov-web-deploy
site_root=/var/www/mkulikov
nginx_config=/etc/nginx/sites-available/mkulikov

for program in nginx certbot python3 curl ssh-keygen useradd; do
  command -v "$program" > /dev/null
done
test -s "$build_dir/index.html"
ssh-keygen -l -f "$public_key" > /dev/null
[[ $(wc -l < "$public_key") -eq 1 ]] || { echo 'Expected one public key' >&2; exit 1; }
[[ $(cat "$public_key") =~ ^ssh-ed25519\ [A-Za-z0-9+/=]+(\ .*)?$ ]] || {
  echo 'Expected an Ed25519 public key' >&2; exit 1;
}
if getent passwd "$deploy_user" > /dev/null || [[ -e $site_root || -e $nginx_config || -e $deploy_home || -e /usr/local/bin/deploy-mkulikov-web || -L /etc/nginx/sites-enabled/mkulikov ]]; then
  echo 'Existing installation found; refusing to overwrite it' >&2
  exit 1
fi
nginx -t

useradd --system --user-group --home-dir "$deploy_home" --shell /bin/bash "$deploy_user"
install -d -o root -g root -m 0755 "$deploy_home"
install -d -o root -g "$deploy_user" -m 0750 "$deploy_home/.ssh"
printf 'restrict,command="/usr/local/bin/deploy-mkulikov-web" %s\n' "$(cat "$public_key")" > "$deploy_home/.ssh/authorized_keys"
chown root:"$deploy_user" "$deploy_home/.ssh/authorized_keys"
chmod 0640 "$deploy_home/.ssh/authorized_keys"
install -o root -g root -m 0755 "$deploy_dir/server/deploy-site.py" /usr/local/bin/deploy-mkulikov-web

install -d -o "$deploy_user" -g "$deploy_user" -m 0755 "$site_root" "$site_root/releases"
bootstrap="bootstrap-$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 0755 "$site_root/releases/$bootstrap"
cp -R -- "$build_dir/." "$site_root/releases/$bootstrap/"
chmod -R u=rwX,go=rX "$site_root/releases/$bootstrap"
chown -R "$deploy_user:$deploy_user" "$site_root/releases/$bootstrap"
ln -s "releases/$bootstrap" "$site_root/current"
chown -h "$deploy_user:$deploy_user" "$site_root/current"

install -d -o root -g root -m 0755 /var/www/letsencrypt /usr/local/share/mkulikov-web
install -o root -g root -m 0644 "$deploy_dir/nginx-https.conf" /usr/local/share/mkulikov-web/nginx-https.conf
install -o root -g root -m 0755 "$deploy_dir/enable-https.sh" /usr/local/bin/enable-mkulikov-https
install -o root -g root -m 0644 "$deploy_dir/nginx-http.conf" "$nginx_config"
ln -s "$nginx_config" /etc/nginx/sites-enabled/mkulikov
if ! nginx -t; then
  unlink /etc/nginx/sites-enabled/mkulikov
  echo 'New Nginx site disabled; existing running configuration is unchanged' >&2
  exit 1
fi
systemctl reload nginx
echo "HTTP site installed: $site_root/current -> releases/$bootstrap"
echo 'After DNS points to 136.234.5.71, run: enable-mkulikov-https'
