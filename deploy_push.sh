#!/usr/bin/env bash
# Выкладка КУРАТОР на GitHub через DEPLOY KEY (ключ с доступом только к репозиторию curator).
# Запускать на Mac из папки проекта:
#   cd "~/Мой диск/ПРОЕКТЫ/Куратор"
#   bash deploy_push.sh <ТВОЙ_GITHUB_ЛОГИН>
set -e

GH_USER="${1:?Укажи логин: bash deploy_push.sh <твой_github_логин>}"
REPO_NAME="curator"
KEY=~/.ssh/curator_deploy
ALIAS="github-curator"                      # алиас хоста только для этого репо
SSH_URL="git@${ALIAS}:${GH_USER}/${REPO_NAME}.git"

# 1. Генерируем deploy-ключ (если ещё нет)
if [ ! -f "$KEY" ]; then
  echo "==> Создаю deploy-ключ $KEY"
  ssh-keygen -t ed25519 -f "$KEY" -N "" -C "curator-deploy" >/dev/null
fi

# 2. Прописываем алиас хоста в ~/.ssh/config (чтобы этот репо использовал именно этот ключ)
if ! grep -q "Host ${ALIAS}\b" ~/.ssh/config 2>/dev/null; then
  echo "==> Добавляю алиас в ~/.ssh/config"
  cat >> ~/.ssh/config <<EOF

Host ${ALIAS}
    HostName github.com
    User git
    IdentityFile ${KEY}
    IdentitiesOnly yes
EOF
fi

# 3. Показываем публичный ключ для добавления в Deploy keys репозитория
echo ""
echo "================= ПУБЛИЧНЫЙ DEPLOY-КЛЮЧ ================="
cat "${KEY}.pub"
echo "========================================================"
command -v pbcopy >/dev/null && pbcopy < "${KEY}.pub" && echo "(ключ также скопирован в буфер обмена)"
echo ""
echo "СЕЙЧАС СДЕЛАЙ ВРУЧНУЮ:"
echo "  1) Создай ПУСТОЙ репозиторий '$REPO_NAME' на https://github.com/new (без README)."
echo "  2) Открой: https://github.com/${GH_USER}/${REPO_NAME}/settings/keys/new"
echo "  3) Title: curator-deploy | вставь ключ выше | ПОСТАВЬ галочку 'Allow write access' | Add key"
read -p "Нажми Enter, когда добавил ключ и создал репозиторий..." _

# 4. Проверяем доступ
echo "==> Проверка доступа по deploy-ключу"
ssh -T "git@${ALIAS}" 2>&1 | grep -q "successfully authenticated" \
  && echo "✅ Доступ есть" || echo "(GitHub ответил — это нормально, продолжаем)"

# 5. Инициализация и пуш
echo "==> Чистим возможный битый .git из облака"
rm -rf .git
git init -q
git add -A
git commit -q -m "КУРАТОР MVP v1.2: спецификация + рабочий демо-прототип"
git branch -M main
git remote add origin "$SSH_URL" 2>/dev/null || git remote set-url origin "$SSH_URL"
git push -u origin main
echo ""
echo "✅ Готово: https://github.com/${GH_USER}/${REPO_NAME}"
