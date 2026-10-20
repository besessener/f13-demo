"""Lädt das Sprachmodell und das Embedding-Modell in Ollama (einmalig, braucht Internet).

Aufruf (PowerShell):  docker compose run --rm modelle-laden

Liest aus der Umgebung (gesetzt in docker-compose.yml / .env):
  OLLAMA_URL        z. B. http://ollama:11434
  LLM_MODELL        z. B. llama3.2:3b
  EMBEDDING_MODELL  z. B. granite-embedding:278m

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

# Wartezeit auf das nächste Lebenszeichen von Ollama (nicht für den ganzen Download).
LESE_TIMEOUT_S = 600
# Fortschritt höchstens alle 5 Prozent ausgeben.
SCHRITT_PROZENT = 5

# Interne Dienste nie über einen Proxy ansprechen.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

STATUS_DEUTSCH = {
    "pulling manifest": "Manifest wird geladen …",
    "verifying sha256 digest": "Prüfsumme wird geprüft …",
    "writing manifest": "Manifest wird geschrieben …",
    "removing any unused layers": "Nicht mehr benötigte Teile werden entfernt …",
    "removing unused layers": "Nicht mehr benötigte Teile werden entfernt …",
}


def groesse(anzahl_bytes):
    """Bytes als deutsche Größenangabe, z. B. '1,9 GB'."""
    wert = float(anzahl_bytes)
    for einheit in ("B", "KB", "MB", "GB", "TB"):
        if wert < 1000 or einheit == "TB":
            text = f"{wert:.0f}" if einheit in ("B", "KB") else f"{wert:.1f}"
            return f"{text.replace('.', ',')} {einheit}"
        wert /= 1000
    return f"{anzahl_bytes} B"


def dauer(sekunden):
    if sekunden < 60:
        return f"{sekunden:.1f} s".replace(".", ",")
    minuten, rest = divmod(int(round(sekunden)), 60)
    return f"{minuten} min {rest:02d} s"


def fehlertext(fehler):
    """Übersetzt Netzwerkfehler in eine verständliche deutsche Meldung."""
    if isinstance(fehler, urllib.error.HTTPError):
        try:
            inhalt = fehler.read().decode("utf-8", "replace").strip()
        except Exception:
            inhalt = ""
        return f"HTTP {fehler.code} {fehler.reason}" + (f": {inhalt[:300]}" if inhalt else "")
    if isinstance(fehler, (TimeoutError, socket.timeout)):
        return "Zeitüberschreitung – Ollama antwortet nicht"
    if isinstance(fehler, urllib.error.URLError):
        grund = fehler.reason
        if isinstance(grund, (TimeoutError, socket.timeout)):
            return "Zeitüberschreitung – Ollama antwortet nicht"
        if isinstance(grund, socket.gaierror):
            return "Name nicht auflösbar – läuft der Dienst? (docker compose ps)"
        if isinstance(grund, ConnectionRefusedError):
            return "Verbindung abgelehnt – startet der Dienst noch?"
        return f"Netzwerkfehler: {grund}"
    return f"{type(fehler).__name__}: {fehler}"


def modell_laden(name):
    """Lädt ein Modell per /api/pull und zeigt den Fortschritt. Gibt True bei Erfolg zurück."""
    print(f"\n▶ Lade Modell „{name}“ …", flush=True)
    start = time.monotonic()
    anfrage = urllib.request.Request(
        f"{OLLAMA_URL}/api/pull",
        data=json.dumps({"model": name, "stream": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    letzter_status = None
    gemeldet = {}  # digest -> zuletzt ausgegebener Prozentschritt
    teile = []  # Reihenfolge der digests, für "Teil 2/3"
    try:
        with OPENER.open(anfrage, timeout=LESE_TIMEOUT_S) as antwort:
            for zeile in antwort:
                zeile = zeile.strip()
                if not zeile:
                    continue
                try:
                    meldung = json.loads(zeile)
                except json.JSONDecodeError:
                    continue
                if "error" in meldung:
                    print(f"  ✘ Ollama meldet einen Fehler: {meldung['error']}", flush=True)
                    return False
                status = meldung.get("status", "")
                digest = meldung.get("digest")
                if digest:
                    gesamt = meldung.get("total") or 0
                    fertig = meldung.get("completed") or 0
                    if digest not in teile:
                        teile.append(digest)
                    if gesamt <= 0:
                        continue
                    prozent = min(100, int(fertig * 100 / gesamt))
                    schritt = prozent - prozent % SCHRITT_PROZENT
                    if schritt > gemeldet.get(digest, -1):
                        gemeldet[digest] = schritt
                        kurz = digest.replace("sha256:", "")[:12]
                        print(
                            f"  Teil {teile.index(digest) + 1} ({kurz}, {groesse(gesamt)}): "
                            f"{schritt:3d} %",
                            flush=True,
                        )
                    continue
                if status == "success":
                    print(f"  ✔ „{name}“ ist vorhanden ({dauer(time.monotonic() - start)}).", flush=True)
                    return True
                if status and status != letzter_status:
                    letzter_status = status
                    print(f"  {STATUS_DEUTSCH.get(status, status)}", flush=True)
    except Exception as fehler:  # noqa: BLE001 – jede Ursache verständlich melden
        print(f"  ✘ Laden von „{name}“ fehlgeschlagen: {fehlertext(fehler)}", flush=True)
        return False
    print(f"  ✘ Ollama hat den Download von „{name}“ nicht mit „success“ abgeschlossen.", flush=True)
    return False


def main():
    print("Modelle laden")
    print(f"  Ollama:    {OLLAMA_URL}")
    print(f"  Sprache:   {LLM_MODELL}")
    print(f"  Embedding: {EMBEDDING_MODELL}")
    print("Das dauert beim ersten Mal je nach Leitung einige Minuten (ca. 2,6 GB).")

    ergebnisse = {name: modell_laden(name) for name in (LLM_MODELL, EMBEDDING_MODELL)}

    print("\nErgebnis:")
    for name, ok in ergebnisse.items():
        print(f"  {'✔' if ok else '✘'} {name}")
    if all(ergebnisse.values()):
        print("\nFertig. Weiter mit: docker compose run --rm warmup")
        return 0
    print("\nNicht alle Modelle konnten geladen werden. Internetverbindung prüfen und erneut")
    print("ausführen: docker compose run --rm modelle-laden  (bereits Geladenes bleibt erhalten)")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(130)
