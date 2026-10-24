# Kindle-Wetter

Macht aus einem alten Kindle eine Wetterstation, die ohne eigenen Server läuft. Der Kindle erkennt seinen Standort selbst.

```
Kindle (wacht alle 30 min auf)                         GitHub (kostenlos)
  1. WLAN-Netze in der Nähe -> BeaconDB -> Koordinaten
     (Fallback: Standort der Internetverbindung)
  2. Ort geändert?  -> Variablen KW_LAT/KW_LON setzen ──►  Workflow "Wetterbild erzeugen"
                       und Workflow anstoßen               render.py: DWD-Daten (Bright Sky)
                                                           + Ortsname (OpenStreetMap)
  3. wetter.png laden und anzeigen  ◄───────────────────  GitHub Pages: wetter.png
  4. schlafen bis zur nächsten Aktualisierung
```

**Was angezeigt wird:**
- die aktuelle Temperatur und der Wetterzustand
- die Höchst- und Tiefstwerte von heute
- Wind, Luftfeuchte, Regen heute und Sonnenauf- und -untergang
- ein Verlauf über die nächsten 24 Stunden
- eine Vorhersage für die nächsten 5 Tage

Nachts (22–6 Uhr) zeigt der Kindle einen Nachtbildschirm und schläft. Das spart Akku.

**Datenschutz:** Der genaue Standort wird nur als Repository-*Variable* gespeichert. Die ist für Außenstehende nicht sichtbar, auch nicht in einem öffentlichen Repository, und wird auf etwa 1 km gerundet. Öffentlich sichtbar ist nur das fertige Bild mit dem Ortsnamen.

---

## Teil 1: GitHub

1. Repository `kindle-wetter` anlegen (öffentlich) und alle Dateien hochladen.
2. **Settings → Pages → Source: GitHub Actions**
3. **Token für den Kindle erstellen:** Gehe zu *Settings (Profil) → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token*.
   - Repository access: *Only select repositories → kindle-wetter*
   - Permissions: **Actions: Read and write** und **Variables: Read and write**
   - Ablaufdatum: am besten 1 Jahr
4. Das Token kommt auf dem Kindle in `dashboard/local/github.conf`.

Optional kannst du einen festen Ort erzwingen. Lege dazu unter *Settings → Secrets and variables → Actions → Variables* die Variable `KW_ORT` an.

## Teil 2: Kindle Paperwhite 2 (Seriennummer 90D4…, Firmware 5.12.x)

> ⚠️ Lass den Kindle bis zum Jailbreak im **Flugmodus**, damit kein Amazon-Update dazwischenkommt.

1. **Jailbreak mit WinterBreak2:** Folge dem Assistenten auf [kindlemodding.org](https://kindlemodding.org/jailbreaking/). Kurz gesagt:
   1. `jb.sh`, `patchedUks.sqsh` und `winterbreak2/` ins Hauptverzeichnis des Kindle kopieren.
   2. WLAN einschalten, im *Experimentellen Browser* `https://winterbreak2.now.sh/` öffnen und auf *Jailbreak* tippen.
   3. Danach sofort wieder in den Flugmodus.
2. **Hotfix, MRPI und KUAL installieren:** Das ist auf kindlemodding.org beschrieben. Den Hotfix nach jedem Neustart über „Run Hotfix" erneut ausführen, falls er angezeigt wird.
3. **kindle-dash herunterladen:** Lade die aktuelle Version von [github.com/pascalw/kindle-dash/releases](https://github.com/pascalw/kindle-dash/releases) herunter und entpacke sie.
4. **Dateien darüberkopieren:** Kopiere `kindle/dashboard/*` darüber. Trage danach dein Token in `local/github.conf` ein.
5. **Auf den Kindle kopieren:**
   - den Ordner nach `dashboard/`, sodass `start.sh` unter `/mnt/us/dashboard/start.sh` liegt,
   - `kindle/extensions/kindle-wetter` nach `extensions/`.
6. **Starten:** WLAN einschalten, dann **KUAL → Kindle-Wetter → Wetter-Anzeige starten**.

**Beenden:** Power-Taste etwa 20 Sekunden gedrückt halten. Der Kindle startet dann ganz normal neu.

**Probleme?** Schau in `dashboard/logs/dash.log`. Dort steht unter anderem `Standort (wlan|ip): …`.

## Lokal testen

```sh
pip install pillow
KW_LAT=53.55 KW_LON=9.99 python3 render.py out/wetter.png
```

Für andere Kindle-Modelle setzt du `KW_BREITE` und `KW_HOEHE` auf die Display-Auflösung.

| Modell | Auflösung |
|---|---|
| Kindle 4/5/7, Touch | 600 × 800 |
| Paperwhite 1/2 | 758 × 1024 |
| Paperwhite 3/4, Voyage, Oasis | 1072 × 1448 |

## Quellen und Lizenzen

- Wetterdaten: [Deutscher Wetterdienst](https://www.dwd.de) über [Bright Sky](https://brightsky.dev)
- Ortsnamen: © [OpenStreetMap](https://www.openstreetmap.org/copyright)-Mitwirkende (Nominatim)
- WLAN-Ortung: [BeaconDB](https://beacondb.net). Netze mit `_nomap` im Namen werden ausgelassen.
- Kindle-Client: [kindle-dash](https://github.com/pascalw/kindle-dash) (MIT), angepasst für den Paperwhite
- Schrift: [Inter](https://rsms.me/inter/) (SIL Open Font License)
