# FTP-uploader

Python-app för Windows, macOS och Linux. Ingen virtuell miljö, BAT, VBS, shellstartare eller Git-installation behövs för att köra appen.

## Installation och start

Installera en aktuell stabil Python med Tcl/Tk från python.org. Python måste installeras innan Python-kod kan köras; appen kan inte installera Python om Python saknas.

Ladda ned projektet och packa upp det i en skrivbar mapp.

- **Windows:** öppna `start.pyw` med Pythonw för start utan konsol. Filassociationen för `.pyw` måste peka på Pythonw. Ingen separat startfil eller virtuell miljö behövs.
- **macOS/Linux:** starta `python3 start.pyw` med installerad Python. GUI kräver en grafisk session. På Linux behövs systempaketet för Tk, exempelvis `python3-tk` på Debian/Ubuntu. Start från en redan öppen terminal stänger inte terminalen.

Direktstart av `main.pyw` fungerar också, men hoppar över releasekontrollen.

## Python-tillägg

Vid varje appstart kontrolleras samtliga appberoenden i `requirements.txt` med pip `install --upgrade`. Saknade paket installeras och befintliga uppgraderas till senaste stabila version som är kompatibel med aktuell Python och plattform. Plattformsberoenden filtreras för macOS/Linux. Status visas i ett fönster och fel visas/loggas i `logs/deps.log`.

Ingen virtuell miljö skapas eller krävs. Paketen installeras för den Python som startar appen; användarinstallation provas om normal installation misslyckas. Detta kan påverka andra program som använder samma Python. OS-hanterade Python-installationer kan blockera pip-installationer (PEP 668); appen kringgår inte systemets skydd. Installera då beroendena via systemets pakethanterare eller använd en separat, användarinstallerad Python.

Nätverk behövs för att verifiera senaste paketversioner. Vid fel försöker appen fortsätta med befintliga paket. Nyaste paket garanterar inte kompatibilitet med appkoden. Tk är en systemkomponent, inte ett pip-paket.

## Inställningar

Inställningar kopieras en gång från projektets `config/` till användarens mapp, utan att befintliga användarfiler skrivs över:

- Windows: `%APPDATA%\FTP-uploader\config`
- macOS: `~/Library/Application Support/FTP-uploader/config`
- Linux: `${XDG_CONFIG_HOME:-~/.config}/FTP-uploader/config`

JSON-filer och ikoner behålls eftersom appen behöver dem; programkoden och startaren är Python.

## Releaser – inga merges

**Inga grenar eller pull requests ska mergas. Appen kör inga Git-kommandon.**

Releasekontrollen använder Pythons standardbibliotek och GitHub API. Den jämför appens versionsnummer med senaste stabila GitHub Release, inte senaste commit på `main`. Taggar ska heta `vX.Y.Z` eller `X.Y.Z` (fyra versionsdelar stöds också). Prereleases/drafts används inte.

Menyn **Uppdateringar** innehåller automatisk uppdatering, fråga först (standard), avstängt och manuell sökning.
Uppdateraren laddar ner källarkivet för **den exakta publicerade release-taggen** från GitHub, aldrig `main`.
Manuell uppdatering inifrån appen schemaläggs till nästa start via `start.pyw`, så att aktiv kod inte byts ut medan appen körs.

Installationen använder bara Python. Den kontrollerar tagg mot `APP_VERSION`, arkivets sökvägar, storleksgränser och Python-syntax innan filer byts ut.
Programkod, `requirements.txt` och ikoner ersätts. Inställningar, exporter och andra filer lämnas orörda.
Gamla programfiler sparas i en syskonmapp med `.release-backup-<tid>` i namnet. Vid installationsfel försöker uppdateraren återställa alla ändrade filer.
Detta skyddar mot vanliga installationsfel, men inte mot strömavbrott; säkerhetskopian behålls för manuell återställning.
Gamla överflödiga programfiler tas inte bort automatiskt. Arkivet verifieras inte med en separat kryptografisk signatur.

En uppackad releaseinstallation kan uppdateras automatiskt. Utvecklingskopior med `.git` uppdateras inte, för att skydda arbetsgrenen och lokala ändringar. Ingen Git-installation behövs och inga merges görs.

Projektet behöver publicerade GitHub Releases för att kontrollen ska hitta en utgåva. Resultat loggas i användarmappens `logs/update.log`. Sätt `FTP_UPLOADER_AUTOUPDATE=0` för att stoppa automatisk releasekontroll (påverkar inte pip-kontrollen).

## Tester

```sh
python -m unittest discover -s tests -v
```

GUI och konsolfri start behöver även verifieras på respektive operativsystem.

## Redigera en befintlig export

I fliken Bildgalleri: välj **Öppna export** och välj mappen som innehåller `index.html`.
Redigeraren kan lägga till bilder, ta bort markerade, flytta en bild upp/ned och ändra titel/beskrivning.
**Spara export** bygger om HTML och bildlistan utan att köra FTP-uppladdning. Minst en bild måste finnas kvar.

Nya exporter innehåller `gallery-project.json` med bildordning, galleriinställningar och egna HTML/CSS-tillägg.
Äldre standard-/flat-exporter kan läsas från bildkorten i HTML, men tema, beskrivning och egna tillägg kan behöva återskapas; en varning visas.
PDF/video tas med vid omsparning. Redigering av enskilda bildtexter och videor ingår inte i denna redigerare.

Sparning sker först i en temporär mapp. Därefter flyttas den gamla exporten till en syskonmapp med `.backup-<tid>` i namnet och ersätts av den nya.
Originalbilder som läggs till ändras inte. Borttagning gäller bara den nya exporten; säkerhetskopian behåller den gamla.
Om omsparning misslyckas före utbytet är originalexporten orörd. Säkerhetskopior tas inte bort automatiskt.

## Förbättrade gallerivyer

- **Appens bildgalleri:** jämnstora bildytor utan beskärning, filnamn som tooltip och tydlig bock vid markering. Sökning och formatfilter kombineras; en tom sökning visar ett meddelande i stället för att felaktigt visa alla bilder.
- **Exportredigeraren:** bläddringsbar bildlista med miniatyrer, större förhandsvisning, pixelmått och filstorlek. Ctrl/⌘ och Shift markerar flera bilder för borttagning; Upp/Ned flyttar en markerad bild i ordningen.
- **Webbgalleriet:** tydligare tangentbordsfokus, större mobilkontroller och lugnare hoverbeteende på pekskärm. Bekvämt visningsläge visar hela bilden utan beskärning och håller bildtexten synlig. Exportera om för att få de nya stilarna i en befintlig export.

Visuella GUI-tester behöver göras på en dator med Tkinter och grafisk session; de automatiska testerna täcker filtrering, layoutberäkning och CSS-regler men är inte skärmbildstester.

### Ändrad release med samma versionsnummer

Även om versionsnumret är oförändrat (t.ex. `v1.0.0`) kontrolleras commit-ID:t bakom den publicerade release-taggen.
Om taggen pekar på en annan commit än den installerade laddas den uppdaterade releasekoden ner enligt valt uppdateringsläge.
Installerat tagg-/commit-ID sparas i `.release-state.json`; en installation som saknar denna information installeras om en gång för att skapa jämförelseunderlag.
Arkivet hämtas för exakt det kontrollerade commit-ID:t, aldrig för `main`. Annoterade taggar stöds också.

För att publicera ändrad programkod under samma release måste release-taggen flyttas till den nya commiten.
Att bara ändra releasebeskrivningen eller byta uppladdade bilagor ändrar inte källarkivet och utlöser inte denna uppdatering.
Äldre versionsnummer installeras inte över nyare. Utvecklingskopior med `.git` skyddas fortfarande från installation.
