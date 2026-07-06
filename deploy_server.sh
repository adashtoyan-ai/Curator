#!/usr/bin/env bash
# Деплой демо КУРАТОР на сервер (Ubuntu/Debian) по SSH. Запускать на своём Mac из папки проекта:
#   cd "~/Мой диск/ПРОЕКТЫ/Куратор"
#   bash deploy_server.sh root@153.80.184.228
#
# После успеха демо будет доступно по адресу:  http://153.80.184.228:8000
# Требуется: SSH-доступ к серверу (ключ или пароль), на сервере — Python 3.
set -e

TARGET="${1:-root@153.80.184.228}"          # ssh user@host
HOST="${TARGET#*@}"
APP_DIR="/opt/curator-demo"
PORT="8000"

echo "==> 1/4 Копирую демо на сервер ($TARGET:$APP_DIR)"
ssh "$TARGET" "mkdir -p $APP_DIR"
# rsync без базы данных и кэша
rsync -az --delete \
  --exclude 'curator.db*' --exclude '__pycache__' --exclude '.git' \
  ./curator-demo/ "$TARGET:$APP_DIR/"

echo "==> 2/4 Устанавливаю зависимости на сервере"
ssh "$TARGET" "bash -s" <<EOF
set -e
(command -v python3 >/dev/null) || { apt-get update && apt-get install -y python3 python3-pip; }
(command -v pip3 >/dev/null)   || apt-get install -y python3-pip
pip3 install --break-system-packages -q -r $APP_DIR/requirements.txt
EOF

echo "==> 3/4 Создаю systemd-сервис (автозапуск, рестарт)"
ssh "$TARGET" "bash -s" <<EOF
set -e
cat > /etc/systemd/system/curator.service <<UNIT
[Unit]
Description=CURATOR demo
After=network.target

[Service]
WorkingDirectory=$APP_DIR
Environment=CURATOR_DB=$APP_DIR/curator.db
ExecStart=/usr/bin/env python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
Restart=always

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now curator
sleep 2
systemctl --no-pager --lines=5 status curator || true
EOF

echo "==> 4/4 Открываю порт $PORT (если есть ufw)"
ssh "$TARGET" "command -v ufw >/dev/null && ufw allow $PORT/tcp || true"

echo ""
echo "✅ Готово. Демо доступно по адресу:"
echo "   http://$HOST:$PORT"
echo ""
echo "Управление на сервере:"
echo "   systemctl restart curator     # перезапуск"
echo "   journalctl -u curator -f      # логи"
