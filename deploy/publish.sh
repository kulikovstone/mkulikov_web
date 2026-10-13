#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
release_id="${GITHUB_SHA:?}-${GITHUB_RUN_ID:?}-${GITHUB_RUN_ATTEMPT:?}"

[[ "$release_id" =~ ^[a-f0-9]{40}-[0-9]+-[0-9]+$ ]] || {
  echo 'Invalid release identifier' >&2
  exit 1
}
: "${DEPLOY_SSH_KEY:?Set the DEPLOY_SSH_KEY repository secret}"
: "${DEPLOY_HOST:?}"
: "${DEPLOY_USER:?}"
test -s "$project_dir/dist/index.html"

umask 077
ssh_dir=$(mktemp -d "${RUNNER_TEMP:-/tmp}/mkulikov-web-ssh.XXXXXX")
trap 'rm -rf -- "$ssh_dir"' EXIT
printf '%s\n' "$DEPLOY_SSH_KEY" | tr -d '\r' > "$ssh_dir/key"
unset DEPLOY_SSH_KEY
ssh-keygen -y -f "$ssh_dir/key" > /dev/null

ssh_options=(
  -F /dev/null
  -i "$ssh_dir/key"
  -o IdentitiesOnly=yes
  -o BatchMode=yes
  -o StrictHostKeyChecking=yes
  -o "UserKnownHostsFile=$project_dir/deploy/known_hosts"
  -o ConnectTimeout=15
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
)

# Только для ручной проверки с компьютера, где SSH иначе уходит через VPN.
if [[ -n "${DEPLOY_SSH_BIND_INTERFACE:-}" ]]; then
  ssh_options+=(-B "$DEPLOY_SSH_BIND_INTERFACE")
fi

# Сервер принимает только эту команду и архив собранного сайта на stdin.
tar -C "$project_dir/dist" -czf - . |
  ssh "${ssh_options[@]}" "$DEPLOY_USER@$DEPLOY_HOST" "deploy $release_id"
