#!/usr/bin/env python3
"""Erzeugt ein Wetter-Dashboard als Graustufen-PNG für ein Kindle-Display.

Daten: Deutscher Wetterdienst (DWD) über die freie Bright-Sky-API (kein API-Key nötig).
Konfiguration über Umgebungsvariablen:
  KW_ORT     Anzeigename des Ortes            (leer oder "auto": aus den Koordinaten bestimmt)
  KW_LAT     Breitengrad                      (Standard: 52.52)
  KW_LON     Längengrad                       (Standard: 13.41)
  KW_BREITE  Displaybreite in Pixeln          (Standard: 758, Kindle Paperwhite 1/2)
  KW_HOEHE   Displayhöhe in Pixeln            (Standard: 1024)
  KW_TZ      Zeitzone                         (Standard: Europe/Berlin)
  KW_DEMO    Pfad zu gespeicherten JSON-Daten statt Live-Abruf (zum Testen)
"""

import json
import math
import os
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

ORT = os.environ.get("KW_ORT", "auto").strip()
LAT = float(os.environ.get("KW_LAT", "52.52"))
LON = float(os.environ.get("KW_LON", "13.41"))
ZIEL_W = int(os.environ.get("KW_BREITE", "758"))
ZIEL_H = int(os.environ.get("KW_HOEHE", "1024"))
W, H = 758, 1024  # Layout-Koordinaten; das Bild wird am Ende auf ZIEL_W x ZIEL_H skaliert
TZ = ZoneInfo(os.environ.get("KW_TZ", "Europe/Berlin"))

S = 3  # Supersampling-Faktor für glatte Kanten
FONTS = Path(__file__).parent / "fonts"

# E-Ink kann 16 Graustufen; wir bleiben auf diesen Stufen.
BLACK, DARK, MID, LIGHT, PALE, WHITE = 0, 68, 119, 187, 221, 255

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]
ZUSTAND = {
    "clear-day": "Sonnig", "clear-night": "Klar",
    "partly-cloudy-day": "Teils bewölkt", "partly-cloudy-night": "Teils bewölkt",
    "cloudy": "Bewölkt", "fog": "Nebel", "wind": "Windig", "rain": "Regen",
    "sleet": "Schneeregen", "snow": "Schnee", "hail": "Hagel", "thunderstorm": "Gewitter",
}
NIEDERSCHLAG = {"rain", "sleet", "snow", "hail", "thunderstorm"}


# ---------------------------------------------------------------- Daten

def hole_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "kindle-wetter/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def lade_daten():
    if os.environ.get("KW_DEMO"):
        return json.loads(Path(os.environ["KW_DEMO"]).read_text())
    heute = datetime.now(TZ).date()
    base = "https://api.brightsky.dev"
    tz = TZ.key
    stunden = hole_json(f"{base}/weather?lat={LAT}&lon={LON}&tz={tz}"
                        f"&date={heute}&last_date={heute + timedelta(days=6)}")
    try:
        aktuell = hole_json(f"{base}/current_weather?lat={LAT}&lon={LON}&tz={tz}")["weather"]
    except Exception as e:  # Messwerte sind nett, aber nicht zwingend
        print(f"Aktuelle Messwerte nicht verfügbar: {e}", file=sys.stderr)
        aktuell = {}
    return {"stunden": stunden["weather"], "aktuell": aktuell,
            "ort": ortsname(stunden.get("sources") or [])}


def ortsname(quellen):
    """Name des Ortes: fest vorgegeben, sonst per OpenStreetMap aus den Koordinaten."""
    if ORT and ORT.lower() != "auto":
        return ORT
    try:
        antwort = hole_json("https://nominatim.openstreetmap.org/reverse?format=json"
                            f"&lat={LAT}&lon={LON}&zoom=10&accept-language=de")
        adresse = antwort.get("address", {})
        for feld in ("city", "town", "village", "municipality", "county"):
            if adresse.get(feld):
                return adresse[feld]
    except Exception as e:
        print(f"Ortsname nicht ermittelbar: {e}", file=sys.stderr)
    if quellen and quellen[0].get("station_name"):
        return quellen[0]["station_name"].split("/")[0].title()
    return f"{LAT:.2f}, {LON:.2f}"


def ts(record):
    return datetime.fromisoformat(record["timestamp"]).astimezone(TZ)


def tag_icon(icon):
    return icon.replace("-night", "-day") if icon else "cloudy"


def zusammenfassen(stunden):
    """Fasst Stundenwerte zu Tageswerten zusammen."""
    tage = defaultdict(list)
    for s in stunden:
        tage[ts(s).date()].append(s)
    ergebnis = []
    for tag in sorted(tage):
        werte = tage[tag]
        temps = [s["temperature"] for s in werte if s.get("temperature") is not None]
        if len(temps) < 12:  # unvollständiger Tag am Ende der Vorhersage
            continue
        regen = sum(s.get("precipitation") or 0 for s in werte)
        wahrsch = max((s.get("precipitation_probability") or 0) for s in werte)
        tagsueber = [tag_icon(s.get("icon")) for s in werte if 8 <= ts(s).hour <= 19] or ["cloudy"]
        if "thunderstorm" in tagsueber:
            icon = "thunderstorm"
        elif regen >= 1.0:
            nass = [i for i in tagsueber if i in NIEDERSCHLAG]
            icon = Counter(nass).most_common(1)[0][0] if nass else "rain"
        else:
            icon = Counter(tagsueber).most_common(1)[0][0]
        ergebnis.append({"tag": tag, "max": max(temps), "min": min(temps),
                         "regen": regen, "wahrsch": wahrsch, "icon": icon})
    return ergebnis


def sonne(tag, lat, lon):
    """Sonnenauf- und -untergang (NOAA-Näherung, auf ca. 1 Minute genau)."""
    n = tag.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    phi = math.radians(lat)
    cos_ha = (math.cos(math.radians(90.833)) / (math.cos(phi) * math.cos(decl))
              - math.tan(phi) * math.tan(decl))
    if not -1 <= cos_ha <= 1:
        return None, None
    ha = math.degrees(math.acos(cos_ha))
    mitternacht = datetime(tag.year, tag.month, tag.day, tzinfo=ZoneInfo("UTC"))
    auf = mitternacht + timedelta(minutes=720 - 4 * (lon + ha) - eqt)
    unter = mitternacht + timedelta(minutes=720 - 4 * (lon - ha) - eqt)
    return auf.astimezone(TZ), unter.astimezone(TZ)


def himmelsrichtung(grad):
    if grad is None:
        return ""
    return ["N", "NO", "O", "SO", "S", "SW", "W", "NW"][int((grad + 22.5) % 360 // 45)]


def zahl(x, stellen=1):
    return f"{x:.{stellen}f}".replace(".", ",")


# ---------------------------------------------------------------- Zeichnen

class Leinwand:
    """Zeichnet in Display-Koordinaten auf eine vergrößerte Fläche."""

    def __init__(self):
        self.img = Image.new("L", (W * S, H * S), WHITE)
        self.d = ImageDraw.Draw(self.img)
        self._fonts = {}

    def font(self, name, size):
        key = (name, size)
        if key not in self._fonts:
            self._fonts[key] = ImageFont.truetype(str(FONTS / f"{name}.otf"), size * S)
        return self._fonts[key]

    def text(self, xy, txt, size, name="Inter-Regular", fill=BLACK, anchor="la"):
        self.d.text((xy[0] * S, xy[1] * S), txt, font=self.font(name, size), fill=fill, anchor=anchor)

    def breite(self, txt, size, name="Inter-Regular"):
        return self.d.textlength(txt, font=self.font(name, size)) / S

    def linie(self, pts, fill=BLACK, w=1.0):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=max(1, round(w * S)), joint="curve")

    def kreis(self, cx, cy, r, fill=None, outline=None, w=1.0):
        self.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S],
                       fill=fill, outline=outline, width=max(1, round(w * S)))

    def rechteck(self, x0, y0, x1, y1, fill, r=0):
        self.d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=r * S, fill=fill)

    def polygon(self, pts, fill):
        self.d.polygon([(x * S, y * S) for x, y in pts], fill=fill)

    def bogen(self, cx, cy, r, start, ende, fill=BLACK, w=1.0):
        self.d.arc([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S],
                   start, ende, fill=fill, width=max(1, round(w * S)))

    def fertig(self):
        return self.img.resize((ZIEL_W, ZIEL_H), Image.LANCZOS)


# ---- Wettersymbole (in einem Kasten der Größe g um den Mittelpunkt cx, cy)

def symbol_sonne(c, cx, cy, g, ausgefuellt=True):
    r = g * 0.2
    w = g * 0.055
    for i in range(8):
        a = math.radians(i * 45)
        c.linie([(cx + math.cos(a) * r * 1.45, cy + math.sin(a) * r * 1.45),
                 (cx + math.cos(a) * r * 2.0, cy + math.sin(a) * r * 2.0)], w=w)
    c.kreis(cx, cy, r, fill=DARK if ausgefuellt else WHITE, outline=BLACK, w=w)


def symbol_mond(c, cx, cy, g):
    r = g * 0.3
    c.kreis(cx, cy, r, fill=DARK)
    c.kreis(cx + r * 0.55, cy - r * 0.35, r * 0.85, fill=WHITE)


def symbol_wolke(c, cx, cy, g, fill=WHITE):
    """Wolke aus Kreisen; erst schwarz vergrößert (Kontur), dann gefüllt."""
    w = g * 0.055
    teile = [(-0.2, 0.03, 0.17), (0.0, -0.08, 0.23), (0.2, 0.04, 0.15)]
    unten = cy + g * 0.18
    for rand, farbe in ((w, BLACK), (0, fill)):
        for dx, dy, r in teile:
            c.kreis(cx + dx * g, cy + dy * g, r * g + rand, fill=farbe)
        c.rechteck(cx - 0.36 * g - rand, cy + 0.02 * g - rand, cx + 0.34 * g + rand,
                   unten + rand, fill=farbe, r=0.16 * g)


def schneeflocke(c, cx, cy, r, w):
    for i in range(3):
        a = math.radians(i * 60 + 90)
        c.linie([(cx - math.cos(a) * r, cy - math.sin(a) * r),
                 (cx + math.cos(a) * r, cy + math.sin(a) * r)], w=w)


def symbol(c, kind, cx, cy, g):
    w = g * 0.05
    kind = kind or "cloudy"
    if kind == "clear-day":
        symbol_sonne(c, cx, cy, g)
    elif kind == "clear-night":
        symbol_mond(c, cx, cy, g)
    elif kind in ("partly-cloudy-day", "partly-cloudy-night"):
        if kind.endswith("day"):
            symbol_sonne(c, cx - g * 0.13, cy - g * 0.13, g * 0.8)
        else:
            symbol_mond(c, cx - g * 0.1, cy - g * 0.14, g * 0.75)
        symbol_wolke(c, cx + g * 0.08, cy + g * 0.12, g * 0.72)
    elif kind == "fog":
        symbol_wolke(c, cx, cy - g * 0.12, g * 0.8)
        for i, (x0, x1) in enumerate([(-0.36, 0.3), (-0.28, 0.38)]):
            y = cy + g * (0.24 + 0.12 * i)
            c.linie([(cx + x0 * g, y), (cx + x1 * g, y)], w=w)
    elif kind == "wind":
        for i, (laenge, r) in enumerate([(0.5, 0.1), (0.62, 0.12), (0.4, 0.08)]):
            y = cy + g * (-0.2 + 0.2 * i)
            x0 = cx - g * 0.36
            x1 = x0 + laenge * g
            c.linie([(x0, y), (x1, y)], w=w)
            c.bogen(x1, y - r * g, r * g, -90, 90, w=w)
    else:
        symbol_wolke(c, cx, cy - g * 0.1, g * 0.85, fill=PALE if kind in NIEDERSCHLAG else WHITE)
        y0, y1 = cy + g * 0.22, cy + g * 0.42
        xs = [cx - g * 0.18, cx, cx + g * 0.18]
        if kind == "rain":
            for x in xs:
                c.linie([(x + g * 0.04, y0), (x - g * 0.04, y1)], w=w)
        elif kind == "snow":
            for x in xs:
                schneeflocke(c, x, (y0 + y1) / 2, g * 0.08, w * 0.8)
        elif kind == "sleet":
            c.linie([(xs[0] + g * 0.04, y0), (xs[0] - g * 0.04, y1)], w=w)
            schneeflocke(c, xs[1], (y0 + y1) / 2, g * 0.08, w * 0.8)
            c.linie([(xs[2] + g * 0.04, y0), (xs[2] - g * 0.04, y1)], w=w)
        elif kind == "hail":
            for i, x in enumerate(xs):
                c.kreis(x, y0 + g * (0.06 + 0.08 * (i % 2)), g * 0.045, fill=BLACK)
        elif kind == "thunderstorm":
            c.polygon([(cx + g * 0.04, y0 - g * 0.06), (cx - g * 0.1, cy + g * 0.33),
                       (cx, cy + g * 0.33), (cx - g * 0.05, cy + g * 0.48),
                       (cx + g * 0.12, cy + g * 0.28), (cx + g * 0.02, cy + g * 0.28),
                       (cx + g * 0.1, y0 - g * 0.06)], fill=BLACK)


# ---- Bereiche

def kopf(c, jetzt, m, ort):
    groesse = 34
    while groesse > 22 and c.breite(ort, groesse, "Inter-Bold") > W - 2 * m - 280:
        groesse -= 2
    c.text((m, 34), ort, groesse, "Inter-Bold", anchor="ls")
    datum = f"{WOCHENTAGE[jetzt.weekday()]}, {jetzt.day}. {MONATE[jetzt.month - 1]}"
    c.text((W - m, 34), datum, 22, "Inter-SemiBold", anchor="rs")
    c.text((W - m, 60), f"Stand {jetzt:%H:%M} Uhr", 16, fill=MID, anchor="rs")
    c.linie([(m, 76), (W - m, 76)], fill=LIGHT, w=1.5)


def jetzt_block(c, aktuell, naechste, heute, m, y):
    temp = aktuell.get("temperature")
    if temp is None:
        temp = naechste["temperature"]
    icon = aktuell.get("icon") or naechste.get("icon") or "cloudy"
    # Messstationen melden oft "cloudy", obwohl es gerade regnet.
    bedingung = aktuell.get("condition") or naechste.get("condition")
    if bedingung in NIEDERSCHLAG and icon not in NIEDERSCHLAG:
        icon = bedingung

    g = 230
    symbol(c, icon, m + g / 2 - 10, y + g / 2, g)
    tx = m + g + 20
    c.text((tx, y + 150), f"{round(temp)}°", 150, "InterDisplay-Bold", anchor="ls")
    c.text((tx + 6, y + 196), ZUSTAND.get(icon, ""), 30, "Inter-SemiBold", anchor="ls")
    if heute:
        c.text((tx + 6, y + 232), f"Max {round(heute['max'])}°   Min {round(heute['min'])}°",
               24, fill=DARK, anchor="ls")


def details(c, aktuell, naechste, heute, auf, unter, m, y):
    wind = aktuell.get("wind_speed_10") or naechste.get("wind_speed")
    richtung = aktuell.get("wind_direction_10") or naechste.get("wind_direction")
    boeen = aktuell.get("wind_gust_speed_10") or naechste.get("wind_gust_speed")
    feuchte = aktuell.get("relative_humidity") or naechste.get("relative_humidity")
    felder = [
        ("Wind", f"{round(wind)} km/h {himmelsrichtung(richtung)}" if wind is not None else "–",
         f"Böen {round(boeen)}" if boeen else ""),
        ("Luftfeuchte", f"{round(feuchte)} %" if feuchte is not None else "–", ""),
        ("Regen heute", f"{zahl(heute['regen'])} mm" if heute else "–",
         f"Risiko {heute['wahrsch']} %" if heute and heute["wahrsch"] else ""),
        ("Sonne", f"{auf:%H:%M} – {unter:%H:%M}" if auf else "–",
         f"{(unter - auf).seconds // 3600} h {(unter - auf).seconds % 3600 // 60} min" if auf else ""),
    ]
    c.rechteck(m, y, W - m, y + 104, fill=PALE, r=14)
    spalte = (W - 2 * m) / len(felder)
    for i, (titel, wert, zusatz) in enumerate(felder):
        x = m + 18 + i * spalte
        c.text((x, y + 30), titel.upper(), 14, "Inter-SemiBold", fill=DARK, anchor="ls")
        c.text((x, y + 64), wert, 23 if len(wert) < 11 else 20, "Inter-Bold", anchor="ls")
        if zusatz:
            c.text((x, y + 88), zusatz, 16, fill=DARK, anchor="ls")


def verlauf(c, stunden, jetzt, m, y, hoehe):
    start = jetzt.replace(minute=0, second=0, microsecond=0)
    werte = [s for s in stunden if start <= ts(s) <= start + timedelta(hours=24)
             and s.get("temperature") is not None]
    if len(werte) < 2:
        return
    c.text((m, y + 16), "NÄCHSTE 24 STUNDEN", 15, "Inter-SemiBold", fill=DARK, anchor="ls")

    x0, x1 = m + 14, W - m - 14
    oben = y + 118          # Oberkante Temperaturkurve
    unten = y + hoehe - 40  # Grundlinie
    temps = [s["temperature"] for s in werte]
    tmin, tmax = min(temps), max(temps)
    spanne = max(tmax - tmin, 4)
    mitte = (tmax + tmin) / 2
    tmin, tmax = mitte - spanne / 2, mitte + spanne / 2
    kurve_unten = unten - 26

    def px(i):
        return x0 + (x1 - x0) * i / (len(werte) - 1)

    def py(t):
        return kurve_unten - (t - tmin) / (tmax - tmin) * (kurve_unten - oben)

    # Niederschlag als Balken, Skala bis mindestens 4 mm/h
    rmax = max(4.0, max((s.get("precipitation") or 0) for s in werte))
    bw = (x1 - x0) / (len(werte) - 1) * 0.62
    for i, s in enumerate(werte):
        mm = s.get("precipitation") or 0
        if mm >= 0.1:
            bh = max(3, mm / rmax * (unten - oben) * 0.6)
            c.rechteck(px(i) - bw / 2, unten - bh, px(i) + bw / 2, unten, fill=LIGHT, r=2)

    # Temperaturfläche und -linie
    punkte = [(px(i), py(t)) for i, t in enumerate(temps)]
    c.polygon(punkte + [(x1, unten), (x0, unten)], fill=238)
    c.linie(punkte, fill=BLACK, w=3.2)
    c.linie([(x0, unten), (x1, unten)], fill=MID, w=1.2)

    # Alle 3 Stunden: Symbol, Temperatur, Uhrzeit
    for i, s in enumerate(werte):
        t = ts(s)
        if i % 3:
            continue
        x = px(i)
        symbol(c, s.get("icon"), x, y + 56, 46)
        c.kreis(x, py(temps[i]), 4.5, fill=WHITE, outline=BLACK, w=2.2)
        c.text((x, py(temps[i]) - 12), f"{round(temps[i])}°", 19, "Inter-Bold", anchor="ms")
        label = "Jetzt" if i == 0 else f"{t:%H}"
        c.text((x, unten + 26), label, 17, "Inter-SemiBold" if i == 0 else "Inter-Medium",
               fill=BLACK if i == 0 else DARK, anchor="ms")


def vorhersage(c, tage, m, y, hoehe):
    c.text((m, y + 16), "NÄCHSTE TAGE", 15, "Inter-SemiBold", fill=DARK, anchor="ls")
    # Heute steht schon oben; hier die folgenden Tage.
    morgen = datetime.now(TZ).date() + timedelta(days=1)
    tage = [t for t in tage if t["tag"] >= morgen][:5]
    if not tage:
        return
    alle_min = min(t["min"] for t in tage)
    alle_max = max(t["max"] for t in tage)
    spalte = (W - 2 * m) / len(tage)
    for i, t in enumerate(tage):
        cx = m + spalte * (i + 0.5)
        name = "Morgen" if t["tag"] == morgen else WOCHENTAGE[t["tag"].weekday()][:2]
        c.text((cx, y + 48), name, 22, "Inter-Bold", anchor="ms")
        symbol(c, t["icon"], cx, y + 94, 68)
        c.text((cx, y + 158), f"{round(t['max'])}°", 30, "Inter-Bold", anchor="ms")
        c.text((cx, y + 186), f"{round(t['min'])}°", 22, "Inter-Medium", fill=MID, anchor="ms")
        # Temperaturspanne als kleiner Balken, über alle Tage vergleichbar
        bx0, bx1 = cx - spalte * 0.32, cx + spalte * 0.32
        def bx(v):
            return bx0 + (v - alle_min) / max(alle_max - alle_min, 1) * (bx1 - bx0)
        c.rechteck(bx0, y + 198, bx1, y + 204, fill=PALE, r=3)
        c.rechteck(bx(t["min"]), y + 198, max(bx(t["max"]), bx(t["min"]) + 6), y + 204, fill=DARK, r=3)
        regen = f"{zahl(t['regen'])} mm" if t["regen"] >= 0.1 else "trocken"
        c.text((cx, y + 228), regen, 17, "Inter-SemiBold" if t["regen"] >= 0.1 else "Inter-Regular",
               fill=BLACK if t["regen"] >= 1 else DARK, anchor="ms")
        if t["wahrsch"] and t["regen"] >= 0.1:
            c.text((cx, y + 247), f"{t['wahrsch']} %", 15, fill=MID, anchor="ms")
        if i:
            c.linie([(m + spalte * i, y + 34), (m + spalte * i, y + hoehe - 6)], fill=PALE, w=1.2)


def render(daten):
    jetzt = datetime.now(TZ)
    stunden = sorted(daten["stunden"], key=ts)
    aktuell = daten.get("aktuell") or {}
    naechste = min(stunden, key=lambda s: abs((ts(s) - jetzt).total_seconds()))
    tage = zusammenfassen(stunden)
    heute = next((t for t in tage if t["tag"] == jetzt.date()), tage[0] if tage else None)
    auf, unter = sonne(jetzt.date(), LAT, LON)

    c = Leinwand()
    m = 36
    kopf(c, jetzt, m, daten.get("ort") or ORT or "Wetter")
    jetzt_block(c, aktuell, naechste, heute, m, 92)
    details(c, aktuell, naechste, heute, auf, unter, m, 342)
    verlauf(c, stunden, jetzt, m, 466, 262)
    c.linie([(m, 736), (W - m, 736)], fill=LIGHT, w=1.5)
    vorhersage(c, tage, m, 748, 254)
    c.text((W / 2, H - 8), "Daten: Deutscher Wetterdienst via Bright Sky", 13, fill=MID, anchor="ms")
    return c.fertig()


def main():
    ziel = Path(sys.argv[1] if len(sys.argv) > 1 else "out/wetter.png")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    bild = render(lade_daten())
    bild.save(ziel, optimize=True)
    print(f"Gespeichert: {ziel} ({bild.size[0]}x{bild.size[1]})")


if __name__ == "__main__":
    main()
