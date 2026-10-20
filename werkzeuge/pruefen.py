"""Prüft, ob alle Teile der Demo laufen. Eine Zeile pro Prüfung mit ✔ oder ✘.

Aufruf (PowerShell):  docker compose run --rm pruefen

Exit-Code 0, wenn alles in Ordnung ist, sonst 1.

Liest aus der Umgebung: OLLAMA_URL, LLM_MODELL, EMBEDDING_MODELL, ELASTICSEARCH_URL,
CORE_URL, FRONTEND_URL. Nur Python-Standardbibliothek.
"""

import json
import os
import socket
import sys
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434").rstrip("/")
ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200").rstrip("/")
CORE_URL = os.environ.get("CORE_URL", "http://core:8000").rstrip("/")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://frontend:9999").rstrip("/")
LLM_MODELL = os.environ.get("SPRACHMODELL", "f13-sprachmodell")
EMBEDDING_MODELL = os.environ.get("EMBEDDING", "f13-embedding")

# Die /llms-Endpunkte fragen ggf. selbst Ollama ab; auf der CPU kann das dauern.
TIMEOUT_S = int(os.environ.get("PRUEFEN_TIMEOUT_S", "30"))

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Pruefungsfehler(Exception):
    """Eine Prüfung ist fehlgeschlagen; der Text ist die deutsche Begründung."""


def fehlertext(fehler):
    if isinstance(fehler, urllib.error.HTTPError):
        if fehler.code in (502, 503, 504):
            return f"HTTP {fehler.code} – der Dienst hinter dem Core läuft nicht oder startet noch"
        return f"HTTP {fehler.code} {fehler.reason}"
    if isinstance(fehler, (TimeoutError, socket.timeout)):
        return f"keine Antwort innerhalb von {TIMEOUT_S} s"
    if isinstance(fehler, urllib.error.URLError):
        grund = fehler.reason
        if isinstance(grund, (TimeoutError, socket.timeout)):
            return f"keine Antwort innerhalb von {TIMEOUT_S} s"
        if isinstance(grund, socket.gaierror):
            return "Dienst nicht gefunden – läuft er? (docker compose ps)"
        if isinstance(grund, ConnectionRefusedError):
            return "Verbindung abgelehnt – startet der Dienst noch?"
        return f"Netzwerkfehler: {grund}"
    return f"{type(fehler).__name__}: {fehler}"


def hole(url):
    """GET-Anfrage. Gibt (Status, Text) zurück oder wirft Pruefungsfehler."""
    try:
        with OPENER.open(url, timeout=TIMEOUT_S) as antwort:
            return antwort.status, antwort.read().decode("utf-8", "replace")
    except Exception as fehler:  # noqa: BLE001
        raise Pruefungsfehler(fehlertext(fehler)) from None


def hole_json(url):
    status, text = hole(url)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise Pruefungsfehler(f"Antwort ist kein JSON (HTTP {status}): {text[:120]!r}") from None


def mit_tag(name):
    """Ollama ergänzt ':latest', wenn kein Tag angegeben ist."""
    return name if ":" in name else f"{name}:latest"


# --- Einzelne Prüfungen: geben einen Erfolgstext zurück oder werfen Pruefungsfehler ---

def pruefe_ollama():
    daten = hole_json(f"{OLLAMA_URL}/api/tags")
    vorhanden = {mit_tag(m.get("name", "")) for m in daten.get("models", [])}
    fehlend = [m for m in (LLM_MODELL, EMBEDDING_MODELL) if mit_tag(m) not in vorhanden]
    if fehlend:
        raise Pruefungsfehler(
            "Modell fehlt: " + ", ".join(fehlend) + " → docker compose run --rm modelle-laden"
        )
    return f"läuft, Modelle {LLM_MODELL} und {EMBEDDING_MODELL} vorhanden"


def pruefe_elasticsearch():
    daten = hole_json(f"{ELASTICSEARCH_URL}/_cluster/health")
    status = daten.get("status")
    if status not in ("green", "yellow"):
        raise Pruefungsfehler(f"Clusterstatus „{status}“")
    return f"läuft, Clusterstatus „{status}“"


def pruefe_core():
    daten = hole_json(f"{CORE_URL}/health")
    text = daten.get("status", "") if isinstance(daten, dict) else ""
    return f"läuft ({text})" if text else "läuft"


def llm_liste(dienst):
    def pruefung():
        daten = hole_json(f"{CORE_URL}/{dienst}/llms")
        # ANNAHME (ungeprüft): Antwort ist eine Liste von Modellen mit "label".
        # Das Format wird nur angezeigt, nicht bewertet.
        if isinstance(daten, list):
            if not daten:
                raise Pruefungsfehler("Antwort ist eine leere Modellliste")
            namen = [str(m.get("label") or m.get("id") or m) if isinstance(m, dict) else str(m) for m in daten]
            return "Modelle: " + ", ".join(namen)
        return "antwortet"
    return pruefung


def pruefe_frontend():
    status, _ = hole(f"{FRONTEND_URL}/")
    return f"läuft (HTTP {status})"


PRUEFUNGEN = [
    ("Ollama", pruefe_ollama),
    ("Elasticsearch", pruefe_elasticsearch),
    ("Core /health", pruefe_core),
    ("Core /chat/llms", llm_liste("chat")),
    ("Core /summary/llms", llm_liste("summary")),
    ("Core /rag/llms", llm_liste("rag")),
    ("Frontend", pruefe_frontend),
]


def alle_pruefen(pruefungen=PRUEFUNGEN):
    """Führt alle Prüfungen aus. Gibt eine Liste (Name, ok, Text) zurück."""
    ergebnisse = []
    for name, pruefung in pruefungen:
        try:
            ergebnisse.append((name, True, pruefung()))
        except Pruefungsfehler as fehler:
            ergebnisse.append((name, False, str(fehler)))
        except Exception as fehler:  # noqa: BLE001 – unerwartete Antwortformate
            ergebnisse.append((name, False, f"unerwartete Antwort: {fehlertext(fehler)}"))
    return ergebnisse


def ausgeben(ergebnisse, aus=print):
    """Gibt die Ergebnisse aus und liefert den Exit-Code (0 = alles ok, 1 = Fehler)."""
    breite = max(len(name) for name, _, _ in ergebnisse)
    for name, ok, text in ergebnisse:
        aus(f"{'✔' if ok else '✘'} {name.ljust(breite)}  {text}")
    fehler = sum(1 for _, ok, _ in ergebnisse if not ok)
    aus("")
    if fehler == 0:
        aus("✔ Alles in Ordnung.")
        return 0
    aus(f"✘ {fehler} von {len(ergebnisse)} Prüfungen fehlgeschlagen.")
    aus("  Tipp: docker compose ps  und  docker compose logs <dienst>")
    return 1


def main():
    print("Prüfe die F13-Demo …\n", flush=True)
    return ausgeben(alle_pruefen())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(130)
