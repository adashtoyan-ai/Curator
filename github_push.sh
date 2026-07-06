#!/usr/bin/env bash
# Выкладка проекта КУРАТОР на GitHub через SSH.
# Запускать на своём Mac из папки проекта:
#   cd "~/Мой диск/ПРОЕКТЫ/Куратор"
#   bash github_push.sh <ТВОЙ_GITHUB_ЛОГИН>
set -e

GH_USER="${1:?Укажи логин: bash github_push.sh <твой_github_логин>}"
REPO_NAME="curator"
VISIBILITY="private"           # или public
SSH_URL="git@github.com:${GH_USER}/${REPO_NAME}.git"

echo "==> Проверка SSH-доступа к GitHub"
if ! ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
  echo "⚠  SSH-ключ не настроен. Настрой один раз:"
  echo "   ssh-keygen -t ed25519 -C \"$USER@mac\"        # Enter на все вопросы"
  echo "   pbcopy < ~/.ssh/id_ed25519.pub                # ключ скопирован в буфер"
  echo "   → вставь его на https://github.com/settings/ssh/new и сохрани"
  echo "   затем запусти этот скрипт снова."
  exit 1
fi

echo "==> Чистим возможный битый .git (создан в облаке)"
rm -rf .git

echo "==> Инициализация репозитория и коммит"
git init -q
git add -A
git commit -q -m "КУРАТОР MVP v1.2: спецификация + рабочий демо-прототип"
git branch -M main

if command -v gh >/dev/null 2>&1; then
  echo "==> Создаём репозиторий на GitHub через gh (SSH)"
  gh repo create "$REPO_NAME" --"$VISIBILITY" --source=. --remote=origin --push
  git remote set-url origin "$SSH_URL"
  echo "✅ Готово. Репозиторий: https://github.com/${GH_USER}/${REPO_NAME}"
else
  echo "==> gh не найден. Создай ПУСТОЙ репозиторий '$REPO_NAME' на https://github.com/new (без README),"
  echo "    затем этот скрипт добавит SSH-remote и запушит."
  read -p "Нажми Enter, когда пустой репозиторий создан..." _
  git remote add origin "$SSH_URL" 2>/dev/null || git remote set-url origin "$SSH_URL"
  git push -u origin main
  echo "✅ Готово. Репозиторий: https://github.com/${GH_USER}/${REPO_NAME}"
fi
