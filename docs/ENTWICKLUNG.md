# Entwicklerdokumentation

Technische Dokumentation der PfÜB-Pipeline. Für den Anwender-Workflow siehe
[../README.md](../README.md).

## Inhalt

- [Architektur](#architektur)
- [Datenfluss](#datenfluss)
- [Engine: `pfueb_fill.py`](#engine-pfueb_fillpy)
- [Generator: `xml_zu_fall.py`](#generator-xml_zu_fallpy)
- [Das XML-Datenmodell](#das-xml-datenmodell)
- [Feldadressierung über Positionen](#feldadressierung-über-positionen)
- [Besonderheiten des Templates](#besonderheiten-des-templates)
- [Einen neuen Fall anlegen](#einen-neuen-fall-anlegen)
- [Das Formular erweitern](#das-formular-erweitern)
- [Fehlerbehebung](#fehlerbehebung)

---

## Architektur

Drei Schichten, klar getrennt nach „Code“ und „Daten“:

| Schicht | Datei | Enthält | Im Repo? |
|---|---|---|---|
| **Engine** | `script/pfueb_fill.py` | Wiederverwendbare Logik, PDF-Manipulation. **Keine** Falldaten. | ja |
| **Generator** | `script/xml_zu_fall.py` | Mapping „XML-Element → Formularposition“. **Keine** Falldaten. | ja |
| **Fall** | `data/fall_<az>_<kurz>.{xml,py}` | Konkrete Mandantendaten. | **nein** (.gitignore) |

Die Trennung ist bewusst: Engine und Generator beschreiben das *Formular* (für
alle Fälle gleich) und werden veröffentlicht; die Falldaten liegen in `data/`
und bleiben privat.

## Datenfluss

```
template/falldaten.xml          (Vorlage, kopieren)
        │  cp
        ▼
data/fall_<az>_<kurz>.xml       (vom Anwender/Chatbot befüllt)
        │  python3 script/xml_zu_fall.py …
        ▼
data/fall_<az>_<kurz>.py        (GENERIERT – nicht von Hand bearbeiten)
        │  python3 data/fall_<az>_<kurz>.py
        │  nutzt script/pfueb_fill.py + template/PfÜB.pdf
        ▼
data/Outbox/PfÜB_<kurz>.pdf     (Ergebnis)
```

Das Fallskript ist bewusst ein eigenständiges, lesbares Python-Skript (eine
Folge von `f.text(...)`/`f.kreuz(...)`-Aufrufen). So bleibt jederzeit
nachvollziehbar und prüfbar, welcher Wert an welche Stelle des Formulars
geschrieben wird.

## Engine: `pfueb_fill.py`

Klasse `PfuebFormular` kapselt das Laden, Aufbereiten und Schreiben des PDF
(über [`pypdf`](https://pypdf.readthedocs.io/)).

Öffentliche API:

```python
f = PfuebFormular(template_pdf)     # lädt Template, bereitet Formular auf
f.text(page, y, x, value)           # Textfeld an Position (Seite, y, x) setzen
f.kreuz(page, y, x)                 # Kontrollkästchen ankreuzen
f.stempel(page, x, y, text="X")     # freien Text als Overlay aufbringen (reportlab)
f.speichern(out_pdf)                # Appearances erzeugen, Stempel mergen, schreiben
```

Ablauf intern:

1. **`__init__`** klont das Template in einen `PdfWriter`, ruft
   `_split_collisions()` und `_index_widgets()` auf.
2. **`_split_collisions()`** spaltet Felder mit mehreren Widgets (`/Kids`) in
   eigenständige Felder auf – siehe [Kollisionsfelder](#kollisionsfelder).
3. **`_index_widgets()`** baut den Lookup `(Seite, y, x) → Widget` auf, indem es
   über alle Seiten-Annotationen vom Typ `/Widget` iteriert und deren `/Rect`
   (untere-linke Ecke, auf ganze Punkte gerundet) als Schlüssel verwendet.
4. **`text()`/`kreuz()`** schlagen das Widget über `_field_at()` nach und merken
   sich Wert bzw. Kreuz-Zustand. `kreuz()` setzt `/V` und `/AS` auf `/Ja`
   (der „An“-Zustand aller Kästchen dieses Formulars).
5. **`speichern()`** erzeugt mit `update_page_form_field_values(...,
   auto_regenerate=False)` eigene Appearance-Streams, entfernt
   `/NeedAppearances` und legt die Stempel als gemergte Overlay-Seiten an.

Feldkarte ausgeben (kein Befüllen):

```bash
python3 script/pfueb_fill.py --felder template/PfÜB.pdf
# Ausgabe je Feld:  S 1 y423 x 70 Text  Name/Firma
```

## Generator: `xml_zu_fall.py`

Liest die Falldaten-XML und schreibt ein Fallskript. Das **Mapping** „semantisches
XML-Element → Formularposition `(Seite, y, x)`“ ist hier fest hinterlegt
(Funktion `generate()`); es beschreibt das Formular und ist für alle Fälle gleich.

Bausteine:

- **`Gen`** – sammelt die zu erzeugenden Zeilen. `text()` lässt leere Werte
  bewusst weg (kein leeres Feld im Formular), `kreuz()`/`stempel()`/`kommentar()`
  schreiben die jeweiligen Aufrufe.
- **`_txt(node, pfad, default)`** / **`_bool(...)`** – robuste Lesehelfer für
  XML-Knoten (fehlende Elemente → Default bzw. `False`).
- **`ANGABEN_BOX` + `typ_kreuz()`** – Position der Anrede-/Typ-Kästchen
  (`herr`/`frau`/`unternehmen`) je „Angaben zu …“-Block.
- **`SKELETT`** – das Python-Grundgerüst des Fallskripts (Pfad-Auflösung,
  Import der Engine, Platzhalter `{body}`).

Aufruf:

```bash
python3 script/xml_zu_fall.py data/fall_<az>_<kurz>.xml [zielpfad.py]
```

Ohne Zielpfad wird neben die XML geschrieben (`fall_<az>_<kurz>.py`), abgeleitet
aus den Attributen `aktenzeichen` und `kurzname` des `<fall>`-Elements.

## Das XML-Datenmodell

`template/falldaten.xml` ist die kommentierte Vorlage. Wurzel `<pfueb>` mit den
Blöcken:

| Element | Inhalt |
|---|---|
| `<fall aktenzeichen="…" kurzname="…"/>` | bestimmt Dateinamen + Ausgabe |
| `<antrag>` | Ort/Datum, Zusatzanträge (Ausfertigung, Zustellung, § 840, Einziehung) |
| `<gericht>` | Antragsgericht |
| `<glaeubiger ziffer="1">` | Gläubiger inkl. `<gesetzlicher_vertreter>` |
| `<bevollmaechtigter bezeichnung="…">` | RA/StB inkl. `<bankverbindung>` |
| `<schuldner ziffer="1">` | Schuldner inkl. `<gesetzlicher_vertreter>` |
| `<vollstreckungstitel ziffer="1">` | Art, Aussteller, Datum, Az |
| `<drittschuldner ziffer="1">` | Bank, `<modul>` (H), `<schuldner_konto_iban>` |
| `<forderung>` | `hauptforderung`, `mahnverfahrenskosten`, `vorgerichtliche_kosten` – je optional `<laufende_zinsen>` |
| `<zwangsvollstreckungskosten>` | Abschnitt IV (§ 788 ZPO) |

Konventionen (siehe Kommentare in der Vorlage):

- Beträge deutsch ohne Währungszeichen: `1.234,56`
- Datum: `TT.MM.JJJJ`
- Wahrheitswerte: `true` / `false`
- `typ`: `unternehmen` | `herr` | `frau` (für „Angaben zu …“)
- `anrede`: `herr` | `frau` (für gesetzliche Vertreter)
- Leere/weggelassene Elemente werden im Formular **nicht** gefüllt.

Die ZV-Kosten werden **nicht** gerechnet, sondern aus der XML übernommen; die
Rechenregeln (GKG KV 2111, VV 3309/7002/7008, Zwischensumme, Summe I–IV) stehen
als Kommentar in der Vorlage.

## Feldadressierung über Positionen

Die Feldnamen des Formulars sind generisch (`Textfeld 340`) und teils mehrfach
vergeben. Ein Feld wird deshalb über seine **Position** angesprochen:

- `Seite` – 1-basierte Seitenzahl (1–13)
- `y`, `x` – auf ganze Punkte gerundete **untere-linke Ecke** des Feldes
  (PDF-Koordinaten, Ursprung unten links)

Diese Positionen beschreiben das *Formular* und sind für jeden Fall gleich – für
einen neuen Fall ändern sich nur die **Werte**. Positionen ermittelt man mit
`pfueb_fill.py --felder` (siehe oben); aus `S 1 y423 x 70 Text  Name/Firma` wird
z. B. `f.text(1, 423, 70, "R & R Immobilien GmbH")`.

## Besonderheiten des Templates

### Kollisionsfelder

Die Forderungsaufstellung (S. 12/13) wurde im Originaltemplate unter
Wiederverwendung derselben Feldnamen eingebettet. Dadurch teilen sich z. B. der
Schuldnername (S. 4) und ein Zinsdatum (S. 12) **ein** Feldobjekt – und damit
denselben Wert. `_split_collisions()` trennt solche Felder beim Laden in
eigenständige Felder auf, sodass jede Position unabhängig gefüllt werden kann.

### Dokumenttyp-Auswahl (S. 5)

Die Auswahl „☐ Pfändungs- und Überweisungsbeschluss / ☐ Pfändungsbeschluss“ ist
**kein** Formularfeld, sondern wird per `f.stempel(...)` als Overlay gesetzt
(benötigt `reportlab`).

### Rendering in allen Viewern

Für Textfelder werden eigene Appearance-Streams erzeugt
(`auto_regenerate=False`), `/NeedAppearances` wird entfernt. So erscheint der
Inhalt in Acrobat, beA, Poppler und Chrome, ohne auf die Regenerierung durch den
Viewer angewiesen zu sein.

### Modulübersicht (für die Adressierung)

| Seite | Inhalt |
|---|---|
| 1 | Antrag, Gericht, Schuldnerangaben, Antragsteller, Zusatzanträge |
| 2 | PKH/Anlagen/Versicherungen, Namen der Antragsteller |
| 3–4 | **Modul A** Gläubiger + Vertreter + Bankverbindung |
| 4–5 | **Modul B** Schuldner + Vertreter |
| 5 | **Modul C** Vollstreckungstitel; Dokumenttyp-Auswahl |
| 6 | **Modul D** Drittschuldner (Bank), Modulverweis |
| 7 | Module E–I (E Arbeitgeber, F Sozialleistungen, G Finanzamt, **H Kreditinstitute**, I Bausparkassen) |
| 8 | Überweisung (Einziehung / an Zahlungs statt) |
| 9–11 | Anordnungen bei natürlichen Personen (P-Konto, Unterhalt) – bei GmbH leer |
| 12–13 | **Forderungs- und Kostenaufstellung** (I. Hauptforderung, III. titulierte Kosten, IV. ZV-Kosten § 788 ZPO) |

## Einen neuen Fall anlegen

Der Regelweg läuft komplett über die XML – kein Python-Wissen nötig:

```bash
cp template/falldaten.xml data/fall_<AZ>_<Kurzname>.xml   # befüllen
python3 script/xml_zu_fall.py data/fall_<AZ>_<Kurzname>.xml
python3 data/fall_<AZ>_<Kurzname>.py
```

Das generierte Fallskript ist Wegwerf-Output – **nicht** von Hand ändern.
Anpassungen gehen in die XML, danach neu generieren.

## Das Formular erweitern

Abgedeckt ist der **Standardfall**: 1 Gläubiger, 1 Schuldner, 1 Drittschuldner-
Bank, 1 Hauptforderung. Noch **nicht** abgebildet:

- mehrere Gläubiger / Schuldner / Drittschuldner,
- weitere Vollstreckungstitel,
- zusätzliche Zinsstaffeln und Säumniszuschläge in der Forderungsaufstellung.

Vorgehen für ein neues/zusätzliches Feld:

1. Position ermitteln: `python3 script/pfueb_fill.py --felder template/PfÜB.pdf`.
2. In `xml_zu_fall.py` in `generate()` das passende `g.text(...)`/`g.kreuz(...)`
   mit dieser Position ergänzen (ggf. neues XML-Element einlesen via `_txt`).
3. Bei neuen Eingabefeldern auch `template/falldaten.xml` um das Element +
   Kommentar erweitern.
4. Neu generieren und PDF visuell prüfen.

**Nicht** das generierte Fallskript patchen – es wird beim nächsten Lauf
überschrieben. Die Engine (`pfueb_fill.py`) bleibt dabei i. d. R. unberührt; sie
ist formularunabhängig.

## Fehlerbehebung

| Symptom | Ursache / Lösung |
|---|---|
| `ModuleNotFoundError: No module named 'pfueb_fill'` | Fallskript außerhalb der Struktur ausgeführt oder Pfade verschoben. Das Skript ergänzt `script/` selbst über `sys.path`; Verzeichnislayout (`data/…`, `script/…`) muss stimmen. |
| `KeyError: Kein Feld bei (Seite=…, y=…, x=…)` | Position falsch. Mit `--felder` die korrekten `(Seite, y, x)` nachschlagen. |
| `Font dictionary for /Arial-BoldMT not found.` | **Unkritisch.** pypdf weicht für die zwei fettgedruckten Summenfelder auf eine Standardschrift aus; der Inhalt wird korrekt dargestellt. |
| Feldinhalt erscheint nur in einem Viewer | Tritt bei `NeedAppearances`-Abhängigkeit auf – wird durch die selbst erzeugten Appearance-Streams in `speichern()` vermieden. |
| Langer Text wird abgeschnitten | Es gibt **keinen** automatischen Zeilenumbruch. Lange Texte selbst mit `\n` umbrechen. |
```
