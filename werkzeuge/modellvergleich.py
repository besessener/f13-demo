"""Vergleicht kleine Sprachmodelle auf dem eigenen Rechner: Tempo, RAM und Antworten.

Aufruf (PowerShell):
  docker compose run --rm modellvergleich
  docker compose run --rm -e MODELLE="llama3.2:3b,gemma3:1b" modellvergleich

Jedes Modell bekommt dieselben fünf deutschen Prompts (P1–P5 aus docs/MESSWERTE.md, mit
echten Textstellen aus demo-data/rag/). Gemessen werden Tokens pro Sekunde, Zeit bis zur
Antwort, Ladezeit und RAM des geladenen Modells laut Ollama. Fehlende Modelle werden geladen
(braucht Internet) und danach wieder gelöscht, außer es ist das Modell aus .env.

Ergebnis: Tabelle in der Konsole und ausgabe/modellvergleich.md mit allen Antworten zum
Bewerten (Deutsch, Quellentreue).

Nur Python-Standardbibliothek.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434").rstrip("/")
LLM_MODELL = os.environ.get("LLM_MODELL", "llama3.2:3b")
EMBEDDING_MODELL = os.environ.get("EMBEDDING_MODELL", "granite-embedding:278m")
MODELLE = [m.strip() for m in os.environ.get(
    "MODELLE", "llama3.2:3b,qwen3.5:2b,gemma4:e2b,gemma3:1b").split(",") if m.strip()]
DATEN = os.environ.get("DEMO_DATEN", "/demo-data")
AUSGABE = os.environ.get("AUSGABE_ORDNER", "/ausgabe")
AUFRAEUMEN = os.environ.get("AUFRAEUMEN", "1") == "1"
KONTEXT = int(os.environ.get("KONTEXT", "4096"))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "300"))

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def anfrage(pfad, nutzlast=None, timeout=1800, methode=None):
    daten = json.dumps(nutzlast).encode("utf-8") if nutzlast is not None else None
    req = urllib.request.Request(f"{OLLAMA_URL}{pfad}", data=daten, method=methode,
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=timeout) as antwort:
        return json.loads(antwort.read().decode("utf-8") or "{}")


def abschnitt(datei, ueberschrift_beginn):
    """Text eines Markdown-Abschnitts ab der Überschrift bis zur nächsten."""
    with open(f"{DATEN}/rag/{datei}", encoding="utf-8") as f:
        text = f.read()
    treffer = re.search(rf"^## {re.escape(ueberschrift_beginn)}.*?$(.*?)(?=^## |\Z)",
                        text, re.S | re.M)
    if not treffer:
        return ""
    return re.sub(r"\*\*", "", treffer.group(1)).strip()


def prompts():
    p3 = abschnitt("01_vwv_pokehaltung.md", "§ 5")
    p4 = abschnitt("01_vwv_pokehaltung.md", "§ 3")
    return [
        ("P1 Leichte Sprache",
         "Schreibe einen kurzen Ablehnungsbescheid in Leichter Sprache für einen Antrag auf "
         "eine Arenalizenz. Grund: Es fehlen Orden. Nenne keine Fristen und keine Beträge."),
        ("P2 Förmlich umformulieren",
         'Formuliere diese E-Mail höflich und förmlich um: "Ihr Antrag ist unvollständig, '
         'schicken Sie den Rest bis Freitag."'),
        ("P3 Zusammenfassen",
         f"Fasse in drei Stichpunkten zusammen:\n\n{p3}"),
        ("P4 Quellentreue",
         "Beantworte die Frage nur mit dem folgenden Text. Wenn die Antwort nicht im Text "
         f"steht, sag das.\n\nText:\n{p4}\n\nFrage: Darf ich mein Glurak mit ins Büro bringen?"),
        ("P5 Korrektur",
         "Korrigiere Rechtschreibung und Grammatik: Die Pokémon dürfen nicht in den "
         "Serverraum, weil das gefärlich ist und die Daten verlohren gehen können wen es "
         "Stromschläge gibt."),
    ]


def vorhanden():
    return {m.get("name") for m in anfrage("/api/tags", timeout=30).get("models", [])}


def laden(modell):
    print(f"  Lade {modell} … (einmalig, braucht Internet)", flush=True)
    ergebnis = anfrage("/api/pull", {"model": modell, "stream": False}, timeout=3600)
    if ergebnis.get("status") != "success":
        raise RuntimeError(ergebnis.get("error") or ergebnis)


def entladen(modell):
    try:
        anfrage("/api/generate", {"model": modell, "keep_alive": 0}, timeout=60)
    except (urllib.error.URLError, OSError, ValueError):
        pass


def ram_des_modells(modell):
    for m in anfrage("/api/ps", timeout=30).get("models", []):
        if m.get("name") == modell or m.get("model") == modell:
            return m.get("size", 0)
    return 0


def gb(anzahl):
    return f"{anzahl / 1e9:.1f} GB".replace(".", ",") if anzahl else "?"


def komma(zahl, stellen=1):
    return f"{zahl:.{stellen}f}".replace(".", ",")


def messen(modell, liste):
    ergebnisse = []
    for name, text in liste:
        nutzlast = {"model": modell, "prompt": text, "stream": False, "keep_alive": "10m",
                    # Denkende Modelle (z. B. Qwen) sollen direkt antworten, sonst zählen
                    # die versteckten Denk-Tokens mit und das Tempo ist nicht vergleichbar.
                    "think": False,
                    "options": {"num_ctx": KONTEXT, "num_predict": MAX_TOKENS, "temperature": 0.2}}
        start = time.monotonic()
        try:
            antwort = anfrage("/api/generate", nutzlast)
        except urllib.error.HTTPError as fehler:
            if fehler.code != 400:
                raise
            # Ältere Modelle kennen "think" nicht.
            nutzlast.pop("think")
            start = time.monotonic()
            antwort = anfrage("/api/generate", nutzlast)
        dauer = time.monotonic() - start
        tokens = antwort.get("eval_count", 0)
        tps = tokens / max((antwort.get("eval_duration") or 1) / 1e9, 1e-9)
        laden_s = (antwort.get("load_duration") or 0) / 1e9
        ergebnisse.append({"name": name, "tps": tps, "dauer": dauer, "laden": laden_s,
                           "antwort": antwort.get("response", "").strip()})
        print(f"    {name:26} {komma(tps):>6} Tokens/s   {komma(dauer):>6} s", flush=True)
    return ergebnisse


def main():
    liste = prompts()
    if not all(text for _, text in liste):
        print("✘ Textstellen aus demo-data/rag/ nicht gefunden.")
        return 1
    print(f"Modellvergleich: {', '.join(MODELLE)}  (Kontext {KONTEXT}, max. {MAX_TOKENS} Tokens)\n")
    bekannt = vorhanden()
    zusammenfassung, details = [], []

    for modell in MODELLE:
        print(f"▶ {modell}", flush=True)
        selbst_geladen = False
        try:
            if modell not in bekannt and f"{modell}:latest" not in bekannt:
                laden(modell)
                selbst_geladen = True
            # Andere Modelle entladen, damit der RAM-Wert nur dieses Modell zeigt.
            for anderes in (LLM_MODELL, EMBEDDING_MODELL, "f13-sprachmodell", "f13-embedding", *MODELLE):
                if anderes != modell:
                    entladen(anderes)
            ergebnisse = messen(modell, liste)
            ram = ram_des_modells(modell)
        except (urllib.error.URLError, OSError, ValueError, RuntimeError) as fehler:
            print(f"  ✘ übersprungen: {fehler}\n", flush=True)
            zusammenfassung.append((modell, None, None, None, f"Fehler: {fehler}"))
            continue
        finally:
            entladen(modell)
            if selbst_geladen and AUFRAEUMEN and modell != LLM_MODELL:
                try:
                    anfrage("/api/delete", {"model": modell}, timeout=120, methode="DELETE")
                    print(f"  Aufgeräumt: {modell} wieder gelöscht.")
                except (urllib.error.URLError, OSError, ValueError):
                    pass
        mittel_tps = sum(e["tps"] for e in ergebnisse) / len(ergebnisse)
        mittel_dauer = sum(e["dauer"] for e in ergebnisse) / len(ergebnisse)
        print(f"  Mittel: {komma(mittel_tps)} Tokens/s, RAM {gb(ram)}\n", flush=True)
        zusammenfassung.append((modell, mittel_tps, mittel_dauer, ram, ""))
        details.append((modell, ergebnisse))

    print("Ergebnis")
    print(f"  {'Modell':22} {'Tokens/s':>9} {'Ø Dauer':>9} {'RAM':>8}")
    for modell, tps, dauer, ram, hinweis in zusammenfassung:
        if tps is None:
            print(f"  {modell:22} {hinweis}")
        else:
            print(f"  {modell:22} {komma(tps):>9} {komma(dauer) + ' s':>9} {gb(ram):>8}")

    os.makedirs(AUSGABE, exist_ok=True)
    datei = f"{AUSGABE}/modellvergleich.md"
    with open(datei, "w", encoding="utf-8") as f:
        f.write(f"# Modellvergleich ({time.strftime('%d.%m.%Y %H:%M')})\n\n")
        f.write("| Modell | Tokens/s (Ø) | Dauer pro Prompt (Ø) | RAM laut Ollama | Deutsch 1–5 | Quellentreue 1–5 |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for modell, tps, dauer, ram, hinweis in zusammenfassung:
            if tps is None:
                f.write(f"| `{modell}` | {hinweis} | | | | |\n")
            else:
                f.write(f"| `{modell}` | {komma(tps)} | {komma(dauer)} s | {gb(ram)} | | |\n")
        for modell, ergebnisse in details:
            f.write(f"\n## {modell}\n")
            for e in ergebnisse:
                f.write(f"\n### {e['name']} – {komma(e['tps'])} Tokens/s, {komma(e['dauer'])} s\n\n")
                f.write("> " + e["antwort"].replace("\n", "\n> ") + "\n")
    print(f"\nAntworten zum Bewerten: ausgabe/modellvergleich.md")
    return 0 if any(t is not None for _, t, *_ in zusammenfassung) else 1


if __name__ == "__main__":
    sys.exit(main())
