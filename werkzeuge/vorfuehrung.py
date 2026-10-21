"""Vorführung im Terminal: Chat, Zusammenfassung und Recherche über die echte F13-API.

Aufruf (PowerShell):
  docker compose run --rm vorfuehrung
  docker compose run --rm -e FRAGEN=1,3,6 vorfuehrung
  docker compose run --rm -e RAG_MODUS=datei vorfuehrung   (PDFs hochladen statt Wissensdatenbank)

Zeigt dieselben Schritte wie die Vorführung im Browser (docs/DEMO-SKRIPT.md), aber
automatisch und mit Zeitmessung. Gedacht als Rückfallebene, falls die Oberfläche hakt, und
für einen zweiten Bildschirm. Die Recherche-Antworten werden mit dem Antwortschlüssel aus
demo-data/rag/testfragen.md und mit der Gegenprobe ohne RAG verglichen.

Nur Python-Standardbibliothek.
"""

import glob
import json
import os
import sys
import textwrap
import time

import f13_api as api
from testfragen import fragen_lesen

FRAGEN = [int(n) for n in os.environ.get("FRAGEN", "1,3,4").split(",") if n.strip()]
BREITE = 88
TEMPO = float(os.environ.get("TEMPO", "0.6"))  # Pause zwischen Abschnitten in Sekunden
# "datenbank": Wissensdatenbank „Pokémon-Regeln“ (vorher: wissensbasis); "datei": PDFs hochladen
RAG_MODUS = os.environ.get("RAG_MODUS", "datenbank")


def zeile(zeichen="─"):
    print(zeichen * BREITE)


def titel(nummer, text):
    print()
    zeile("━")
    print(f" {nummer}  {text}")
    zeile("━")
    time.sleep(TEMPO)


def block(beschriftung, text):
    print(f"\n{beschriftung}")
    for absatz in str(text).splitlines() or [""]:
        for teil in textwrap.wrap(absatz, BREITE - 4) or [""]:
            print(f"  │ {teil}")


def sekunden(sek):
    return f"{sek:.1f} s".replace(".", ",")


def ergebnis(status, sek):
    if status == 200:
        print(f"\n  ✔ fertig in {sekunden(sek)}")
        return True
    print(f"\n  ✘ HTTP {status} nach {sekunden(sek)}")
    return False


def schritt_chat():
    titel("1", "Chat: Bescheid in Leichter Sprache")
    frage = ("Schreibe einen kurzen Ablehnungsbescheid in Leichter Sprache für einen Antrag "
             "auf eine Arenalizenz. Grund: Es fehlen Orden. Nenne keine Fristen und keine Beträge.")
    block("Frage:", frage)
    status, text, sek = api.chat(frage)
    block("Antwort von F13:", api.text_aus(text))
    return ergebnis(status, sek)


def schritt_zusammenfassung():
    titel("2", "Zusammenfassung: VwV PokéHaltung (PDF, 3 Seiten)")
    pfad = f"{api.DATEN}/summary/vwv_pokehaltung.pdf"
    print(f"\nDokument: {os.path.basename(pfad)}")
    status, text, sek = api.zusammenfassung_datei(pfad)
    block("Zusammenfassung von F13:", api.text_aus(text))
    return ergebnis(status, sek)


def schritt_recherche():
    titel("3", "Recherche (RAG) in der Pokémon-Wissensbasis")
    pdfs = sorted(glob.glob(f"{api.DATEN}/rag/0*.pdf"))
    if RAG_MODUS == "datei":
        print(f"\nHochgeladene Dokumente: {', '.join(os.path.basename(p) for p in pdfs)}")
    else:
        print(f"\nWissensdatenbank: {api.WISSENSBASIS} ({len(pdfs)} Dokumente, vorab geladen)")
    with open(f"{api.DATEN}/rag/testfragen.md", encoding="utf-8") as datei:
        _, alle = fragen_lesen(datei.read())
    schluessel = antwortschluessel()
    erfolge = []
    for nummer in FRAGEN:
        if not 1 <= nummer <= len(alle):
            continue
        frage = alle[nummer - 1]
        print()
        zeile()
        print(f" Frage {nummer}: {frage}")
        zeile()
        if RAG_MODUS == "datei":
            status, text, sek = api.recherche_dateien(pdfs, frage)
        else:
            status, text, sek = api.recherche_datenbank(frage)
        block("Mit RAG (F13 + Dokumente):", api.text_aus(text))
        quellen = api.quellen_aus(text)
        if quellen:
            print("\n  Quellen: " + "; ".join(dict.fromkeys(quellen)))
        if nummer in schluessel:
            block("Laut Antwortschlüssel:", schluessel[nummer])
        status_ohne, text_ohne, _ = api.ohne_rag(frage)
        if status_ohne == 200:
            antwort_ohne = json.loads(text_ohne).get("message", {}).get("content", "").strip()
            block("Ohne RAG (nur das Sprachmodell):", antwort_ohne)
        erfolge.append(ergebnis(status, sek))
    return all(erfolge) if erfolge else False


def antwortschluessel():
    """Nr. -> erwartete Antwort aus der Tabelle in testfragen.md."""
    ergebnis_ = {}
    with open(f"{api.DATEN}/rag/testfragen.md", encoding="utf-8") as datei:
        for zeile_ in datei:
            zellen = [z.strip() for z in zeile_.strip().strip("|").split("|")]
            if len(zellen) >= 3 and zellen[0].isdigit():
                ergebnis_[int(zellen[0])] = zellen[2]
    return ergebnis_


def main():
    zeile("━")
    print(" F13 · Vorführung im Terminal")
    print(f" Sprachmodell: {api.LLM_MODELL}   Alles läuft lokal auf diesem Rechner.")
    zeile("━")
    start = time.monotonic()
    ergebnisse = []
    for schritt in (schritt_chat, schritt_zusammenfassung, schritt_recherche):
        try:
            ergebnisse.append(schritt())
        except Exception as fehler:  # noqa: BLE001 – Vorführung soll weiterlaufen
            print(f"\n  ✘ {type(fehler).__name__}: {fehler}")
            ergebnisse.append(False)
    print()
    zeile("━")
    print(f" Fertig in {sekunden(time.monotonic() - start)}: "
          f"{sum(ergebnisse)} von {len(ergebnisse)} Schritten erfolgreich.")
    zeile("━")
    return 0 if all(ergebnisse) else 1


if __name__ == "__main__":
    sys.exit(main())
