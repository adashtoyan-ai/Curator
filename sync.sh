#!/usr/bin/env bash
# Авто-синхронизация: (1) выложить изменения на GitHub, (2) при изменении демо — редеплой на сервер.
# Работает из любого места. Запускается вручную (bash sync.sh) или автоматически через launchd.
set -e
cd "$(dirname "$0")"

SERVER="root@153.80.184.228"
MSG="${1:-Автосинхронизация $(date '+%Y-%m-%d %H:%M')}"

# --- 1. GitHub ---
git add -A
if ! git diff --cached --quiet; then
  git commit -q -m "$MSG"
  git push -q
  echo "✅ GitHub: $MSG"
fi

# --- 2. Авто-редеплой демо при изменении кода демо ---
HASH=$(find curator-demo -type f -not -name 'curator.db*' -not -path '*/__pycache__/*' \
        2>/dev/null | sort | xargs cat 2>/dev/null | shasum | cut -d' ' -f1)
if [ "$HASH" != "$(cat .last_deploy_hash 2>/dev/null)" ]; then
  echo "↻ Изменения демо обнаружены — редеплой на $SERVER ..."
  if SSH_OPTS='-o BatchMode=yes -o ConnectTimeout=10' bash deploy_server.sh "$SERVER" >/tmp/curator_deploy.log 2>&1; then
    echo "$HASH" > .last_deploy_hash
    echo "✅ Редеплой выполнен: http://153.80.184.228:8090"
  else
    echo "⚠ Редеплой не удался (SSH по ключу к серверу?). Лог: /tmp/curator_deploy.log"
  fi
fi
