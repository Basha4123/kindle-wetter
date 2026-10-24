# Kindle-Wetter

Macht aus einem alten Kindle eine Wetterstation an der Wand. Du brauchst keinen eigenen Server dafür.

```
GitHub Actions (alle 30 min, kostenlos)       Kindle (WLAN, schläft dazwischen)
  render.py holt DWD-Daten (Bright Sky)  ──►    lädt wetter.png von GitHub Pages
  und zeichnet wetter.png                       und zeigt es an
```

**Was angezeigt wird:**
- die aktuelle Temperatur und der Wetterzustand
- die Höchst- und Tiefstwerte von heute
- Wind, Luftfeuchte, Regen heute und Sonnenauf- und -untergang
- ein Verlauf über die nächsten 24 Stunden mit Symbolen, Temperaturkurve und Regenbalken
- eine Vorhersage für die nächsten 5 Tage

Nachts (22–6 Uhr) zeigt der Kindle einen Nachtbildschirm und schläft. Das spart Akku.

---

## Teil 1: Das Wetterbild in der Cloud (ca. 10 Minuten)

1. Lege einen kostenlosen Account auf [github.com](https://github.com) an.
2. Erstelle ein neues **öffentliches** Repository mit dem Namen `kindle-wetter` und lade alle Dateien aus diesem Ordner hoch.
3. Gehe zu **Settings → Pages → Build and deployment → Source** und stelle **GitHub Actions** ein.
4. Gehe zu **Settings → Secrets and variables → Actions → Variables** und lege diese Variablen an:

   | Name | Beispiel | Bedeutung |
   |---|---|---|
   | `KW_ORT` | `Hamburg` | Name oben im Bild |
   | `KW_LAT` | `53.55` | Breitengrad |
   | `KW_LON` | `9.99` | Längengrad |

   Die Koordinaten findest du so: Rechtsklick auf den Ort in Google Maps, dann erscheint die erste Zahl. Zwei Nachkommastellen reichen. Das Repository ist öffentlich, deshalb lieber den Ort angeben als die genaue Hausadresse.
5. Gehe zu **Actions → „Wetterbild erzeugen" → Run workflow**.
6. Nach etwa einer Minute ist das Bild unter `https://DEIN-NAME.github.io/kindle-wetter/` erreichbar.

Das Bild wird danach automatisch alle 30 Minuten neu erzeugt.

## Teil 2: Den Kindle vorbereiten

> ⚠️ **Lass den Kindle bis zum Jailbreak im Flugmodus.** Ein automatisches Amazon-Update kann den Jailbreak unmöglich machen.

1. **Modell und Firmware herausfinden:** Geh auf *Einstellungen → Geräteoptionen → Geräteinfo* und notiere die Seriennummer (die ersten 4–6 Zeichen) und die Firmware-Version.
2. **Jailbreak:** Welche Methode passt, hängt von Modell und Firmware ab. Nutze den Assistenten auf [kindlemodding.org](https://kindlemodding.org/jailbreaking/) und folge der Anleitung dort.
3. **KUAL und MRPI installieren:** Das ist ebenfalls auf kindlemodding.org beschrieben.
4. **kindle-dash herunterladen:** Lade die aktuelle Version von [github.com/pascalw/kindle-dash/releases](https://github.com/pascalw/kindle-dash/releases) herunter und entpacke sie.
5. **Dateien von hier darüberkopieren:**
   - Kopiere `kindle/dashboard/*` über den entpackten kindle-dash-Ordner. Bestehende Dateien werden dabei ersetzt.
   - Ersetze in `local/fetch-dashboard.sh` den Platzhalter `DEIN-GITHUB-NAME` durch deinen GitHub-Namen.
6. **Auf den Kindle kopieren:** Schließe den Kindle per USB an und kopiere:
   - den Ordner mit allem darin nach `dashboard/`, sodass `start.sh` unter `/mnt/us/dashboard/start.sh` liegt,
   - `kindle/extensions/kindle-wetter` nach `extensions/`.
7. **Starten:** Schalte das WLAN ein und öffne **KUAL → Kindle-Wetter → Wetter-Anzeige starten**.

**Beenden:** Halte die Power-Taste etwa 20 Sekunden gedrückt. Der Kindle startet dann ganz normal neu.

**Probleme?** Das Protokoll liegt auf dem Kindle unter `dashboard/logs/dash.log` und ist per USB sichtbar.

## Lokal testen

```sh
pip install pillow
KW_ORT=Hamburg KW_LAT=53.55 KW_LON=9.99 python3 render.py out/wetter.png
```

Für andere Kindle-Modelle setzt du `KW_BREITE` und `KW_HOEHE` auf die Display-Auflösung. Diese Variablen kannst du auch in GitHub anlegen.

| Modell | Auflösung |
|---|---|
| Kindle 4/5/7, Touch | 600 × 800 |
| Paperwhite 1/2 | 758 × 1024 |
| Paperwhite 3/4, Voyage, Oasis | 1072 × 1448 |

## Quellen und Lizenzen

- Wetterdaten: [Deutscher Wetterdienst](https://www.dwd.de) über [Bright Sky](https://brightsky.dev)
- Kindle-Client: [kindle-dash](https://github.com/pascalw/kindle-dash) (MIT), angepasst für den Paperwhite
- Schrift: [Inter](https://rsms.me/inter/) (SIL Open Font License)
