# Kindle-Wetter

Macht aus einem alten Kindle eine Wetterstation, die ohne eigenen Server läuft. Der Kindle erkennt seinen Standort selbst.

```
Kindle (wacht alle 10 min auf)                         GitHub (kostenlos)
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

Das Wetter bleibt rund um die Uhr sichtbar (kein Bildschirmschoner) und wird alle 10 Minuten aktualisiert. Zeitplan und Intervalle stehen in `kindle/dashboard/local/env.sh`. Bei diesem Takt hält der Akku etwa 1 Woche, ein USB-Netzteil ist empfehlenswert.

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

1. **Jailbreak mit WinterBreak2:** Folge dem Assistenten auf [kindlemodding.org](https://kindlemodding.org/jailbreaking/WinterBreak2/). Den Hotfix bringt WinterBreak2 schon mit, und KUAL wird nicht gebraucht.
2. **Kindle-Paket herunterladen:** Gehe zu *Actions → „Kindle-Paket bauen"*, öffne den letzten erfolgreichen Lauf und lade das Artefakt **kindle-paket** herunter.
3. **Token eintragen:** Trage dein Token in `dashboard/local/github.conf` ein.
4. **Auf den Kindle kopieren:** Kopiere die Ordner `dashboard`, `documents` und `extensions` per USB ins Hauptverzeichnis des Kindle. Bestehende Ordner werden dabei zusammengeführt.
5. **Starten:** Schalte das WLAN ein. In der Bibliothek erscheint **„Kindle-Wetter starten"**. Antippen, fertig. Falls KUAL installiert ist, geht es alternativ über *KUAL → Kindle-Wetter*.

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
- Kindle-Client: [kindle-dash](https://github.com/pascalw/kindle-dash) (MIT), angepasst für den Paperwhite; HTTP-Client [xh](https://github.com/ducaale/xh) (MIT)
- Schrift: [Inter](https://rsms.me/inter/) (SIL Open Font License)
