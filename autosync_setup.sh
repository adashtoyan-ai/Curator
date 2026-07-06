#!/usr/bin/env bash
# Включает АВТО-выгрузку проекта КУРАТОР на GitHub через launchd (штатный планировщик macOS).
# Каждые 3 минуты проверяет папку и, если есть изменения, коммитит и пушит (через sync.sh).
# Запуск один раз на Mac из папки проекта:
#   cd "~/Мой диск/ПРОЕКТЫ/Куратор"
#   bash autosync_setup.sh
#
# Выключить позже:  bash autosync_setup.sh off
set -e

LABEL="com.curator.autosync"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$PROJECT_DIR/.autosync.log"

if [ "$1" = "off" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "🛑 Авто-синхронизация выключена."
  exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${PROJECT_DIR}/sync.sh</string>
  </array>
  <key>StartInterval</key><integer>180</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>${LOG}</string>
  <key>StandardErrorPath</key><string>${LOG}</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "✅ Авто-синхронизация включена (каждые 3 минуты)."
echo "   Лог: $LOG"
echo "   Выключить: bash autosync_setup.sh off"
