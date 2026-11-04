#!/usr/bin/env sh
# Basierend auf kindle-dash von Pascal Widdershoven (MIT, siehe LICENSE-kindle-dash),
# angepasst für Kindle Paperwhite (anderer RTC-Weckmechanismus).
DEBUG=${DEBUG:-false}
[ "$DEBUG" = true ] && set -x

DIR="$(cd "$(dirname "$0")" && pwd)"
DASH_PNG="$DIR/dash.png"
FETCH_DASHBOARD_CMD="$DIR/local/fetch-dashboard.sh"
LOW_BATTERY_CMD="$DIR/local/low-battery.sh"
BIN_DIR="$DIR"
STANDARD_WARTEZEIT=600
erster_lauf=true
zeile=3

REFRESH_SCHEDULE=${REFRESH_SCHEDULE:-"2,32 8-17 * * MON-FRI"}
FULL_DISPLAY_REFRESH_RATE=${FULL_DISPLAY_REFRESH_RATE:-0}
SLEEP_SCREEN_INTERVAL=${SLEEP_SCREEN_INTERVAL:-3600}
RTC=/sys/devices/platform/mxc_rtc.0/wakeup_enable

LOW_BATTERY_REPORTING=${LOW_BATTERY_REPORTING:-false}
LOW_BATTERY_THRESHOLD_PERCENT=${LOW_BATTERY_THRESHOLD_PERCENT:-10}

num_refresh=0

# Meldung ins Protokoll und – beim Start oder bei Fehlern – aufs Display
zeige() {
  echo "$(date '+%H:%M:%S') $*"
  /usr/sbin/eips 2 "$zeile" "$*" >/dev/null 2>&1
  zeile=$((zeile + 2))
}

# Programme direkt von /mnt/us starten; falls das nicht erlaubt ist,
# nach /var/tmp kopieren und von dort ausführen.
pruefe_programme() {
  if "$BIN_DIR/next-wakeup" --schedule="$REFRESH_SCHEDULE" --timezone="$TIMEZONE" >/dev/null 2>&1; then
    return 0
  fi
  echo "Programme auf /mnt/us nicht ausführbar, kopiere nach /var/tmp"
  BIN_DIR=/var/tmp/kindle-wetter
  mkdir -p "$BIN_DIR"
  cp "$DIR/xh" "$DIR/next-wakeup" "$BIN_DIR/" && chmod +x "$BIN_DIR/xh" "$BIN_DIR/next-wakeup"
  if ! "$BIN_DIR/next-wakeup" --schedule="$REFRESH_SCHEDULE" --timezone="$TIMEZONE" >/dev/null 2>&1; then
    zeige "FEHLER: Programme nicht ausfuehrbar"
    zeige "Bitte dashboard/logs/dash.log schicken"
    return 1
  fi
}

init() {
  if [ -z "$TIMEZONE" ] || [ -z "$REFRESH_SCHEDULE" ]; then
    echo "Missing required configuration."
    echo "Timezone: ${TIMEZONE:-(not set)}."
    echo "Schedule: ${REFRESH_SCHEDULE:-(not set)}."
    exit 1
  fi

  echo "Starting dashboard with $REFRESH_SCHEDULE refresh..."

  # Kindle-Oberfläche anhalten (K4: init.d, Paperwhite: upstart)
  if [ -x /etc/init.d/framework ]; then
    /etc/init.d/framework stop
  else
    stop lab126_gui >/dev/null 2>&1 || stop framework >/dev/null 2>&1
  fi
  initctl stop webreader >/dev/null 2>&1
  echo powersave >/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
  lipc-set-prop com.lab126.powerd preventScreenSaver 1

  /usr/sbin/eips -c >/dev/null 2>&1
  zeige "Kindle-Wetter startet ..."
  pruefe_programme
  export XH_BIN="$BIN_DIR/xh"
}

prepare_sleep() {
  echo "Preparing sleep"

  /usr/sbin/eips -f -g "$DIR/sleeping.png"

  # Give screen time to refresh
  sleep 2

  # Ensure a full screen refresh is triggered after wake from sleep
  num_refresh=$FULL_DISPLAY_REFRESH_RATE
}

refresh_dashboard() {
  echo "Refreshing dashboard"
  [ "$erster_lauf" = true ] && zeige "Verbinde mit WLAN ..."
  lipc-set-prop com.lab126.wifid enable 1 >/dev/null 2>&1
  lipc-set-prop com.lab126.cmd ensureConnection "wifi:" >/dev/null 2>&1
  if ! sh "$DIR/wait-for-wifi.sh" "$WIFI_TEST_IP"; then
    zeige "Kein WLAN - neuer Versuch in 10 Minuten"
    return 1
  fi

  [ "$erster_lauf" = true ] && zeige "Lade Wetterbild (bis zu 2 Minuten) ..."
  sh "$FETCH_DASHBOARD_CMD" "$DASH_PNG"
  fetch_status=$?

  if [ "$fetch_status" -ne 0 ] || [ ! -s "$DASH_PNG" ]; then
    zeige "Wetterbild nicht geladen (Fehler $fetch_status)"
    return 1
  fi
  erster_lauf=false

  if [ "$num_refresh" -eq "$FULL_DISPLAY_REFRESH_RATE" ]; then
    num_refresh=0

    # trigger a full refresh once in every 4 refreshes, to keep the screen clean
    echo "Full screen refresh"
    /usr/sbin/eips -f -g "$DASH_PNG"
  else
    echo "Partial screen refresh"
    /usr/sbin/eips -g "$DASH_PNG"
  fi

  num_refresh=$((num_refresh + 1))
}

log_battery_stats() {
  battery_level=$(gasgauge-info -c)
  echo "$(date) Battery level: $battery_level."

  if [ "$LOW_BATTERY_REPORTING" = true ]; then
    battery_level_numeric=${battery_level%?}
    if [ "$battery_level_numeric" -le "$LOW_BATTERY_THRESHOLD_PERCENT" ]; then
      "$LOW_BATTERY_CMD" "$battery_level_numeric"
    fi
  fi
}

rtc_sleep() {
  duration=$1

  if [ "$DEBUG" = true ]; then
    sleep "$duration"
  elif [ -e "$RTC" ]; then
    # Kindle 4: eigener Weckmechanismus
    # shellcheck disable=SC2039
    [ "$(cat "$RTC")" -eq 0 ] && echo -n "$duration" >"$RTC"
    echo "mem" >/sys/power/state
  else
    # Paperwhite & neuere: Wecker über die Standard-RTC-Schnittstelle
    for wake in /sys/class/rtc/rtc1/wakealarm /sys/class/rtc/rtc0/wakealarm; do
      [ -e "$wake" ] || continue
      echo 0 >"$wake"
      echo "+$duration" >"$wake"
      break
    done
    echo "mem" >/sys/power/state
  fi
}

main_loop() {
  while true; do
    log_battery_stats

    next_wakeup_secs=$("$BIN_DIR/next-wakeup" --schedule="$REFRESH_SCHEDULE" --timezone="$TIMEZONE")
    case "$next_wakeup_secs" in
      '' | *[!0-9]*) next_wakeup_secs=$STANDARD_WARTEZEIT ;;
    esac

    if [ "$next_wakeup_secs" -gt "$SLEEP_SCREEN_INTERVAL" ]; then
      action="sleep"
      prepare_sleep
    else
      action="suspend"
      refresh_dashboard
    fi

    # take a bit of time before going to sleep, so this process can be aborted
    sleep 10

    echo "Going to $action, next wakeup in ${next_wakeup_secs}s"

    rtc_sleep "$next_wakeup_secs"
  done
}

init
main_loop
