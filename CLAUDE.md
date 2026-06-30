# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Projektkontext

Dies ist **kein Software-Projekt**, sondern ein juristischer Dokumenten-Arbeitsbereich. Aufgabe: Aus den Falldaten einen **Pfändungs- und Überweisungsbeschluss (PfÜB)** für eine **Kontopfändung** erstellen, indem das amtliche Zwangsvollstreckungsformular befüllt wird.

Es gibt keine Build-, Lint- oder Testbefehle. Der „Workflow" ist Datenextraktion → Formular-Modul-Zuordnung → Ausgabe.

## Arbeitskonventionen (verbindlich)

- **Sprache:** Deutsch.
- **Beträge:** deutsche Formatierung (`1.234,56 €`).
- **Bei Unklarheit: nicht raten – nachfragen.** Die Falldaten enthalten ausdrücklich gekennzeichnete offene Fragen (s. u.), die vor der Erstellung zu klären sind.
- **Ergebnisse** in `data/Outbox/` ablegen.
- **Datenschutz:** Alles unter `data/` ist personenbezogen und per `.gitignore` vom Repo ausgenommen (nur die leere Ordnerstruktur via `.gitkeep` ist eingecheckt). Niemals Mandantendaten außerhalb von `data/` ablegen.

## Dateien & Datenfluss

| Datei | Rolle |
|---|---|
| `data/fall_<az>_<kurz>.xml` | **Datenquelle eines Falls.** Beteiligte, Titel, Forderungsaufstellung, offene Fragen. Aus `template/falldaten.xml` kopiert. |
| `docs/PROMPT.md` | Ursprünglicher Erhebungsauftrag (Gliederung der Datensammlung); historischer Kontext. |
| `docs/ENTWICKLUNG.md` | Entwicklerdokumentation (Architektur, Engine, Generator, XML-Modell). |
| `template/PfÜB.pdf` | Amtliches Formular „Antrag auf Erlass eines Pfändungsbeschlusses und eines Pfändungs- und Überweisungsbeschlusses" (13 Seiten). |
| `template/falldaten.xml` | Kommentierte XML-Vorlage für die Falldaten. |
| `script/` | Automatisierung: Generator (`xml_zu_fall.py`) + Engine (`pfueb_fill.py`). |
| `data/Inbox/` | Eingang: Titel (`Titel/`) und Vollstreckungsunterlagen. |
| `data/Outbox/` | Zielverzeichnis für das fertige Dokument. |

## Automatisierter Befüll-Weg (`script/`)

Pipeline (Details in `docs/ENTWICKLUNG.md`):

1. `template/falldaten.xml` nach `data/fall_<AZ>_<Kurzname>.xml` kopieren und mit den Falldaten füllen (semantische Felder, keine Koordinaten).
2. `python3 script/xml_zu_fall.py data/fall_<AZ>_<Kurzname>.xml` → erzeugt `data/fall_<AZ>_<Kurzname>.py`.
3. `python3 data/fall_<AZ>_<Kurzname>.py` → `data/Outbox/PfÜB_<Kurzname>.pdf`.

Engine `pfueb_fill.py` adressiert Felder über die Position `(Seite, y, x)` (die generischen Feldnamen sind mehrfach vergeben) und spaltet die Kollisionsfelder der Forderungsaufstellung (S. 12/13) automatisch auf. Das Mapping „XML-Element → Position" liegt fest in `xml_zu_fall.py`. **Generierte `fall_*.py` nicht von Hand bearbeiten** – stattdessen XML anpassen und neu generieren.

### Offene Erweiterung (bei Gelegenheit)

XML-Vorlage und Generator decken bislang nur den **Standardfall** ab: **1 Gläubiger, 1 Schuldner, 1 Drittschuldner-Bank, 1 Hauptforderung**. Noch **nicht** abgebildet und bei Bedarf in `xml_zu_fall.py` (und der XML-Vorlage) zu ergänzen:

- mehrere Gläubiger / Schuldner / Drittschuldner,
- weitere Vollstreckungstitel,
- zusätzliche Zinsstaffeln und Säumniszuschläge in der Forderungsaufstellung.

## Aufbau des amtlichen Formulars (`template/PfÜB.pdf`)

Das Formular ist **modular** (Buchstaben am linken Rand). Für eine Kontopfändung relevant sind A–D und insbesondere **H**:

- **Antragsseite (S. 1–2):** Antragsgericht, Schuldnerangaben, Kontaktdaten des Antragstellers (Gläubiger / gesetzl. Vertreter / Bevollmächtigter), Zusatzanträge (Ausfertigung, Zustellung durch Geschäftsstelle, Aufforderung Drittschuldner nach § 840 Abs. 1 ZPO), beizufügende Anlagen, Versicherungen (u. a. § 829a ZPO bei elektronischer Übermittlung).
- **Modul A** – Gläubiger inkl. Bevollmächtigtem und **Bankverbindung des Gläubigers/Bevollmächtigten** (für Zahlungseingang).
- **Modul B** – Schuldner inkl. gesetzlichem Vertreter (bei GmbH: Geschäftsführer).
- **Modul C** – Vollstreckungstitel (Art, Aussteller, Datum, Geschäftszeichen).
- **Modul D** – Drittschuldner (bei Kontopfändung: die **Bank**).
- **Modul E** Arbeitgeber · **F** Agentur für Arbeit/Versicherungsträger · **G** Finanzamt · **H** Kreditinstitute · **I** Bausparkassen.
- **Modul H (Kreditinstitute)** ist der **Kern der Kontopfändung**: Pfändung der Guthaben sämtlicher Zahlungskonten, Auszahlungsansprüche, Sparguthaben/Festgeld, „offene Kreditlinie"/Dispokredit, ggf. Schließfach/Depot.

## Fallspezifische offene Punkte (vor Erstellung klären)

Die Falldaten-XML markiert mit ⚠️ ungeklärte Fragen, die die Erstellung blockieren – **nicht eigenmächtig entscheiden**:

1. **Geburtsdatum** des Geschäftsführers des Schuldners (Modul B verlangt ggf. Geburtsdatum/-ort).
2. **Zuordnung der IBAN/des Kontos** zum Schuldner – aus dem Titel selbst nicht ersichtlich; Zustellanschrift der Drittschuldner-Bank ist zu verifizieren.
3. **Eingelegter Einspruch** gegen den Vollstreckungsbescheid – kann die Vollstreckbarkeit berühren; rechtlich prüfen lassen.

## Forderungsberechnung

Die Forderungsaufstellung in der Falldaten-XML ist in Haupt-, Verfahrens-, Neben- und Zinsforderung gegliedert (Gesamtsumme laut Titel **2.876,45 €**) zuzüglich **laufender, noch nicht ausgerechneter Zinsen** mit unterschiedlichen Sätzen und Anfangsdaten. Diese Zinsstaffeln beim Befüllen der Forderungsaufstellung exakt übernehmen (Satz, Bezugsbetrag, Beginn) und nicht zusammenfassen.
