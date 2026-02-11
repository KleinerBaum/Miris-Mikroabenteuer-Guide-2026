# Changelog

## Unreleased

### Added
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
