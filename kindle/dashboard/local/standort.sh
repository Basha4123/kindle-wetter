#!/usr/bin/env sh
# Ermittelt den Standort des Kindle und meldet ihn an GitHub, wenn er sich geändert hat.
#  1. WLAN-Netze in der Nähe -> BeaconDB (freie, offene Standortdatenbank)
#  2. Fallback: Standort der Internetverbindung (IP-Adresse)
# Rückgabe: 0 = Standort unverändert, 10 = neuer Standort gemeldet, sonst Fehler.

DIR="$(cd "$(dirname "$0")" && pwd)"
XH="$DIR/../xh"
STATE="$DIR/state/standort"
. "$DIR/github.conf"

# Ab dieser Entfernung (km) gilt der Standort als geändert
SCHWELLE_KM=${SCHWELLE_KM:-5}

zahl() { # erste Zahl hinter "$1": aus JSON auf stdin
  sed -n "s/.*\"$1\"[ ]*:[ ]*\(-\{0,1\}[0-9][0-9.]*\).*/\1/p" | head -n 1
}

wlan_standort() {
  command -v wpa_cli >/dev/null 2>&1 || return 1
  wpa_cli -i wlan0 scan >/dev/null 2>&1
  sleep 4
  netze=$(wpa_cli -i wlan0 scan_results 2>/dev/null |
    awk -F'\t' 'NR > 1 && $1 ~ /^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$/ && $5 !~ /_nomap$/ {
      printf "%s{\"macAddress\":\"%s\",\"signalStrength\":%d}", (n++ ? "," : ""), $1, $3 }')
  [ -n "$netze" ] || return 1
  antwort=$(echo "{\"considerIp\":false,\"wifiAccessPoints\":[$netze]}" |
    "$XH" --check-status --timeout 20 POST https://api.beacondb.net/v1/geolocate \
      Content-Type:application/json User-Agent:kindle-wetter) || return 1
  LAT=$(echo "$antwort" | zahl lat)
  LON=$(echo "$antwort" | zahl lng)
  QUELLE=wlan
  [ -n "$LAT" ] && [ -n "$LON" ]
}

ip_standort() {
  antwort=$("$XH" --check-status --ignore-stdin --timeout 20 GET https://ipinfo.io/json) || return 1
  loc=$(echo "$antwort" | sed -n 's/.*"loc"[ ]*:[ ]*"\([^"]*\)".*/\1/p' | head -n 1)
  LAT=${loc%,*}
  LON=${loc#*,}
  QUELLE=ip
  [ -n "$loc" ]
}

wlan_standort || ip_standort || { echo "Standort nicht ermittelbar"; exit 1; }

# Auf ~1 km runden (2 Nachkommastellen) – genauer braucht das Wetter nicht.
LAT=$(awk -v x="$LAT" 'BEGIN { printf "%.2f", x }')
LON=$(awk -v x="$LON" 'BEGIN { printf "%.2f", x }')
echo "Standort ($QUELLE): $LAT, $LON"

if [ -f "$STATE" ]; then
  read -r ALT_LAT ALT_LON <"$STATE"
  km=$(awk -v a="$ALT_LAT" -v b="$ALT_LON" -v c="$LAT" -v d="$LON" 'BEGIN {
    dy = (c - a) * 111; dx = (d - b) * 111 * cos(a * 3.14159 / 180)
    printf "%d", sqrt(dx * dx + dy * dy) }')
  if [ "$km" -lt "$SCHWELLE_KM" ]; then
    exit 0
  fi
  echo "Standort hat sich um ${km} km geändert"
fi

api() { # api METHODE PFAD [feld=wert ...]
  methode=$1; pfad=$2; shift 2
  "$XH" -q --check-status --ignore-stdin --timeout 20 "$methode" "https://api.github.com/repos/$GITHUB_REPO$pfad" \
    "Authorization:Bearer $GITHUB_TOKEN" Accept:application/vnd.github+json User-Agent:kindle-wetter "$@"
}

setze_variable() { # vorhandene Variable ändern, sonst anlegen
  api PATCH "/actions/variables/$1" "name=$1" "value=$2" >/dev/null 2>&1 ||
    api POST "/actions/variables" "name=$1" "value=$2" >/dev/null
}

setze_variable KW_LAT "$LAT" && setze_variable KW_LON "$LON" &&
  api POST "/actions/workflows/wetter.yml/dispatches" ref=main >/dev/null || {
    echo "GitHub-Aktualisierung fehlgeschlagen (Token prüfen)"
    exit 2
  }

mkdir -p "$(dirname "$STATE")"
echo "$LAT $LON" >"$STATE"
echo "Neuer Standort an GitHub gemeldet"
exit 10
