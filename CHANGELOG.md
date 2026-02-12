# Changelog

## Unreleased

### Geändert / Changed
- DE: Neues „Activity Search (NEW)“-Schema in `mikroabenteuer/models.py` ergänzt (inkl. `TimeWindow`, `ActivitySearchCriteria`, `WeatherReport`, `SearchStrategy`, `ActivitySuggestion`, `ActivityPlan`) mit strikter Validierung (`extra="forbid"`).
- EN: Added a new “Activity Search (NEW)” schema section in `mikroabenteuer/models.py` (including `TimeWindow`, `ActivitySearchCriteria`, `WeatherReport`, `SearchStrategy`, `ActivitySuggestion`, `ActivityPlan`) with strict validation (`extra="forbid"`).
- DE: Die Landing-Page wurde auf die neuen Module unter `src/mikroabenteuer` umgestellt (Config, Seed, Wetter, Recommender, OpenAI-Planung) und konsistent integriert.
- EN: The landing page now uses the new modules under `src/mikroabenteuer` (config, seed, weather, recommender, OpenAI planning) in a consistent integration.
- DE: Export-Flow erweitert: Tagesplan kann jetzt direkt als JSON, Markdown und ICS heruntergeladen werden.
- EN: Export flow extended: the daily plan can now be downloaded directly as JSON, Markdown, and ICS.
- DE: Neuer optionaler Automation-Bereich zum manuellen Auslösen des Daily-Jobs (inkl. optionalem Gmail-/Google-Calendar-Versand bei konfigurierten Credentials).
- EN: Added an optional automation area to manually run the daily job (including optional Gmail/Google Calendar delivery when credentials are configured).
- DE: Für KI-Textgenerierung wurden in der UI verständliche Fehlhinweise plus Retry mit exponentiellem Backoff ergänzt.
- EN: For AI text generation, the UI now provides clear error hints plus retry with exponential backoff.
- DE: Alle relevanten UI- und Mail-Texte wurden auf die exklusive Zielgruppe „Miri (Mutter) und Carla (Tochter)" angepasst.
- EN: All relevant UI and email texts were adjusted for the exclusive audience “Miri (mother) and Carla (daughter)”.
- DE: Die Landingpage wurde visuell entschlackt und neu strukturiert: kompakter Hero, klarer 3-Schritte-Einstieg, Fokus auf Filter/Karten und reduzierter Abschlussbereich.
- EN: The landing page was visually decluttered and restructured: compact hero, clear 3-step onboarding, focus on filters/cards, and a reduced closing section.
- DE: Kontraste im Export-Bereich wurden erhöht; Download-Buttons und E-Mail-Vorschau sind nun auch ohne Hover eindeutig lesbar.
- EN: Increased contrast in the export area; download buttons and email preview are now clearly readable without hover.
- DE: Die Hero-CTA-Buttons wurden von Blau auf Dunkelgrau umgestellt; die Button-Schrift bleibt weiß für klare Lesbarkeit.
- EN: Hero CTA buttons were changed from blue to dark gray; button text remains white for clear readability.
- DE: Wetterabfrage ist jetzt standortkonfigurierbar über `WEATHER_LAT` und `WEATHER_LON`; Standard ist Volksgarten (Düsseldorf) statt festem Stadtzentrum.
- EN: Weather lookup is now location-configurable via `WEATHER_LAT` and `WEATHER_LON`; default is Volksgarten (Düsseldorf) instead of a fixed city-center coordinate.
- DE: Bei mehreren passenden Abenteuern priorisiert die Auswahl nun Einträge mit Standort „Volksgarten“.
- EN: If multiple adventures match, selection now prioritizes entries whose location contains “Volksgarten”.
- DE: Google OAuth2 wurde auf Least-Privilege-Scopes für Kalender und Gmail erweitert (`calendar.events`, `calendar.readonly`, `gmail.send`) und zentral im neuen Auth-Modul gebündelt.
- EN: Google OAuth2 was expanded to least-privilege scopes for calendar and Gmail (`calendar.events`, `calendar.readonly`, `gmail.send`) and centralized in a new auth module.
- DE: Neue Google-Integrationen für Kalender-Events und HTML-Mail-Versand inkl. API-Retry mit exponentiellem Backoff ergänzt.
- EN: Added new Google integrations for calendar events and HTML email sending, including API retry with exponential backoff.
- DE: Abenteuer-Detailansicht um Aktionen „In Kalender eintragen / Add to calendar“ und „Per Mail senden / Send by email“ erweitert.
- EN: Adventure detail view now includes actions “In Kalender eintragen / Add to calendar” and “Per Mail senden / Send by email”.
- DE: Die Startseite wurde zu einer conversion-orientierten, zweisprachigen Funnel-Landingpage ausgebaut (Hero, Problem/Lösung, Erklärsektion, Filterkarten, Nutzenargumentation, 3-Schritte-Start, Lead-Element, Abschluss-CTA).
- EN: The homepage was expanded into a conversion-oriented bilingual funnel landing page (hero, problem/solution, explanation section, filter cards, impact arguments, 3-step start, lead element, closing CTA).
- DE: Neue Abenteuer-Kategorien mit kombinierten Filtern (Jahreszeit, Dauer, Alter, Stimmung) und Karten-CTAs "Details ansehen / View details" unterstützen die direkte Nutzerhandlung.
- EN: New adventure categories with combined filters (season, duration, age, mood) and card CTAs "Details ansehen / View details" support direct user action.
- DE: Über dem Begrüßungsbild wird jetzt zentriert die Headline „Kleine Abenteuer. Große Erinnerungen 🎂“ angezeigt, ergänzt um die englische Zeile „Small adventures. Big memories.“.
- EN: A centered headline “Kleine Abenteuer. Große Erinnerungen 🎂” is now shown above the welcome image, complemented by the English line “Small adventures. Big memories.”.
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
- DE: Neue UI-Sektion „Wetter & Events“ ergänzt, inkl. Resource-Factory (`@st.cache_resource`) für `OpenAIActivityService` + `ActivityOrchestrator`, validierter Kriterien-Erfassung und Ausgabe von Wetter, Hinweisen, Events sowie Quellen.
- EN: Added a new “Weather & Events” UI section including a resource factory (`@st.cache_resource`) for `OpenAIActivityService` + `ActivityOrchestrator`, validated criteria input, and rendering of weather, warnings, events, and sources.
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
- Landing-Page integriert jetzt die neue `src`-Architektur inklusive Exporte (JSON/Markdown/ICS) und optionaler Daily-Automation.
- Export- und Vorschau-Elemente sind kontrastoptimiert und damit in hellen/dunklen Zuständen besser zugänglich.
- App-Texte adressieren jetzt durchgehend Miri und Carla statt allgemein Familien.
- Landingpage ist jetzt deutlich übersichtlicher und führt Nutzer:innen mit weniger Ablenkung schneller zur Abenteuerauswahl.
- OAuth2-Setup für Kalender + Gmail ist nun vorbereitet (Consent-Screen-Konfiguration, Desktop-Client-Datei in `secrets/`, lokale Token-Erzeugung).
- Daily- und manuelle Mailflows verwenden dieselbe sichere Credential-Verwaltung.
- Das Projekt unterstützt jetzt automatisierte tägliche Abenteuer-Mails als SaaS-nahe Basis.
- Für Production wird ein HTTPS-Reverse-Proxy (z. B. Nginx + Let's Encrypt) empfohlen.
- Wetter-Standort kann jetzt per `WEATHER_LAT`/`WEATHER_LON` gesetzt werden; die Abenteuerauswahl priorisiert bei Mehrfachtreffern den Volksgarten.
- Neue Wetter-&-Events-Sektion liefert zusätzliche, quellenbasierte Event-Vorschläge mit klaren Status- und Fehlerhinweisen direkt im Main-Flow.
