#!/usr/bin/env sh
# Prüft den Standort, sorgt für ein frisches Wetterbild und lädt es nach "$1".
DIR="$(cd "$(dirname "$0")" && pwd)"
. "$DIR/github.sh"

# GitHub braucht etwa eine Minute, bis ein angefordertes Bild online ist.
WARTEZEIT=${WARTEZEIT:-75}
# Älter als das (Sekunden) gilt das Bild als veraltet.
MAX_ALTER=${MAX_ALTER:-2400}

sh "$DIR/standort.sh"
if [ $? -eq 10 ]; then
  echo "Neuer Ort – warte auf das passende Bild"
  sleep "$WARTEZEIT"
else
  stand=$("$XH" --ignore-stdin --timeout 20 GET "$SEITE/stand.txt?t=$(date +%s)" 2>/dev/null | tr -dc '0-9')
  alter=$(( $(date +%s) - ${stand:-0} ))
  if [ "$alter" -gt "$MAX_ALTER" ]; then
    echo "Bild ist ${alter}s alt – fordere ein neues an"
    bild_anfordern && sleep "$WARTEZEIT"
  else
    # Aktuell genug: zeigen, und fürs nächste Aufwachen schon ein neues bestellen.
    bild_anfordern
  fi
fi

"$XH" -d -q --ignore-stdin --timeout 30 -o "$1" get "$SEITE/wetter.png?t=$(date +%s)"
