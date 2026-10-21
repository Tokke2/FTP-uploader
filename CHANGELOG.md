# Ändringslogg

## v1.0.0

Första GitHub-releasen med den nya start- och uppdateringslösningen. Appens tidigare interna versionsnummer 2.8.4 ersätts av 1.0.0 för denna releasebaslinje.

### Nytt

- Python-startare för Windows, macOS och Linux, utan BAT/VBS eller krav på virtuell miljö.
- Uppdatering från publicerade stabila GitHub Releases, utan Git eller merges.
- Detektering av ändrad release-commit även när versionsnumret är oförändrat.
- Uppdateringsval: automatiskt, fråga först, avstängt och manuell kontroll.
- Säkerhetskopiering och återställning vid installationsfel; utvecklingskopior med `.git` skrivs inte över.
- Inställningar i användarens appmapp med engångsmigrering från `config/`.
- Kontroll, installation och uppgradering av appens Python-paket vid varje start.
- Minimering till tray med vanlig minimering som fallback om tray saknas.
- Öppna och redigera exporterade gallerier: lägg till/ta bort bilder, ändra ordning, titel och beskrivning.
- Säkerhetskopia av exporten vid omsparning; ingen automatisk FTP-uppladdning.
- Förbättrade gallerivyer, miniatyrer och förhandsvisning i exportredigeraren samt tillgängligare webbstilar.

### Installation

Installera Python med Tcl/Tk. Hämta och packa upp releasekällkoden, starta `start.pyw` med Pythonw på Windows eller `python3 start.pyw` på macOS/Linux. Appen kontrollerar Python-paketen vid start. Linux kan behöva systempaketet `python3-tk`.

Användare av tidigare interna versioner med versionsnummer över 1.0.0 måste installera denna baslinje manuellt: uppdateraren gör inte automatisk nedgradering.

### Verifiering och begränsningar

- 37 automatiska tester passerar samt Python-syntaxkontroller.
- GUI och plattformsspecifika tray-funktioner är inte visuellt verifierade i sandboxen (Tkinter saknas).
- Senaste pip-paket garanterar inte kompatibilitet; systemhanterad Python kan begränsa paketinstallation.
- Releasearkiv har ingen separat kryptografisk signatur. Säkerhetskopior behålls för manuell återställning.
- Äldre exporter kan sakna projektdata för tema/egen HTML/CSS; redigeraren visar en varning.
