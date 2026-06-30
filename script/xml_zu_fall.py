#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generiert aus einer Falldaten-XML (siehe template/falldaten.xml) das Fallskript
fall_<Aktenzeichen>_<Kurzname>.py, das mit der Engine pfueb_fill.py das amtliche
PfÜB-Formular befüllt.

Verwendung (aus dem Projektwurzelverzeichnis):
    python3 script/xml_zu_fall.py data/fall_06629_R-R-Immobilien.xml
    # -> schreibt data/fall_06629_R-R-Immobilien.py

Optional anderen Zielpfad angeben:
    python3 script/xml_zu_fall.py daten.xml data/fall_xyz.py

Das Mapping "semantisches Feld -> Position (Seite, y, x)" ist hier fest
hinterlegt; es beschreibt das Formular und ist für alle Fälle gleich.
"""
import sys
import os
import xml.etree.ElementTree as ET

# Anrede/Typ -> Position des Kontrollkästchens je Block
# (unternehmen nur bei den "Angaben zu ...", nicht beim gesetzlichen Vertreter)
def _txt(node, pfad, default=""):
    if node is None:
        return default
    el = node.find(pfad)
    if el is None or el.text is None:
        return default
    return el.text.strip()

def _bool(node, pfad):
    return _txt(node, pfad).lower() in ("true", "ja", "1", "x")

class Gen:
    def __init__(self):
        self.lines = []   # erzeugte f.text/f.kreuz-Zeilen
    def text(self, page, y, x, value):
        if value is None or str(value).strip() == "":
            return
        self.lines.append(f"f.text({page}, {y}, {x}, {value!r})")
    def kreuz(self, page, y, x):
        self.lines.append(f"f.kreuz({page}, {y}, {x})")
    def stempel(self, page, x, y, s="X"):
        self.lines.append(f"f.stempel({page}, {x}, {y}, {s!r})")
    def leer(self):
        self.lines.append("")
    def kommentar(self, s):
        self.lines.append(f"# {s}")

# Kontrollkästchen-Positionen für Anrede/Typ je "Angaben zu"-Block
ANGABEN_BOX = {
    # block: (herr, frau, unternehmen)  -> (page,y,x)
    "schuldner_s1":  {"herr": (1,453,70),  "frau": (1,453,114), "unternehmen": (1,453,158)},
    "glaeubiger":    {"herr": (3,670,81),  "frau": (3,670,130), "unternehmen": (3,670,174)},
    "schuldner_s4":  {"herr": (4,516,81),  "frau": (4,516,116), "unternehmen": (4,516,152)},
    "drittschuldner":{"herr": (6,769,85),  "frau": (6,769,133), "unternehmen": (6,769,178)},
}

def typ_kreuz(g, block, typ):
    typ = (typ or "").lower()
    box = ANGABEN_BOX[block]
    if typ in box:
        g.kreuz(*box[typ])


def generate(xml_path):
    root = ET.parse(xml_path).getroot()
    g = Gen()

    fall = root.find("fall")
    az = fall.get("aktenzeichen", "0000")
    kurz = fall.get("kurzname", "Fall")

    antrag = root.find("antrag")
    gericht = root.find("gericht")
    glaeub = root.find("glaeubiger")
    bevoll = root.find("bevollmaechtigter")
    schuld = root.find("schuldner")
    titel = root.find("vollstreckungstitel")
    dritt = root.find("drittschuldner")
    ford = root.find("forderung")
    zvk = root.find("zwangsvollstreckungskosten")

    # ---- Seite 1 ----
    g.kommentar("Seite 1: Antrag / Gericht / Schuldner / Antragsteller / Zusatzanträge")
    g.text(1, 666, 70, _txt(gericht, "name"))
    g.text(1, 638, 70, _txt(gericht, "strasse"))
    g.text(1, 624, 70, _txt(gericht, "plz_ort"))
    g.text(1, 624, 354, _txt(antrag, "ort"))
    g.text(1, 623, 521, _txt(antrag, "datum"))
    typ_kreuz(g, "schuldner_s1", _txt(schuld, "typ"))
    g.text(1, 423, 70, _txt(schuld, "name"))
    g.text(1, 423, 321, _txt(schuld, "vorname"))
    g.text(1, 397, 70, _txt(schuld, "strasse"))
    g.text(1, 397, 321, _txt(schuld, "hausnummer"))
    g.text(1, 372, 70, _txt(schuld, "plz"))
    g.text(1, 372, 321, _txt(schuld, "ort"))
    g.kreuz(1, 283, 225)  # Antragsteller: Bevollmächtigter
    g.text(1, 253, 73, _txt(bevoll, "name"))
    g.text(1, 253, 321, _txt(bevoll, "vorname"))
    g.text(1, 227, 74, _txt(bevoll, "telefon"))
    g.text(1, 177, 73, _txt(bevoll, "geschaeftszeichen"))
    if _bool(antrag, "ausfertigung"): g.kreuz(1, 124, 73)
    if _bool(antrag, "zustellung_durch_geschaeftsstelle"): g.kreuz(1, 110, 73)
    if _bool(antrag, "drittschuldnererklaerung_840"): g.kreuz(1, 97, 83)
    g.leer()

    # ---- Seite 2 ----
    g.kommentar("Seite 2: Namen der Antragsteller")
    bez = (bevoll.get("bezeichnung") if bevoll is not None else "") or "Rechtsanwalt"
    namen = " ".join(x for x in [bez, _txt(bevoll, "vorname"), _txt(bevoll, "name")] if x)
    g.text(2, 79, 70, namen)
    g.kreuz(2, 515, 405)  # Versand als elektronisches Dokument
    g.kreuz(2, 176, 74)   # Kreuz Versicherung gem. § 753a S. 1 ZPO
    g.kreuz(2, 160, 74)   # Kreuz Versicherung gem. § 829a Abs. 1 S. 1 Nr. 4 ZPO
    g.leer()

    # ---- Seite 3: Modul A Gläubigerin + ges. Vertreter ----
    g.kommentar("Seite 3: Modul A – Gläubiger + gesetzlicher Vertreter")
    g.text(3, 786, 111, _txt(gericht, "name"))
    g.text(3, 682, 185, glaeub.get("ziffer", "1"))
    typ_kreuz(g, "glaeubiger", _txt(glaeub, "typ"))
    g.text(3, 640, 82, _txt(glaeub, "name"))
    g.text(3, 640, 327, _txt(glaeub, "vorname"))
    g.text(3, 614, 82, _txt(glaeub, "strasse"))
    g.text(3, 614, 327, _txt(glaeub, "hausnummer"))
    g.text(3, 589, 82, _txt(glaeub, "plz"))
    g.text(3, 589, 327, _txt(glaeub, "ort"))
    if not _bool(glaeub, "vorsteuerabzugsberechtigt"):
        g.kreuz(3, 526, 84)  # "nicht vorsteuerabzugsberechtigt"
    gv = glaeub.find("gesetzlicher_vertreter")
    if gv is not None:
        g.text(3, 481, 161, glaeub.get("ziffer", "1"))
        g.kreuz(3, 471, 85)
        g.kreuz(3, 425, 96 if _txt(gv, "anrede").lower() != "frau" else 134)
        g.text(3, 396, 96, _txt(gv, "name"))
        g.text(3, 367, 96, _txt(gv, "vorname"))
        g.text(3, 339, 96, _txt(gv, "strasse"))
        g.text(3, 311, 96, _txt(gv, "hausnummer"))
        g.text(3, 283, 96, _txt(gv, "plz"))
        g.text(3, 255, 96, _txt(gv, "ort"))
    g.leer()

    # ---- Seite 4: Modul A Bevollmächtigter + Bankverbindung + Modul B Schuldner ----
    g.kommentar("Seite 4: Modul A Bevollmächtigter + Bankverbindung + Modul B Schuldner")
    g.text(4, 782, 161, glaeub.get("ziffer", "1"))
    g.kreuz(4, 760, 84 if _txt(bevoll, "anrede").lower() != "frau" else 133)
    g.text(4, 730, 85, _txt(bevoll, "name"))
    g.text(4, 730, 330, _txt(bevoll, "vorname"))
    g.text(4, 704, 85, _txt(bevoll, "strasse"))
    g.text(4, 703, 270, _txt(bevoll, "hausnummer"))
    g.text(4, 703, 330, _txt(bevoll, "plz"))
    g.text(4, 704, 390, _txt(bevoll, "ort"))
    g.text(4, 679, 330, _txt(bevoll, "geschaeftszeichen"))
    bank = bevoll.find("bankverbindung") if bevoll is not None else None
    if bank is not None:
        g.kreuz(4, 643, 252)  # Bankverbindung: Bevollmächtigter
        g.text(4, 613, 85, _txt(bank, "kontoinhaber"))
        g.text(4, 590, 85, _txt(bank, "iban"))
        g.text(4, 562, 85, _txt(bank, "verwendungszweck"))
    g.text(4, 530, 183, schuld.get("ziffer", "1"))
    typ_kreuz(g, "schuldner_s4", _txt(schuld, "typ"))
    g.text(4, 486, 81, _txt(schuld, "name"))
    g.text(4, 486, 325, _txt(schuld, "vorname"))
    g.text(4, 461, 81, _txt(schuld, "strasse"))
    g.text(4, 461, 325, _txt(schuld, "hausnummer"))
    g.text(4, 436, 81, _txt(schuld, "plz"))
    g.text(4, 436, 143, _txt(schuld, "ort"))
    sv = schuld.find("gesetzlicher_vertreter")
    if sv is not None:
        g.text(4, 342, 161, schuld.get("ziffer", "1"))
        g.kreuz(4, 331, 84)
        g.kreuz(4, 285, 96 if _txt(sv, "anrede").lower() != "frau" else 134)
        g.text(4, 256, 96, _txt(sv, "name"))
        g.text(4, 229, 96, _txt(sv, "vorname"))
        g.text(4, 202, 96, _txt(sv, "strasse"))
        g.text(4, 175, 96, _txt(sv, "hausnummer"))
        g.text(4, 148, 96, _txt(sv, "plz"))
        g.text(4, 121, 96, _txt(sv, "ort"))
    g.leer()

    # ---- Seite 5: Modul C Vollstreckungstitel ----
    g.kommentar("Seite 5: Modul C – Vollstreckungstitel + Dokumenttyp-Auswahl")
    g.text(5, 392, 239, titel.get("ziffer", "1"))
    g.text(5, 359, 84, _txt(titel, "art"))
    g.text(5, 359, 324, _txt(titel, "aussteller"))
    g.text(5, 331, 84, _txt(titel, "datum"))
    g.text(5, 331, 324, _txt(titel, "geschaeftszeichen"))
    g.stempel(5, 130.6, 440.6, "X")  # "Pfändungs- und Überweisungsbeschluss"
    g.leer()

    # ---- Seite 6: Modul D Drittschuldner ----
    g.kommentar("Seite 6: Modul D – Drittschuldner (Bank) + Modulverweis")
    g.text(6, 782, 251, dritt.get("ziffer", "1"))
    typ_kreuz(g, "drittschuldner", _txt(dritt, "typ"))
    g.text(6, 739, 85, _txt(dritt, "name"))
    g.text(6, 714, 85, _txt(dritt, "strasse"))
    g.text(6, 714, 330, _txt(dritt, "hausnummer"))
    g.text(6, 688, 85, _txt(dritt, "plz"))
    g.text(6, 688, 330, _txt(dritt, "ort"))
    g.text(6, 591, 409, _txt(dritt, "schuldner_ziffer") or schuld.get("ziffer", "1"))
    g.text(6, 591, 517, _txt(dritt, "modul") or "H")
    g.leer()

    # ---- Seite 7: Modul H Kontokonkretisierung ----
    iban = _txt(dritt, "schuldner_konto_iban")
    if iban:
        g.kommentar("Seite 7: Modul H – Konkretisierung des Schuldnerkontos")
        g.kreuz(7, 253, 84)
        text = ("Die vorstehend gepfändeten Ansprüche betreffen insbesondere das beim Drittschuldner\n"
                f"geführte Konto des Schuldners IBAN {iban}.")
        g.text(7, 194, 96, text)
        g.leer()

    # ---- Seite 8: Überweisung ----
    if _bool(antrag, "ueberweisung_zur_einziehung"):
        g.kommentar("Seite 8: Überweisung zur Einziehung")
        g.kreuz(8, 490, 85)
        g.leer()

    # ---- Seite 12: Forderungsaufstellung I. Hauptforderung ----
    g.kommentar("Seite 12: Forderungsaufstellung – I. Hauptforderung")
    g.text(12, 720, 402, titel.get("ziffer", "1"))
    hf = ford.find("hauptforderung")
    if hf is not None:
        g.kreuz(12, 685, 73)
        g.text(12, 670, 442, _txt(hf, "betrag"))
        g.text(12, 657, 442, _txt(hf, "zinsen_ausgerechnet"))
        lz = hf.find("laufende_zinsen")
        if lz is not None and _txt(lz, "prozentpunkte"):
            g.kreuz(12, 577, 82)
            g.text(12, 575, 92, _txt(lz, "prozentpunkte"))
            g.text(12, 564, 99, _txt(lz, "aus"))
            g.text(12, 564, 257, _txt(lz, "ab"))
    g.leer()

    # ---- Seite 13: III. Titulierte Kosten + IV. ZV-Kosten ----
    g.kommentar("Seite 13: III. Titulierte Kosten")
    mvk = ford.find("mahnverfahrenskosten")
    if mvk is not None:
        g.kreuz(13, 769, 73)
        g.text(13, 755, 442, _txt(mvk, "betrag"))
        lz = mvk.find("laufende_zinsen")
        if lz is not None and _txt(lz, "prozentpunkte"):
            g.kreuz(13, 662, 82)
            g.text(13, 660, 92, _txt(lz, "prozentpunkte"))
            g.text(13, 649, 99, _txt(lz, "aus"))
            g.text(13, 648, 257, _txt(lz, "ab"))
    vgk = ford.find("vorgerichtliche_kosten")
    if vgk is not None:
        g.kreuz(13, 597, 73)
        g.text(13, 583, 442, _txt(vgk, "betrag"))
        lz = vgk.find("laufende_zinsen")
        if lz is not None and _txt(lz, "prozentpunkte"):
            g.kreuz(13, 490, 82)
            g.text(13, 489, 92, _txt(lz, "prozentpunkte"))
            g.text(13, 478, 99, _txt(lz, "aus"))
            g.text(13, 478, 257, _txt(lz, "ab"))
    g.kommentar("IV. Kosten der Zwangsvollstreckung (§ 788 ZPO)")
    if zvk is not None:
        g.text(13, 203, 442, _txt(zvk, "gkg_kv2111"))
        g.text(13, 190, 329, _txt(zvk, "gegenstandswert"))
        g.text(13, 177, 442, _txt(zvk, "vv3309"))
        g.text(13, 155, 442, _txt(zvk, "vv7002"))
        g.text(13, 129, 442, _txt(zvk, "umsatzsteuer_vv7008"))
        g.text(13, 117, 315, _txt(zvk, "zwischensumme_ra"))
        g.text(13, 73, 442, _txt(zvk, "summe_i_bis_iv"))

    out_pdf = f"PfÜB_{kurz}.pdf"
    body = "\n".join(g.lines)
    script = SKELETT.format(az=az, kurz=kurz, out_pdf=out_pdf, body=body)
    return az, kurz, script


SKELETT = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fall {az} – {kurz}
AUTOMATISCH GENERIERT aus XML durch xml_zu_fall.py. Nicht von Hand bearbeiten;
stattdessen die XML anpassen und neu generieren.

Ausführen (von überall, das Skript löst seine Pfade selbst auf):
    python3 data/fall_{az}_{kurz}.py
"""
import os
import sys

# Das Fallskript liegt in data/, die Engine in script/ -> Pfade selbst auflösen.
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "script"))
from pfueb_fill import PfuebFormular

TEMPLATE = os.path.join(BASE, "template", "PfÜB.pdf")
OUT = os.path.join(BASE, "data", "Outbox", "{out_pdf}")

f = PfuebFormular(TEMPLATE)

{body}

f.speichern(OUT)
print("Erstellt:", OUT)
'''


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    xml_path = sys.argv[1]
    az, kurz, script = generate(xml_path)
    if len(sys.argv) >= 3:
        out = sys.argv[2]
    else:
        out = os.path.join(os.path.dirname(os.path.abspath(xml_path)),
                           f"fall_{az}_{kurz}.py")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(script)
    print("Generiert:", out)


if __name__ == "__main__":
    main()
