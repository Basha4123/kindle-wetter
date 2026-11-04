#!/usr/bin/env sh

export WIFI_TEST_IP=${WIFI_TEST_IP:-1.1.1.1}

# Rund um die Uhr alle 10 Minuten aktualisieren. Das Wetterbild bleibt
# dazwischen dauerhaft stehen (E-Ink braucht dafür keinen Strom),
# der Bildschirmschoner ist abgeschaltet.
export REFRESH_SCHEDULE=${REFRESH_SCHEDULE:-"*/10 * * * *"}
export TIMEZONE=${TIMEZONE:-"Europe/Berlin"}

# Jede 3. Aktualisierung (also alle 30 Minuten) mit vollem Bildaufbau
# (kurzes Blinken), damit sich keine Geisterbilder ansammeln.
export FULL_DISPLAY_REFRESH_RATE=${FULL_DISPLAY_REFRESH_RATE:-3}

# Nachtbildschirm nur bei Pausen über 2 Stunden – kommt bei diesem
# Zeitplan nie vor, das Wetter bleibt also immer sichtbar.
export SLEEP_SCREEN_INTERVAL=7200

# Bild älter als 15 Minuten -> auf ein frisches warten (siehe fetch-dashboard.sh)
export MAX_ALTER=${MAX_ALTER:-900}

# Standort nur etwa einmal pro Stunde prüfen (spart Akku und Anfragen)
export STANDORT_INTERVALL=${STANDORT_INTERVALL:-3300}

export LOW_BATTERY_REPORTING=${LOW_BATTERY_REPORTING:-false}
export LOW_BATTERY_THRESHOLD_PERCENT=10
