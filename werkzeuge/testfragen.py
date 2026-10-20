"""Gegenprobe: stellt die Testfragen direkt an das Sprachmodell, OHNE RAG.

Aufruf (PowerShell):  docker compose run --rm testfragen

Die Fragen stammen aus demo-data/rag/testfragen.md (im Container: /demo-data/rag/).
Die Antworten zeigen, was das Modell ohne die Wissensbasis „weiß“ (meist rät es).
Zum Vergleich dieselben Fragen in der Oberfläche unter „Recherche“ mit den
hochgeladenen PDFs stellen.

Liest aus der Umgebung: OLLAMA_URL, LLM_MODELL, TESTFRAGEN_DATEI.
Nur Python-Standardbibliothek.
"""

import json
import os
import re
import socket
import sys
import textwrap
import time
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434").rstrip("/")
LLM_MODELL = os.environ.get("SPRACHMODELL", "f13-sprachmodell")
TESTFRAGEN_DATEI = os.environ.get("TESTFRAGEN_DATEI", "/demo-data/rag/testfragen.md")

SYSTEM_PROMPT = "Antworte knapp auf Deutsch."
# Eine Antwort auf der CPU kann mehrere Minuten dauern.
TIMEOUT_S = int(os.environ.get("TESTFRAGEN_TIMEOUT_S", "600"))

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

# Zeichen, die um eine Frage herum entfernt werden (Anführungszeichen, Hervorhebung).
_RAND = " \t„“”\"'‚‘’»«*_"


def _zellen(zeile):
    """Zerlegt eine Markdown-Tabellenzeile in Zellen. Beachtet maskierte Pipes (\\|)."""
    zeile = zeile.strip()
    if zeile.startswith("|"):
        zeile = zeile[1:]
    if zeile.endswith("|") and not zeile.endswith("\\|"):
        zeile = zeile[:-1]
    teile = re.split(r"(?<!\\)\|", zeile)
    return [t.replace("\\|", "|").strip() for t in teile]


def _ist_trennzeile(zellen):
    return bool(zellen) and all(re.fullmatch(r":?-+:?", z.replace(" ", "")) for z in zellen)


def fragen_lesen(text):
    """Liest die erste Markdown-Tabelle und gibt (Kopfzeile, Fragen) zurück.

    ANNAHME (ungeprüft): testfragen.md enthält als erste Tabelle die Testfragen, und
    Spalte 2 heißt „Frage“. Codeblöcke (```) werden übersprungen.
    """
    tabelle = []
    im_code = False
    for zeile in text.splitlines():
        streifen = zeile.strip()
        if streifen.startswith("```") or streifen.startswith("~~~"):
            im_code = not im_code
            continue
        if im_code:
            continue
        if streifen.startswith("|"):
            tabelle.append(_zellen(streifen))
        elif tabelle:
            break  # Ende der ersten Tabelle

    if len(tabelle) < 2 or not _ist_trennzeile(tabelle[1]):
        return [], []
    kopf, daten = tabelle[0], tabelle[2:]

    fragen = []
    for zellen in daten:
        if len(zellen) < 2:
            continue
        frage = re.sub(r"<br\s*/?>", " ", zellen[1], flags=re.IGNORECASE)
        frage = re.sub(r"\s+", " ", frage).strip(_RAND)
        if frage:
            fragen.append(frage)
    return kopf, fragen


def dauer(sekunden):
    if sekunden < 60:
        return f"{sekunden:.1f} s".replace(".", ",")
    minuten, rest = divmod(int(round(sekunden)), 60)
    return f"{minuten} min {rest:02d} s"


def fehlertext(fehler):
    if isinstance(fehler, urllib.error.HTTPError):
        hinweis = " – Modell fehlt? docker compose run --rm modelle-laden" if fehler.code == 404 else ""
        return f"HTTP {fehler.code} {fehler.reason}{hinweis}"
    if isinstance(fehler, (TimeoutError, socket.timeout)):
        return f"keine Antwort innerhalb von {TIMEOUT_S} s"
    if isinstance(fehler, urllib.error.URLError):
        grund = fehler.reason
        if isinstance(grund, (TimeoutError, socket.timeout)):
            return f"keine Antwort innerhalb von {TIMEOUT_S} s"
        if isinstance(grund, socket.gaierror):
            return "Ollama nicht auffindbar – läuft der Dienst? (docker compose ps)"
        if isinstance(grund, ConnectionRefusedError):
            return "Verbindung abgelehnt – startet Ollama noch?"
        return f"Netzwerkfehler: {grund}"
    return f"{type(fehler).__name__}: {fehler}"


def frage_stellen(frage):
    anfrage = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(
            {
                "model": LLM_MODELL,
                "stream": False,
                "keep_alive": -1,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": frage},
                ],
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with OPENER.open(anfrage, timeout=TIMEOUT_S) as antwort:
        daten = json.loads(antwort.read().decode("utf-8"))
    return (daten.get("message") or {}).get("content", "").strip()


def einruecken(text, breite=88):
    zeilen = []
    for absatz in text.splitlines() or [""]:
        zeilen.extend(textwrap.wrap(absatz, breite - 4) or [""])
    return "\n".join("    " + z for z in zeilen)


def main():
    try:
        with open(TESTFRAGEN_DATEI, encoding="utf-8") as datei:
            kopf, fragen = fragen_lesen(datei.read())
    except OSError as fehler:
        print(f"✘ Datei {TESTFRAGEN_DATEI} nicht lesbar: {fehler.strerror}")
        return 1
    if not fragen:
        print(f"✘ Keine Fragen gefunden. Erwartet wird in {TESTFRAGEN_DATEI} eine")
        print("  Markdown-Tabelle mit der Frage in Spalte 2.")
        return 1
    if len(kopf) < 2 or "frage" not in kopf[1].lower():
        print(f"Hinweis: Spalte 2 heißt „{kopf[1] if len(kopf) > 1 else ''}“, nicht „Frage“.")

    print(f"Gegenprobe ohne RAG: {len(fragen)} Fragen an „{LLM_MODELL}“")
    print(f"Systemprompt: „{SYSTEM_PROMPT}“")
    print("Hinweis: Auf der CPU dauert jede Antwort eine Weile.\n")

    fehler_anzahl = 0
    gesamt_start = time.monotonic()
    for nummer, frage in enumerate(fragen, start=1):
        print(f"── Frage {nummer}/{len(fragen)} " + "─" * 50)
        print(f"  {frage}", flush=True)
        start = time.monotonic()
        try:
            antwort = frage_stellen(frage)
        except Exception as fehler:  # noqa: BLE001
            fehler_anzahl += 1
            print(f"  ✘ Fehler nach {dauer(time.monotonic() - start)}: {fehlertext(fehler)}\n", flush=True)
            continue
        print("  Antwort (ohne RAG):")
        print(einruecken(antwort or "(leer)"))
        print(f"  ✔ Dauer: {dauer(time.monotonic() - start)}\n", flush=True)

    print(f"Gesamtdauer: {dauer(time.monotonic() - gesamt_start)}")
    if fehler_anzahl:
        print(f"✘ {fehler_anzahl} von {len(fragen)} Fragen ohne Antwort.")
        return 1
    print("✔ Alle Fragen beantwortet. Jetzt dieselben Fragen in der Recherche (mit RAG) stellen.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(130)
