#!/usr/bin/env bash
# Деплой демо КУРАТОР на сервер (Ubuntu/Debian) по SSH. Запускать на своём Mac из папки проекта:
#   cd "~/Мой диск/ПРОЕКТЫ/Куратор"
#   bash deploy_server.sh root@153.80.184.228
#
# После успеха демо доступно по адресу:  http://153.80.184.228:8000
# Требуется: SSH-доступ к серверу, на сервере — Python 3. Ставится в venv (без системного pip).
set -e

TARGET="${1:-root@153.80.184.228}"          # ssh user@host
HOST="${TARGET#*@}"
APP_DIR="/opt/curator-demo"
PORT="8000"
SSH="ssh ${SSH_OPTS:-}"                       # SSH_OPTS='-o BatchMode=yes' для авто-режима

echo "==> 1/4 Копирую демо на сервер ($TARGET:$APP_DIR)"
$SSH "$TARGET" "mkdir -p $APP_DIR"
rsync -az --delete -e "$SSH" \
  --exclude 'curator.db*' --exclude '__pycache__' --exclude '.git' \
  ./curator-demo/ "$TARGET:$APP_DIR/"

echo "==> 2/4 Ставлю зависимости в виртуальное окружение (venv)"
$SSH "$TARGET" "bash -s" <<EOF
set -e
export DEBIAN_FRONTEND=noninteractive
command -v python3 >/dev/null || { apt-get update -qq && apt-get install -y -qq python3; }
# ставим venv-пакет под ТОЧНУЮ версию Python (нужен ensurepip)
PYV=\$(python3 -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')
apt-get update -qq
apt-get install -y -qq "python\${PYV}-venv" python3-venv || apt-get install -y -qq python3-venv
rm -rf $APP_DIR/venv
python3 -m venv $APP_DIR/venv
$APP_DIR/venv/bin/pip install -q --upgrade pip
$APP_DIR/venv/bin/pip install -q -r $APP_DIR/requirements.txt
EOF

echo "==> 3/4 Создаю systemd-сервис (автозапуск, рестарт)"
$SSH "$TARGET" "bash -s" <<EOF
set -e
cat > /etc/systemd/system/curator.service <<UNIT
[Unit]
Description=CURATOR demo
After=network.target

[Service]
WorkingDirectory=$APP_DIR
Environment=CURATOR_DB=$APP_DIR/curator.db
ExecStart=$APP_DIR/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
Restart=always

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now curator
sleep 2
systemctl --no-pager --lines=8 status curator || true
EOF

echo "==> 4/4 Открываю порт $PORT (если есть ufw)"
$SSH "$TARGET" "command -v ufw >/dev/null && ufw allow $PORT/tcp >/dev/null 2>&1 || true"

echo ""
echo "✅ Готово. Демо доступно по адресу:"
echo "   http://$HOST:$PORT"
echo ""
echo "Если не открывается — проверь, что порт $PORT разрешён в панели хостера (внешний файрвол)."
echo "Управление на сервере:  systemctl restart curator | journalctl -u curator -f"
