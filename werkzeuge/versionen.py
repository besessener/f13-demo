"""Zeigt, welche F13-Images und Tags es in der Registry von opencode.de gibt.

Aufruf (PowerShell):  docker compose run --rm versionen

Fragt die öffentliche GitLab-API von gitlab.opencode.de ohne Anmeldung ab und
vergleicht mit den Versionen aus .env. Stimmt etwas nicht, den Wert in .env korrigieren.
Braucht Internet. Nur Python-Standardbibliothek.
"""

import json
import os
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

GITLAB_API = os.environ.get("GITLAB_API", "https://gitlab.opencode.de/api/v4").rstrip("/")
GRUPPE = "f13/microservices"
TIMEOUT_S = 30
MAX_TAGS = 15

# Projekt -> Variable in .env
PROJEKTE = [
    ("chat", "F13_CHAT_VERSION"),
    ("summary", "F13_SUMMARY_VERSION"),
    ("rag", "F13_RAG_VERSION"),
    ("parser", "F13_PARSER_VERSION"),
    ("feedback", "F13_FEEDBACK_VERSION"),
    # F13 v3 nutzt das Svelte-Frontend aus "frontend" (nicht das neuere "f13-frontend").
    ("frontend", "F13_FRONTEND_VERSION"),
]


class Abfragefehler(Exception):
    pass


def hole_json(pfad):
    url = f"{GITLAB_API}{pfad}"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_S) as antwort:
            return json.loads(antwort.read().decode("utf-8"))
    except urllib.error.HTTPError as fehler:
        if fehler.code == 404:
            raise Abfragefehler("nicht gefunden (oder nicht öffentlich)") from None
        if fehler.code in (401, 403):
            raise Abfragefehler(f"kein anonymer Zugriff (HTTP {fehler.code})") from None
        raise Abfragefehler(f"HTTP {fehler.code} {fehler.reason}") from None
    except (TimeoutError, socket.timeout):
        raise Abfragefehler(f"keine Antwort innerhalb von {TIMEOUT_S} s") from None
    except urllib.error.URLError as fehler:
        grund = fehler.reason
        if isinstance(grund, (TimeoutError, socket.timeout)):
            raise Abfragefehler(f"keine Antwort innerhalb von {TIMEOUT_S} s") from None
        if isinstance(grund, socket.gaierror):
            raise Abfragefehler("gitlab.opencode.de nicht erreichbar – Internet/Proxy prüfen") from None
        raise Abfragefehler(f"Netzwerkfehler: {grund}") from None
    except json.JSONDecodeError:
        raise Abfragefehler("Antwort ist kein JSON") from None


def versionsschluessel(tag):
    """Sortiert v3.10.0 nach v3.9.0; Tags ohne Zahlen (z. B. latest) zuerst."""
    zahlen = [int(z) for z in re.findall(r"\d+", tag)]
    return (bool(zahlen), zahlen, tag)


def projekt_id(projekt):
    return urllib.parse.quote(f"{GRUPPE}/{projekt}", safe="")


def registry_abfragen(projekt):
    """Gibt eine Liste (Image-Pfad, [Tags]) zurück."""
    daten = hole_json(f"/projects/{projekt_id(projekt)}/registry/repositories?tags=true&tags_count=true&per_page=100")
    ergebnis = []
    for repo in daten if isinstance(daten, list) else []:
        tags = [t.get("name", "") for t in repo.get("tags") or []]
        ergebnis.append((repo.get("location") or repo.get("path") or "?", sorted(tags, key=versionsschluessel)))
    return ergebnis


def git_tags_abfragen(projekt):
    daten = hole_json(f"/projects/{projekt_id(projekt)}/repository/tags?per_page=100&order_by=updated")
    return sorted((t.get("name", "") for t in daten if isinstance(t, dict)), key=versionsschluessel)


def kuerzen(tags):
    if len(tags) <= MAX_TAGS:
        return ", ".join(tags)
    return "…, " + ", ".join(tags[-MAX_TAGS:]) + f"  ({len(tags)} insgesamt, neueste zuletzt)"


def main():
    print(f"F13-Images auf opencode.de ({GITLAB_API})\n", flush=True)
    probleme = 0
    for projekt, variable in PROJEKTE:
        aktuell = os.environ.get(variable, "")
        print(f"■ {projekt}   ({variable}={aktuell or '?'} in .env)", flush=True)
        alle_tags = []
        abgefragt = False
        try:
            repos = registry_abfragen(projekt)
            abgefragt = True
            if not repos:
                print("    Kein Image in der Registry.")
            for ort, tags in repos:
                alle_tags.extend(tags)
                print(f"    Image: {ort}")
                print(f"    Tags:  {kuerzen(tags) if tags else '(keine)'}")
        except Abfragefehler as fehler:
            print(f"    ✘ Registry: {fehler}")

        if projekt == "frontend":
            # Das Frontend wird aus einem Git-Tag gebaut, nicht aus einem Image.
            try:
                git_tags = git_tags_abfragen(projekt)
                abgefragt = True
                alle_tags.extend(git_tags)
                print(f"    Git-Tags (zum Bauen): {kuerzen(git_tags) if git_tags else '(keine)'}")
            except Abfragefehler as fehler:
                print(f"    ✘ Git-Tags: {fehler}")

        if not abgefragt:
            probleme += 1
            print("    ✘ Konnte nicht geprüft werden (siehe Fehler oben).")
        elif aktuell:
            if aktuell in alle_tags:
                print(f"    ✔ {aktuell} gibt es.")
            else:
                probleme += 1
                print(f"    ✘ {aktuell} nicht gefunden – {variable} in .env anpassen.")
        print(flush=True)

    print("Hinweis: Weicht ein Image-Pfad oben von docker-compose.yml ab, bitte dort anpassen.")
    if probleme:
        print(f"\n✘ {probleme} Version(en) aus .env nicht bestätigt (siehe oben).")
        return 1
    print("\n✔ Alle Versionen aus .env gefunden.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(130)
