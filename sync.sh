#!/usr/bin/env bash
# Выложить ВСЕ текущие изменения на GitHub (репозиторий и remote уже настроены).
# Работает из любого места — сам переходит в папку проекта.
#   bash sync.sh                      # или: bash sync.sh "своё сообщение коммита"
set -e

cd "$(dirname "$0")"                   # папка, где лежит сам скрипт = папка проекта

MSG="${1:-Автосинхронизация $(date '+%Y-%m-%d %H:%M')}"

git add -A
if git diff --cached --quiet; then
  exit 0                              # нет изменений — тихо выходим
fi
git commit -q -m "$MSG"
git push -q
echo "✅ Выложено на GitHub: $MSG"
