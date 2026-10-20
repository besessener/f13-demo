# Testfragen mit Antwortschlüssel – Wissensbasis LPA Kanto

Fiktives Dokument – nur für interne Demonstrationszwecke.

Die Fragen prüfen, ob die Recherche (RAG) die richtigen Stellen aus den sechs Dokumenten in `demo-data/rag/` findet. Alle Regeln sind erfunden. Ein Sprachmodell kann sie also nicht aus seinen Trainingsdaten kennen.

**Gegenprobe:** Dieselben Fragen werden zusätzlich **ohne RAG** gestellt, also direkt an das Sprachmodell ohne hochgeladene Dokumente. Das erledigt das Werkzeug `testfragen` (`docker compose run --rm testfragen`). Ohne Quellen rät das Modell oder sagt, dass es die Regel nicht kennt. Mit RAG sollte es die erwartete Antwort mit Fundstelle liefern. Der Unterschied zeigt, dass die Antwort aus den Dokumenten stammt. Frage 12 ist eine Kontrollfrage: Die Dokumente beantworten sie nicht. Das Modell soll dann sagen, dass die Information nicht in den Quellen steht, statt etwas zu erfinden.

| Nr | Frage | Erwartete Antwort | Fundstelle |
| --- | --- | --- | --- |
| 1 | Darf ich mein Glurak mit ins Büro bringen? | Nur mit schriftlicher Brandschutzfreigabe der oder des Brandschutzbeauftragten. Antrag mit Formblatt BS-17 spätestens 10 Arbeitstage vorher. Die Freigabe gilt 6 Monate für einen Raum. Zusätzlich Anmeldung als Begleitpokémon (PH-1). | VwV PokéHaltung § 3 (und § 4) |
| 2 | Was kostet eine Arenalizenz und wie lange dauert das Verfahren? | 2.500 Pokédollar. Entscheidung innerhalb von 6 Wochen nach Eingang der vollständigen Unterlagen, bei Ortsbegehung höchstens 10 Wochen. | ArenaLizO § 6 und § 7 |
| 3 | Welche Pokémon dürfen nicht in den Serverraum? | Elektro-Pokémon, ausdrücklich Pikachu, Raichu, Voltobal, Lektrobal, Elektek und Magnetilo, auch im Pokéball. Grund: unkontrollierte Entladungen, Spannungsspitzen, Datenverlust und Fehlalarme. | VwV PokéHaltung § 7 |
| 4 | Wer darf Meisterbälle ausgeben? | Ausschließlich die oder der Meisterballbeauftragte im Referat Z 2, im Vier-Augen-Prinzip mit Gegenzeichnung der Leitung der Abteilung Z. Antrag mit Formblatt MB-1. | Dienstanweisung Pokéball-Inventur § 7 |
| 5 | Wie lange darf Relaxo im Flur liegen? | Höchstens 15 Minuten am Stück. Danach zurück in den Pokéball oder in den Ruheraum für Großpokémon (Raum 0.12). 1,20 m Durchgang müssen frei bleiben. | VwV PokéHaltung § 5 |
| 6 | Darf Simsala bei meinem Mitarbeitergespräch dabei sein? | Nein. Psycho-Pokémon wie Abra, Kadabra und Simsala dürfen nicht an Personalgesprächen teilnehmen, auch nicht mit Zustimmung aller Beteiligten. | VwV PokéHaltung § 9 |
| 7 | Was kostet die Wiederbelebung eines Altbernsteins und gibt es dafür eine Ermäßigung? | 4.500 Pokédollar, nur im Pokécenter-Labor auf der Zinnoberinsel, Dauer 5 Werktage. Die Fossil-Wiederbelebung ist nicht ermäßigungsfähig. Nachts kommen 40 Prozent Nachtzuschlag hinzu. | GebO Pokécenter § 3, § 4 und § 5 |
| 8 | Bis wann kann ich gegen die Ablehnung meiner Arenalizenz Widerspruch einlegen? | Innerhalb von 21 Kalendertagen nach Bekanntgabe, schriftlich bei der Widerspruchsstelle des LPA Kanto (Referat A 1). Eine E-Mail genügt nicht. | ArenaLizO § 10 |
| 9 | Ein belegter dienstlicher Pokéball ist verschwunden. Was muss ich tun? | Verlustmeldung mit Formblatt VM-5 innerhalb von 24 Stunden an Referat Z 2. Weil der Ball belegt war, zusätzlich Verlustanzeige beim Pokémon-Fundbüro mit Formblatt FB-3 innerhalb von 48 Stunden. | Dienstanweisung Pokéball-Inventur § 5 und FAQ Bürgeranfragen Frage 1 |
| 10 | Mein Pikachu ist als Assistenzpokémon anerkannt. Darf es mit in den Serverraum? | Nein. Assistenzpokémon sind zwar von der Anmeldepflicht befreit, die typbezogenen Regeln gelten aber weiter. Elektro-Pokémon wie Pikachu dürfen den Serverraum nicht betreten. | FAQ Bürgeranfragen Frage 6 und VwV PokéHaltung § 7 |
| 11 | Welche Attacken sind gegen Glurak besonders wirksam und was brauche ich, um es ins Büro mitzunehmen? | Gestein-Attacken richten vierfachen Schaden an, Wasser und Elektro doppelten. Für das Büro ist eine Brandschutzfreigabe mit Formblatt BS-17 nötig, beantragt 10 Arbeitstage vorher. | Merkblatt Typenwirksamkeit Abschnitt 8 und VwV PokéHaltung § 3 |
| 12 | Wie hoch ist die jährliche Pokémon-Steuer für ein Arkani in Kanto? | Steht nicht in den Quellen. Das Modell soll sagen, dass die Dokumente dazu keine Angabe enthalten, und keinen Betrag erfinden. | keine (Kontrollfrage) |
