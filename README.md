# PfÜB-Generator – Kontopfändung

KI-gestützter Workflow zum Erstellen eines **Pfändungs- und Überweisungs­beschlusses
(PfÜB)** für eine **Kontopfändung**. Aus den Falldaten wird das amtliche
Zwangsvollstreckungs­formular des BMJ (13 Seiten, ausfüllbares PDF) befüllt.

Der Kern ist eine kleine Python-Pipeline: Falldaten werden in einer **XML-Datei**
erfasst, daraus wird ein **Fallskript** generiert, das das amtliche PDF mit einer
wiederverwendbaren **Engine** positionsgenau ausfüllt.

> **Arbeitssprache Deutsch.** Beträge deutsch formatiert (`1.234,56 €`).
> Bei Unklarheit nicht raten, sondern nachfragen.

---

## Verzeichnisse

```
.
├── template/           Vorlagen (im Repo, nicht fallspezifisch)
│   ├── PfÜB.pdf            amtliches Formular (ausfüllbares AcroForm)
│   └── falldaten.xml       XML-Vorlage zum Erfassen eines Falls
├── script/             Programmcode (im Repo)
│   ├── pfueb_fill.py       Engine: füllt das PDF über Feldpositionen
│   └── xml_zu_fall.py      Generator: XML → Fallskript
├── data/               Mandantendaten – per .gitignore geschützt *
│   ├── Inbox/              Eingang: Titel & Vollstreckungsunterlagen
│   │   ├── Titel/
│   │   └── Vollstreckungsunterlagen/
│   └── Outbox/            fertige PfÜB-PDFs
├── docs/
│   ├── PROMPT.md           Erhebungsauftrag (Datensammlung)
│   └── ENTWICKLUNG.md      Entwicklerdokumentation
├── CLAUDE.md           Hinweise für die Arbeit mit Claude Code
└── README.md
```

\* Der Inhalt von `data/` wird **nicht** veröffentlicht (siehe
[Datenschutz](#datenschutz)). Nur die leere Ordnerstruktur ist im Repo.

---

## Voraussetzungen

```bash
pip install pypdf reportlab
```

`pypdf` ist Pflicht, `reportlab` wird nur für die gestempelte Dokumenttyp-Auswahl
auf Seite 5 benötigt.

---

## Workflow

```bash
# 1) Falldaten-Vorlage kopieren und - ggf. mit KI die falldaten.xml z.B. aus Vollstreckungsbescheid - befüllen. Drittschuldner nicht vergessen!)
cp template/falldaten.xml data/fall_<AZ>_<Kurzname>.xml
#    z. B. data/fall_06629_R-R-Immobilien.xml  – Platzhalter [ ... ] ersetzen

# 2) Fallskript aus der XML generieren
python3 script/xml_zu_fall.py data/fall_<AZ>_<Kurzname>.xml
#    -> data/fall_<AZ>_<Kurzname>.py

# 3) Fallskript ausführen -> fertiges PDF
python3 data/fall_<AZ>_<Kurzname>.py
#    -> data/Outbox/PfÜB_<Kurzname>.pdf
```

Das generierte Fallskript **nicht von Hand bearbeiten** – stattdessen die XML
anpassen und neu generieren. Das Mapping „semantisches XML-Element →
Formularposition“ liegt fest im Generator.

Die Formularfelder samt Positionen lassen sich auflisten mit:

```bash
python3 script/pfueb_fill.py --felder template/PfÜB.pdf
```

---

## So funktioniert die Befüllung (Kurzfassung)

- Die Feldnamen des Formulars sind generisch und teils mehrfach vergeben; Felder
  werden deshalb über ihre **Position `(Seite, y, x)`** adressiert.
- Die Forderungsaufstellung (S. 12/13) teilt sich im Original Feldobjekte mit dem
  Hauptformular; die Engine spaltet diese **Kollisionsfelder** automatisch auf.
- Für Textfelder werden eigene Appearance-Streams erzeugt, damit der Inhalt in
  allen Viewern (Acrobat, beA, Poppler, Chrome) erscheint.
- Die Dokumenttyp-Auswahl auf S. 5 ist kein Formularfeld und wird als Overlay
  gestempelt (`reportlab`).

Details, Datenmodell und Erweiterung siehe **[docs/ENTWICKLUNG.md](docs/ENTWICKLUNG.md)**.

---

## Stand und Grenzen

- Abgedeckt ist der **Standardfall**: 1 Gläubiger, 1 Schuldner, 1 Drittschuldner-
  Bank, 1 Hauptforderung. Mehrere Beteiligte, weitere Titel oder zusätzliche
  Zinsstaffeln sind im Generator noch nicht abgebildet (siehe
  [docs/ENTWICKLUNG.md](docs/ENTWICKLUNG.md)).
- Einreichungsabhängige Angaben (Zahlungsweise, Vollmacht/Versicherung
  § 753a bzw. § 829a ZPO, beA-Versandart) und HRB-Registerdaten sind im Formular
  bewusst offen gelassen.
- Die ZV-Kosten (§ 788 ZPO) werden **nicht** automatisch berechnet, sondern aus
  der XML übernommen; die Rechenregeln stehen als Kommentar in
  `template/falldaten.xml`.

---

## Datenschutz

Dieser Workflow verarbeitet personenbezogene Mandantendaten. Damit beim
Veröffentlichen nichts durchsickert:

- Alles unter `data/` ist per [`.gitignore`](.gitignore) vom Repo ausgenommen –
  Titel, Falldaten-XML, generierte Fallskripte und fertige PfÜB-PDFs.
- Im Repo verbleibt nur die **leere Ordnerstruktur** (über `.gitkeep`-Dateien),
  damit der Workflow nach dem Klonen sofort die erwarteten Pfade vorfindet.

> Vor dem ersten Push prüfen, dass keine Falldaten getrackt werden:
> `git status` darf unter `data/` nur `.gitkeep`-Dateien zeigen.

---

## Rechtlicher Hinweis

Kein Rechtsrat. Die Vollstreckbarkeit (z. B. bei eingelegtem Einspruch gegen den
Vollstreckungs­bescheid) und die Vollständigkeit der Angaben sind im Einzelfall
juristisch zu prüfen. Das amtliche Formular (`template/PfÜB.pdf`) ist eine
Veröffentlichung des Bundesministeriums der Justiz.
