# Changelog

## Unreleased

### Geändert / Changed
- DE: Die Sektion „Alle Mikroabenteuer“ wurde in „Alternative Mikroabenteuer“ umbenannt und die zusätzliche Übersichtstabelle entfernt; die Abenteuer bleiben über Drop-down-Elemente (`st.expander`) erreichbar.
- EN: Renamed the “All Micro-Adventures” section to “Alternative Micro-Adventures” and removed the extra overview table; adventures remain accessible via drop-down expanders (`st.expander`).
- DE: Den gesamten im Header sichtbaren Begrüßungstext entfernt (Bild-Caption, Hero-Titel und Hero-Untertitel), sodass im oberen Seitenbereich nur noch das Bild angezeigt wird.
- EN: Removed all visible welcome text in the header (image caption, hero title, and hero subtitle), so only the image remains in the top section.
- DE: Das Begrüßungsbild im Hero-Bereich wird jetzt aus dem lokalen Asset `20251219_155329.jpg` via `st.image` geladen, um Streamlit-`MediaFileHandler`-Fehler durch abgelaufene Media-IDs zu vermeiden.
- EN: The hero welcome image is now loaded from the local asset `20251219_155329.jpg` via `st.image` to avoid Streamlit `MediaFileHandler` errors caused by expired media IDs.
- DE: Headline „🌿 Mikroabenteuer mit Carla / Kleine Abenteuer. Große Erinnerungen.“ im Hero-Bereich zentriert und das Begrüßungsbild auf eine um 70% reduzierte Darstellung (30% Breite) umgestellt.
- EN: Centered the hero headline “🌿 Mikroabenteuer mit Carla / Kleine Abenteuer. Große Erinnerungen.” and reduced the welcome image display by 70% (30% width).
- DE: `mikroabenteuer/ui/__init__.py` ergänzt und Package-Imports auf relative Importe umgestellt, um sporadische `KeyError`-Importprobleme in Streamlit-Reloadern zu vermeiden.
- EN: Added `mikroabenteuer/ui/__init__.py` and switched package internals to relative imports to prevent intermittent `KeyError` import failures during Streamlit reloads.
- Wetterservice (`Open-Meteo`) für Düsseldorf inkl. typed API-Parsing und Retry-Backoff.
- Adventure Engine mit wetterbasierter Auswahl (Regen/Sonne/Wind/Kalt).
- Daily Scheduler (APScheduler) mit Cron 08:20 (Europe/Berlin).
- RFC-5545-konformer ICS-Builder mit escaped Feldern und UTC-Timestamps.
- Bilinguales HTML-Mail-Template mit Inline-CSS.
- Gmail Service für Versand von HTML-Mail + ICS Attachment via OAuth.
- Dockerfile und `docker-compose.yml` für Deployment.
- Unit-Tests für Adventure Engine, ICS-Builder und Mail-Template.

### Changed
- `app.py` startet Scheduler optional über `ENABLE_DAILY_SCHEDULER=1`.
- `requirements.txt` um Scheduler-, Weather- und Google-API-Abhängigkeiten erweitert.
- README um Architektur-, Deployment-, Security- und OAuth-Setup-Dokumentation erweitert.

### Release Notes
- Das Projekt unterstützt jetzt automatisierte tägliche Abenteuer-Mails als SaaS-nahe Basis.
- Für Production wird ein HTTPS-Reverse-Proxy (z. B. Nginx + Let's Encrypt) empfohlen.
