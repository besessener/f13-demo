#!/usr/bin/env python3
"""PDF-Erzeugung für die Demo-Wissensbasis (LPA Kanto).

Wandelt jede Datei ``demo-data/rag/0*.md`` in ein gesetztes A4-PDF mit gleichem
Basisnamen um (z. B. ``01_vwv_pokehaltung.md`` -> ``01_vwv_pokehaltung.pdf``) und
kopiert das PDF von Dokument 1 nach ``demo-data/summary/vwv_pokehaltung.pdf``.

Wichtig:
- Dieses Skript führt die Maintainerin bzw. der Maintainer einmalig auf dem eigenen
  Rechner aus, wenn sich die Markdown-Texte ändern. Es ist NICHT Teil des
  Compose-Stacks und läuft auch nicht im Werkzeug-Container (dort gibt es nur die
  Standardbibliothek). Die erzeugten PDFs liegen fertig im Repo.
- Benötigt reportlab:  pip install reportlab
- Aufruf:              python3 werkzeuge/pdf_erzeugen.py

Unterstütztes Markdown (bewusst einfach): Überschriften (#, ##, ###), Absätze,
Aufzählungen (- oder *), nummerierte Absätze, **fett**, *kursiv*, `Code` und
einfache Tabellen mit | ... |. Die Aufzählung direkt unter der Hauptüberschrift
wird als Kopfdaten-Kasten gesetzt (Behörde, Aktenzeichen, Stand, Hinweis).

Schrift: Helvetica (PDF-Standardschrift, WinAnsi-Kodierung). Damit funktionieren
ä, ö, ü, ß, é, „ “, – und §. Zeichen außerhalb von WinAnsi (cp1252) werden vorab
gemeldet, weil sie im PDF als Kästchen erscheinen würden.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

try:
    from reportlab import rl_config
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        KeepTogether,
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError:
    sys.exit("Fehler: reportlab fehlt. Bitte zuerst installieren: pip install reportlab")

# Reproduzierbare PDFs (kein Zeitstempel, feste Dokument-ID): unveränderter Text
# ergibt eine byte-gleiche Datei und damit keinen unnötigen Git-Diff.
rl_config.invariant = 1

REPO = Path(__file__).resolve().parent.parent
RAG_DIR = REPO / "demo-data" / "rag"
SUMMARY_PDF = REPO / "demo-data" / "summary" / "vwv_pokehaltung.pdf"

FUSSZEILE = "Fiktives Dokument – nur für interne Demonstrationszwecke · Seite {seite}"
AUTOR = "Landesamt für Pokémon-Angelegenheiten Kanto (fiktiv)"

# Farben: zurückhaltend, behördlich
DUNKELBLAU = colors.HexColor("#1F3A5F")
GRAU_TEXT = colors.HexColor("#555555")
GRAU_LINIE = colors.HexColor("#B8C2CC")
KASTEN = colors.HexColor("#EEF2F6")
TABELLENKOPF = colors.HexColor("#DCE4EC")

# ---------------------------------------------------------------------------
# Absatzformate
# ---------------------------------------------------------------------------
STIL = {
    "h1": ParagraphStyle(
        "h1", fontName="Helvetica-Bold", fontSize=17, leading=21,
        textColor=DUNKELBLAU, spaceAfter=10, alignment=TA_LEFT,
    ),
    "h2": ParagraphStyle(
        "h2", fontName="Helvetica-Bold", fontSize=12, leading=15,
        textColor=DUNKELBLAU, spaceBefore=12, spaceAfter=5,
    ),
    "h3": ParagraphStyle(
        "h3", fontName="Helvetica-Bold", fontSize=10.5, leading=13,
        spaceBefore=8, spaceAfter=3,
    ),
    "text": ParagraphStyle(
        "text", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=6,
    ),
    "liste": ParagraphStyle(
        "liste", fontName="Helvetica", fontSize=10, leading=14,
    ),
    "zelle": ParagraphStyle(
        "zelle", fontName="Helvetica", fontSize=9.5, leading=12.5,
    ),
    "zelle_kopf": ParagraphStyle(
        "zelle_kopf", fontName="Helvetica-Bold", fontSize=9.5, leading=12.5,
    ),
    "kopf_label": ParagraphStyle(
        "kopf_label", fontName="Helvetica-Bold", fontSize=9, leading=12,
        textColor=GRAU_TEXT,
    ),
    "kopf_wert": ParagraphStyle(
        "kopf_wert", fontName="Helvetica", fontSize=9, leading=12,
    ),
}


# ---------------------------------------------------------------------------
# Inline-Formatierung
# ---------------------------------------------------------------------------
def inline(text: str) -> str:
    """Wandelt einfaches Inline-Markdown in reportlab-Markup um."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    return text


def ohne_markup(text: str) -> str:
    """Entfernt Inline-Markdown, z. B. für PDF-Metadaten."""
    return re.sub(r"[*`]", "", text).strip()


# ---------------------------------------------------------------------------
# Markdown in Blöcke zerlegen
# ---------------------------------------------------------------------------
def bloecke(markdown: str) -> list[tuple[str, object]]:
    """Zerlegt Markdown in eine Liste (art, inhalt)."""
    ergebnis: list[tuple[str, object]] = []
    absatz: list[str] = []
    liste: list[str] = []
    tabelle: list[str] = []

    def absatz_ende() -> None:
        if absatz:
            ergebnis.append(("absatz", " ".join(absatz)))
            absatz.clear()

    def liste_ende() -> None:
        if liste:
            ergebnis.append(("liste", list(liste)))
            liste.clear()

    def tabelle_ende() -> None:
        if tabelle:
            zeilen = []
            for z in tabelle:
                zellen = [c.strip() for c in z.strip().strip("|").split("|")]
                if all(re.fullmatch(r":?-{3,}:?", c) for c in zellen):
                    continue  # Trennzeile | --- | --- |
                zeilen.append(zellen)
            ergebnis.append(("tabelle", zeilen))
            tabelle.clear()

    def alles_ende() -> None:
        absatz_ende()
        liste_ende()
        tabelle_ende()

    for roh in markdown.splitlines():
        zeile = roh.rstrip()
        if not zeile.strip():
            alles_ende()
            continue
        if zeile.lstrip().startswith("|"):
            absatz_ende()
            liste_ende()
            tabelle.append(zeile)
            continue
        tabelle_ende()
        kopf = re.match(r"^(#{1,3})\s+(.*)$", zeile)
        if kopf:
            alles_ende()
            ergebnis.append((f"h{len(kopf.group(1))}", kopf.group(2).strip()))
            continue
        if re.fullmatch(r"\s*(-{3,}|\*{3,})\s*", zeile):
            alles_ende()
            ergebnis.append(("linie", None))
            continue
        punkt = re.match(r"^\s*[-*]\s+(.*)$", zeile)
        if punkt:
            absatz_ende()
            liste.append(punkt.group(1))
            continue
        if liste and roh.startswith((" ", "\t")):
            liste[-1] += " " + zeile.strip()  # Fortsetzungszeile eines Listenpunkts
            continue
        liste_ende()
        absatz.append(zeile.strip())
    alles_ende()
    return ergebnis


# ---------------------------------------------------------------------------
# Blöcke in reportlab-Flowables umsetzen
# ---------------------------------------------------------------------------
def kopfdaten_kasten(punkte: list[str], breite: float) -> Table:
    """Setzt die Kopfdaten (Behörde, Aktenzeichen, Stand, Hinweis) als Kasten."""
    daten = []
    for punkt in punkte:
        treffer = re.match(r"^\*\*(.+?):?\*\*:?\s*(.*)$", punkt)
        if treffer:
            label, wert = treffer.group(1).rstrip(":"), treffer.group(2)
        else:
            label, wert = "", punkt
        daten.append([Paragraph(inline(label), STIL["kopf_label"]),
                      Paragraph(inline(wert), STIL["kopf_wert"])])
    tab = Table(daten, colWidths=[3.2 * cm, breite - 3.2 * cm])
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), KASTEN),
        ("LINEABOVE", (0, 0), (-1, 0), 1.2, DUNKELBLAU),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, GRAU_LINIE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tab


def tabelle_setzen(zeilen: list[list[str]], breite: float) -> Table:
    spalten = max(len(z) for z in zeilen)
    zeilen = [z + [""] * (spalten - len(z)) for z in zeilen]
    daten = []
    for i, z in enumerate(zeilen):
        stil = STIL["zelle_kopf"] if i == 0 else STIL["zelle"]
        daten.append([Paragraph(inline(c), stil) for c in z])
    # Spaltenbreiten grob nach Textlänge verteilen, jede Spalte mindestens 12 %
    laengen = [max(len(z[s]) for z in zeilen) + 4 for s in range(spalten)]
    summe = sum(laengen)
    anteile = [max(l / summe, 0.12) for l in laengen]
    norm = sum(anteile)
    tab = Table(daten, colWidths=[breite * a / norm for a in anteile],
                repeatRows=1, hAlign="LEFT")
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TABELLENKOPF),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAU_LINIE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
    ]))
    return tab


def flowables(markdown: str, breite: float) -> tuple[list, str]:
    teile: list = []
    titel = ""
    vor_erstem_abschnitt = True
    ausstehende_ueberschrift = None  # h2/h3 bleibt mit dem ersten Inhalt zusammen

    def anhaengen(element) -> None:
        nonlocal ausstehende_ueberschrift
        if ausstehende_ueberschrift is not None:
            teile.append(KeepTogether([ausstehende_ueberschrift, element]))
            ausstehende_ueberschrift = None
        else:
            teile.append(element)

    for art, inhalt in bloecke(markdown):
        if art == "h1":
            titel = titel or ohne_markup(inhalt)
            teile.append(Paragraph(inline(inhalt), STIL["h1"]))
        elif art in ("h2", "h3"):
            vor_erstem_abschnitt = False
            if ausstehende_ueberschrift is not None:
                teile.append(ausstehende_ueberschrift)
            ausstehende_ueberschrift = Paragraph(inline(inhalt), STIL[art])
        elif art == "liste" and vor_erstem_abschnitt and titel:
            teile.append(kopfdaten_kasten(inhalt, breite))
            teile.append(Spacer(1, 8))
        elif art == "liste":
            punkte = [ListItem(Paragraph(inline(p), STIL["liste"]), leftIndent=14)
                      for p in inhalt]
            anhaengen(ListFlowable(punkte, bulletType="bullet", start="•",
                                   leftIndent=14, bulletFontSize=8,
                                   spaceAfter=6))
            teile.append(Spacer(1, 4))
        elif art == "tabelle":
            anhaengen(tabelle_setzen(inhalt, breite))
            teile.append(Spacer(1, 8))
        elif art == "linie":
            teile.append(Spacer(1, 6))
        else:
            anhaengen(Paragraph(inline(inhalt), STIL["text"]))
    if ausstehende_ueberschrift is not None:
        teile.append(ausstehende_ueberschrift)
    return teile, titel


# ---------------------------------------------------------------------------
# Seite, Fußzeile, PDF
# ---------------------------------------------------------------------------
def fusszeile(canvas, doc) -> None:
    canvas.saveState()
    breite, _ = A4
    canvas.setStrokeColor(GRAU_LINIE)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 1.6 * cm, breite - doc.rightMargin, 1.6 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRAU_TEXT)
    canvas.drawCentredString(breite / 2, 1.1 * cm, FUSSZEILE.format(seite=doc.page))
    canvas.restoreState()


def zeichen_pruefen(pfad: Path, text: str) -> list[str]:
    """Meldet Zeichen, die Helvetica (WinAnsi/cp1252) nicht darstellen kann."""
    fehlend = sorted({c for c in text if c not in "\n\r\t" and not _cp1252(c)})
    return [f"{pfad.name}: Zeichen {c!r} (U+{ord(c):04X}) fehlt in Helvetica" for c in fehlend]


def _cp1252(zeichen: str) -> bool:
    try:
        zeichen.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


def pdf_erzeugen(md_pfad: Path) -> Path:
    text = md_pfad.read_text(encoding="utf-8")
    for warnung in zeichen_pruefen(md_pfad, text):
        print("Warnung:", warnung)
    ziel = md_pfad.with_suffix(".pdf")
    doc = SimpleDocTemplate(
        str(ziel), pagesize=A4,
        leftMargin=2.3 * cm, rightMargin=2.3 * cm,
        topMargin=2.0 * cm, bottomMargin=2.3 * cm,
    )
    teile, titel = flowables(text, doc.width)
    doc.title = titel or md_pfad.stem
    doc.author = AUTOR
    doc.subject = "Fiktives Dokument – nur für interne Demonstrationszwecke"
    doc.creator = "f13-demo werkzeuge/pdf_erzeugen.py"
    doc.build(teile, onFirstPage=fusszeile, onLaterPages=fusszeile)
    return ziel


def main() -> int:
    # Windows-Konsolen (cp850/cp1252) sollen nicht an Sonderzeichen scheitern.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    quellen = sorted(RAG_DIR.glob("0*.md"))
    if not quellen:
        print(f"Fehler: keine Dateien 0*.md in {RAG_DIR} gefunden.")
        return 1
    for md in quellen:
        pdf = pdf_erzeugen(md)
        print(f"OK: {pdf.relative_to(REPO)} erzeugt")
    erstes = RAG_DIR / "01_vwv_pokehaltung.pdf"
    if erstes.exists():
        SUMMARY_PDF.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(erstes, SUMMARY_PDF)
        print(f"OK: {SUMMARY_PDF.relative_to(REPO)} kopiert (Dokument für die Zusammenfassung)")
    else:
        print("Warnung: 01_vwv_pokehaltung.pdf fehlt, keine Kopie für summary/ angelegt.")
    print(f"Fertig: {len(quellen)} PDF-Dateien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
