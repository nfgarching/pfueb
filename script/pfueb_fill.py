#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wiederverwendbare Engine zum Befüllen des amtlichen Formulars
"Antrag auf Erlass eines Pfändungsbeschlusses und eines Pfändungs- und
Überweisungsbeschlusses" (BMJ-Zwangsvollstreckungsformular, 13 Seiten).

Diese Datei enthält KEINE Falldaten. Die Daten werden fallweise in einem
eigenen Skript eingetragen (siehe fall_VORLAGE.py) und über die hier
definierten Methoden gesetzt.

Adressierung der Felder
-----------------------
Die Feldnamen des Formulars sind generisch ("Textfeld 340", "Kontrollkästchen
365") und teils mehrfach vergeben. Ein Feld wird deshalb NICHT über seinen
Namen, sondern über seine Position adressiert:

    (Seite, y, x)

- Seite : 1-basierte Seitenzahl der PDF (1..13)
- y, x  : auf ganze Punkte gerundete untere-linke Ecke des Feldes
          (PDF-Koordinaten, Ursprung unten links)

Die Positionen ermittelt man einmalig mit:

    python3 script/pfueb_fill.py --felder template/PfÜB.pdf

Das gibt für jede Seite alle Felder mit (y, x), Typ und Beschriftung aus.

Kollisionsfelder
----------------
Die Forderungsaufstellung (Seiten 12/13) wurde im Originaltemplate unter
Wiederverwendung derselben Feldnamen eingebettet. Dadurch teilen sich z. B.
der Schuldnername (S. 4) und ein Zinsdatum (S. 12) EIN Feldobjekt und damit
denselben Wert. Die Engine spaltet solche Felder vor dem Befüllen automatisch
in eigenständige Felder auf (_split_collisions), sodass jede Position
unabhängig gefüllt werden kann.

Abhängigkeiten
--------------
- pypdf       (Pflicht)
- reportlab   (nur nötig, wenn stempel() verwendet wird, z. B. für die
              Dokumenttyp-Auswahl "Pfändungs- und Überweisungsbeschluss",
              die im Template kein ausfüllbares Feld ist)
"""

import sys
import pypdf
from pypdf.generic import NameObject, TextStringObject, ArrayObject

ON = NameObject("/Ja")   # "An"-Zustand aller Kontrollkästchen dieses Formulars


class PfuebFormular:
    def __init__(self, template_pdf):
        self.w = pypdf.PdfWriter(clone_from=template_pdf)
        self.acro = self.w._root_object["/AcroForm"]
        self._split_collisions()
        self._index_widgets()
        self._text = {}      # Seite -> {Feldname: Wert}
        self._stamps = []    # (seitenindex0, x, y, text, size)

    # ----- Aufbau -----------------------------------------------------------
    def _split_collisions(self):
        """Felder mit mehreren Widgets in eigenständige Felder aufspalten."""
        fields = self.acro["/Fields"]
        neu, drop = [], set()
        for ref in list(fields):
            f = ref.get_object()
            kids = f.get("/Kids")
            if kids and len(kids) > 1:
                base = str(f.get("/T"))
                attrs = {"/FT": f.get("/FT"), "/DA": f.get("/DA"),
                         "/Ff": f.get("/Ff"), "/Q": f.get("/Q"),
                         "/MaxLen": f.get("/MaxLen")}
                for i, k in enumerate(kids):
                    kw = k.get_object()
                    kw[NameObject("/T")] = TextStringObject(f"{base}__{i}")
                    for key, val in attrs.items():
                        if val is not None:
                            kw[NameObject(key)] = val
                    if "/Parent" in kw:
                        del kw[NameObject("/Parent")]
                    neu.append(k)
                drop.add(ref.idnum)
        self.acro[NameObject("/Fields")] = ArrayObject(
            [r for r in fields if r.idnum not in drop] + neu)

    def _index_widgets(self):
        """Lookup (Seite, y, x) -> Widget-Objekt aufbauen."""
        self._look = {}
        for pi, page in enumerate(self.w.pages):
            for a in (page.get("/Annots") or []):
                o = a.get_object()
                if o.get("/Subtype") != "/Widget":
                    continue
                r = o.get("/Rect")
                self._look[(pi + 1, int(float(r[1])), int(float(r[0])))] = o

    def _field_at(self, page, y, x):
        if (page, y, x) not in self._look:
            raise KeyError(f"Kein Feld bei (Seite={page}, y={y}, x={x}). "
                           f"Position mit --felder prüfen.")
        o = self._look[(page, y, x)]
        cur = o
        while cur.get("/T") is None and cur.get("/Parent") is not None:
            cur = cur["/Parent"].get_object()
        return str(cur.get("/T")), o

    # ----- Öffentliche API --------------------------------------------------
    def text(self, page, y, x, value):
        """Textfeld an Position (Seite, y, x) setzen.
        Zeilenumbruch in mehrzeiligen Feldern mit '\\n'."""
        name, _ = self._field_at(page, y, x)
        self._text.setdefault(page, {})[name] = value

    def kreuz(self, page, y, x):
        """Kontrollkästchen an Position (Seite, y, x) ankreuzen."""
        _, o = self._field_at(page, y, x)
        fld = o
        while fld.get("/FT") is None and fld.get("/Parent") is not None:
            fld = fld["/Parent"].get_object()
        fld[NameObject("/V")] = ON
        o[NameObject("/AS")] = ON

    def stempel(self, page, x, y, text="X", size=9):
        """Freien Text/Markierung auf eine Seite stempeln (nicht-Feld-Inhalte,
        z. B. die Dokumenttyp-Auswahl auf S. 5). page ist 1-basiert."""
        self._stamps.append((page - 1, x, y, text, size))

    def speichern(self, out_pdf):
        # 1) Text-Appearances erzeugen (rendert in allen Viewern)
        for pi, page in enumerate(self.w.pages):
            d = self._text.get(pi + 1)
            if d:
                self.w.update_page_form_field_values(page, d, auto_regenerate=False)
        if "/NeedAppearances" in self.acro:
            del self.acro[NameObject("/NeedAppearances")]
        # 2) Stempel als Overlay aufbringen
        if self._stamps:
            from reportlab.pdfgen import canvas
            import io
            for pidx, x, y, txt, size in self._stamps:
                buf = io.BytesIO()
                box = self.w.pages[pidx].mediabox
                c = canvas.Canvas(buf, pagesize=(float(box.width), float(box.height)))
                c.setFont("Helvetica-Bold", size)
                c.drawString(x, y, txt)
                c.showPage()
                c.save()
                buf.seek(0)
                self.w.pages[pidx].merge_page(pypdf.PdfReader(buf).pages[0])
        # 3) Schreiben
        with open(out_pdf, "wb") as fh:
            self.w.write(fh)


def feldkarte(template_pdf):
    """Alle Formularfelder mit (Seite, y, x), Typ und Beschriftung ausgeben."""
    r = pypdf.PdfReader(template_pdf)
    rows = []
    for pi, page in enumerate(r.pages):
        for a in (page.get("/Annots") or []):
            o = a.get_object()
            if o.get("/Subtype") != "/Widget":
                continue
            par = o.get("/Parent")
            ft = o.get("/FT") or (par.get_object().get("/FT") if par else None)
            tu = o.get("/TU") or (par.get_object().get("/TU") if par else "")
            rect = o.get("/Rect")
            rows.append((pi + 1, int(float(rect[1])), int(float(rect[0])),
                         "Kreuz" if str(ft) == "/Btn" else "Text", str(tu)))
    rows.sort(key=lambda t: (t[0], -t[1], t[2]))
    for pg, y, x, typ, tu in rows:
        print(f"S{pg:>2} y{y:>3} x{x:>3} {typ:<5} {tu}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--felder":
        feldkarte(sys.argv[2])
    else:
        print("Verwendung:\n"
              "  python3 pfueb_fill.py --felder <Template.pdf>   # Feldpositionen anzeigen\n"
              "  (zum Befüllen ein Fallskript verwenden, siehe fall_VORLAGE.py)")
