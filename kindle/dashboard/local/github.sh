#!/usr/bin/env sh
# Gemeinsame Helfer für den Zugriff auf GitHub (wird per "." eingebunden).
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"
XH="$LOCAL_DIR/../xh"
. "$LOCAL_DIR/github.conf"

BENUTZER=$(echo "${GITHUB_REPO%%/*}" | tr 'A-Z' 'a-z')
SEITE="https://$BENUTZER.github.io/${GITHUB_REPO#*/}"

api() { # api METHODE PFAD [feld=wert ...]
  methode=$1; pfad=$2; shift 2
  "$XH" -q --check-status --ignore-stdin --timeout 20 "$methode" "https://api.github.com/repos/$GITHUB_REPO$pfad" \
    "Authorization:Bearer $GITHUB_TOKEN" Accept:application/vnd.github+json User-Agent:kindle-wetter "$@"
}

bild_anfordern() { # startet auf GitHub die Erzeugung eines neuen Wetterbilds
  api POST "/actions/workflows/wetter.yml/dispatches" ref=main >/dev/null
}
