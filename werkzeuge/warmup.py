"""Lädt Sprach- und Embedding-Modell vor der Vorführung in den Arbeitsspeicher.

Aufruf (PowerShell):  docker compose run --rm warmup

Beide Modelle werden mit keep_alive = -1 geladen und bleiben damit geladen, bis Ollama
neu startet. So muss bei der ersten Frage in der Vorführung niemand warten.

Liest aus der Umgebung: OLLAMA_URL, LLM_MODELL, EMBEDDING_MODELL.
Nur Python-Standardbibliothek.
"""

import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434").rstrip("/")
LLM_MODELL = os.environ.get("LLM_MODELL", "llama3.2:3b")
EMBEDDING_MODELL = os.environ.get("EMBEDDING_MODELL", "granite-embedding:278m")

# Laden und Rechnen auf der CPU kann lange dauern.
TIMEOUT_S = 900

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def dauer(sekunden):
    if sekunden < 60:
        return f"{sekunden:.1f} s".replace(".", ",")
    minuten, rest = divmod(int(round(sekunden)), 60)
    return f"{minuten} min {rest:02d} s"


def fehlertext(fehler):
    if isinstance(fehler, urllib.error.HTTPError):
        try:
            inhalt = fehler.read().decode("utf-8", "replace").strip()
        except Exception:
            inhalt = ""
        hinweis = ""
        if fehler.code == 404:
            hinweis = " – Modell fehlt? Erst: docker compose run --rm modelle-laden"
        return f"HTTP {fehler.code} {fehler.reason}" + (f": {inhalt[:300]}" if inhalt else "") + hinweis
    if isinstance(fehler, (TimeoutError, socket.timeout)):
        return f"Zeitüberschreitung nach {TIMEOUT_S} s – ist der Rechner ausgelastet?"
    if isinstance(fehler, urllib.error.URLError):
        grund = fehler.reason
        if isinstance(grund, (TimeoutError, socket.timeout)):
            return f"Zeitüberschreitung nach {TIMEOUT_S} s – ist der Rechner ausgelastet?"
        if isinstance(grund, socket.gaierror):
            return "Ollama nicht auffindbar – läuft der Dienst? (docker compose ps)"
        if isinstance(grund, ConnectionRefusedError):
            return "Verbindung abgelehnt – startet Ollama noch?"
        return f"Netzwerkfehler: {grund}"
    return f"{type(fehler).__name__}: {fehler}"


def post(pfad, daten):
    anfrage = urllib.request.Request(
        f"{OLLAMA_URL}{pfad}",
        data=json.dumps(daten).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with OPENER.open(anfrage, timeout=TIMEOUT_S) as antwort:
        return json.loads(antwort.read().decode("utf-8"))


def schritt(text, funktion):
    print(f"▶ {text} …", flush=True)
    start = time.monotonic()
    try:
        ergebnis = funktion()
    except Exception as fehler:  # noqa: BLE001
        print(f"  ✘ fehlgeschlagen nach {dauer(time.monotonic() - start)}: {fehlertext(fehler)}", flush=True)
        return False, None
    print(f"  ✔ fertig in {dauer(time.monotonic() - start)}", flush=True)
    return True, ergebnis


def main():
    print(f"Warm-up für die Vorführung (Ollama: {OLLAMA_URL})\n")
    ergebnisse = []

    # 1. Sprachmodell laden: Ein leerer Prompt lädt das Modell nur, ohne zu antworten.
    ok, _ = schritt(
        f"Sprachmodell „{LLM_MODELL}“ laden",
        lambda: post("/api/generate", {"model": LLM_MODELL, "keep_alive": -1}),
    )
    ergebnisse.append(ok)

    # 2. Kurze Probeantwort: zeigt die Geschwindigkeit (Tokens pro Sekunde).
    if ok:
        ok2, antwort = schritt(
            "Probeantwort erzeugen",
            lambda: post(
                "/api/generate",
                {
                    "model": LLM_MODELL,
                    "prompt": "Sag in einem kurzen Satz Hallo.",
                    "stream": False,
                    "keep_alive": -1,
                    "options": {"num_predict": 32},
                },
            ),
        )
        ergebnisse.append(ok2)
        if ok2 and antwort:
            text = (antwort.get("response") or "").strip().replace("\n", " ")
            print(f"  Antwort: {text}")
            anzahl = antwort.get("eval_count") or 0
            nanosek = antwort.get("eval_duration") or 0
            if anzahl and nanosek:
                print(f"  Geschwindigkeit: {anzahl / (nanosek / 1e9):.1f} Tokens/s".replace(".", ","))

    # 3. Embedding-Modell laden.
    ok3, _ = schritt(
        f"Embedding-Modell „{EMBEDDING_MODELL}“ laden",
        lambda: post("/api/embed", {"model": EMBEDDING_MODELL, "input": "Aufwärmen", "keep_alive": -1}),
    )
    ergebnisse.append(ok3)

    # 4. Was ist jetzt geladen?
    try:
        with OPENER.open(f"{OLLAMA_URL}/api/ps", timeout=30) as antwort:
            geladen = json.loads(antwort.read().decode("utf-8")).get("models", [])
        print("\nGeladene Modelle:")
        for modell in geladen:
            gb = f"{(modell.get('size') or 0) / 1e9:.1f}".replace(".", ",")
            print(f"  • {modell.get('name')}: ca. {gb} GB")
    except Exception as fehler:  # noqa: BLE001
        print(f"\nGeladene Modelle konnten nicht abgefragt werden: {fehlertext(fehler)}")

    if all(ergebnisse):
        print("\n✔ Warm-up abgeschlossen. Die Vorführung kann beginnen.")
        return 0
    print("\n✘ Warm-up unvollständig. Details siehe oben; Status: docker compose ps")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(130)
