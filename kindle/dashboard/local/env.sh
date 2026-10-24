#!/usr/bin/env sh

export WIFI_TEST_IP=${WIFI_TEST_IP:-1.1.1.1}

# Aktualisierung alle 30 Minuten von 6 bis 22 Uhr (Minute 10 und 40,
# weil GitHub das Bild meist ein paar Minuten nach :00/:30 fertig hat).
# Nachts schläft der Kindle und zeigt einen Nachtbildschirm – das spart Akku.
export REFRESH_SCHEDULE=${REFRESH_SCHEDULE:-"10,40 6-22 * * *"}
export TIMEZONE=${TIMEZONE:-"Europe/Berlin"}

# Jede 2. Aktualisierung mit vollem Bildaufbau (kurzes Blinken), damit
# sich keine Geisterbilder auf dem E-Ink-Display ansammeln.
export FULL_DISPLAY_REFRESH_RATE=${FULL_DISPLAY_REFRESH_RATE:-2}

# Ab dieser Schlafdauer (Sekunden) wird der Nachtbildschirm gezeigt.
export SLEEP_SCREEN_INTERVAL=3600

export LOW_BATTERY_REPORTING=${LOW_BATTERY_REPORTING:-false}
export LOW_BATTERY_THRESHOLD_PERCENT=10
