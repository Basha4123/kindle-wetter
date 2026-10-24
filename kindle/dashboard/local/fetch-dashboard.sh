#!/usr/bin/env sh
# Prüft den Standort und lädt das aktuelle Wetterbild nach "$1".
DIR="$(cd "$(dirname "$0")" && pwd)"
. "$DIR/github.conf"

"$DIR/standort.sh"
if [ $? -eq 10 ]; then
  # Neuer Ort: GitHub braucht etwa eine Minute für das neue Bild.
  sleep 90
fi

BENUTZER=${GITHUB_REPO%%/*}
URL="https://$(echo "$BENUTZER" | tr 'A-Z' 'a-z').github.io/${GITHUB_REPO#*/}/wetter.png"
"$DIR/../xh" -d -q --ignore-stdin -o "$1" get "$URL"
